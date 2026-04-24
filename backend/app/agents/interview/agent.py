import json
import logging
import re
from typing import AsyncIterator
from app.agents.base import BaseAgent, AgentState
from app.services.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Empty response from LLM")

    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        text = json_match.group()

    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)

    return json.loads(text)


INTERVIEW_SYSTEM_PROMPT = """你是一个专业的模拟面试官。你需要根据学员的简历和面试阶段，提出有针对性的问题，并评估学员的回答。

面试流程分为四个阶段：
1. INTRO - 自我介绍阶段：让学员进行自我介绍
2. TECH - 技术问题阶段：针对简历中的技术栈提问
3. PROJECT - 项目经验阶段：深入询问项目细节
4. REPORT - 面试报告阶段：生成面试评估报告

评估维度：
- 技术深度：评估回答的技术深度和准确性
- 表达能力：评估回答的逻辑性和表达清晰度

每个维度独立评分（0-100分）。"""


INTRO_PROMPT = """你是一位面试官，请开始模拟面试。

学员简历摘要：
{resume_summary}

重点关注领域：{focus_areas}

已知薄弱点：{weaknesses}

请用友好专业的语气邀请学员进行自我介绍，并简要说明面试流程（技术问题3道、项目问题2道）。"""


TECH_QUESTION_PROMPT = """基于学员的简历和之前的回答，提出一个技术问题。

学员简历摘要：
{resume_summary}

之前的问答记录：
{qa_history}

已提问的技术问题：
{asked_questions}

已知薄弱点（优先针对这些点出题）：
{weaknesses}

要求：
1. 优先针对薄弱点出题，如果没有薄弱点则针对简历中提到的技术栈提问
2. 不要重复已提问的问题
3. 问题难度适中，由浅入深
4. 每次只问一个问题

请直接提出问题，不要其他内容。"""


TECH_EVAL_PROMPT = """请严格根据学员的实际回答内容进行评估。

问题：{question}
学员回答：{answer}

评估规则：
1. 如果回答为空、过短（少于10个字）、或与问题无关，tech_score和expression_score必须为0-20分
2. 如果回答只是简单确认（如"是"、"好的"、"1"等），tech_score和expression_score必须为0-20分
3. 只有当回答包含实质性技术内容时，才能给较高分数
4. 评分必须基于回答的实际内容，不要臆想或补充回答中没有的内容

请以JSON格式返回评估结果：
{{
  "tech_score": 0-100,
  "expression_score": 0-100,
  "feedback": "简短反馈（50字以内）",
  "key_points": ["回答中提到的关键点"],
  "missed_points": ["回答中遗漏的重要点"],
  "weakness_tags": ["薄弱点标签"]
}}"""


PROJECT_QUESTION_PROMPT = """基于学员的简历和之前的回答，提出一个关于项目经验的问题。

学员简历摘要：
{resume_summary}

之前的问答记录：
{qa_history}

已提问的项目问题：
{asked_questions}

已知薄弱点（优先针对这些点出题）：
{weaknesses}

要求：
1. 优先针对薄弱点出题，关注项目中的技术决策和问题解决过程
2. 不要重复已提问的问题
3. 每次只问一个问题

请直接提出问题。"""


PROJECT_EVAL_PROMPT = """请严格根据学员的实际回答内容进行评估。

问题：{question}
学员回答：{answer}

评估规则：
1. 如果回答为空、过短（少于10个字）、或与问题无关，tech_score和expression_score必须为0-20分
2. 如果回答只是简单确认（如"是"、"好的"、"1"等），tech_score和expression_score必须为0-20分
3. 只有当回答包含实质性技术内容时，才能给较高分数
4. 评分必须基于回答的实际内容，不要臆想或补充回答中没有的内容

请以JSON格式返回评估结果：
{{
  "tech_score": 0-100,
  "expression_score": 0-100,
  "feedback": "简短反馈（50字以内）",
  "depth_analysis": "基于实际回答内容的技术深度分析",
  "expression_analysis": "基于实际回答内容的表达分析",
  "weakness_tags": ["薄弱点标签"]
}}"""


REPORT_PROMPT = """请基于以下面试记录生成完整的面试评估报告：

学员简历摘要：
{resume_summary}

面试问答记录：
{qa_history}

各轮评分：
{scores}

请以JSON格式返回报告：
{{
  "overall_comment": "总体评价（100字以内）",
  "tech_score": 0-100,
  "expression_score": 0-100,
  "overall_score": 0-100,
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["建议1", "建议2", "建议3"],
  "radar_data": {{
    "indicators": ["技术深度", "表达能力", "项目经验", "问题解决", "逻辑思维", "沟通技巧"],
    "values": [0, 0, 0, 0, 0, 0]
  }},
  "detailed_feedback": "详细反馈"
}}"""


class InterviewAgent(BaseAgent):
    agent_type = "interview"
    agent_name = "模拟面试官"
    agent_description = "四阶段模拟面试 | 状态机控制 | 多轮交互"

    TECH_QUESTIONS_COUNT = 3
    PROJECT_QUESTIONS_COUNT = 2

    async def _intro(self, state: AgentState) -> AgentState:
        resume_summary = state.get("context", {}).get("resume_summary", "暂无简历信息")
        focus_areas = state.get("context", {}).get("focus_areas", [])
        weaknesses = state.get("context", {}).get("weaknesses", [])
        focus_str = "、".join(focus_areas) if focus_areas else "无特别关注"
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        response = await LLMFactory.chat(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": INTRO_PROMPT.format(
                    resume_summary=resume_summary,
                    focus_areas=focus_str,
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        )
        state["final_answer"] = response
        state["context"]["stage"] = "TECH"
        if "qa_history" not in state["context"]:
            state["context"]["qa_history"] = []
        if "scores" not in state["context"]:
            state["context"]["scores"] = []
        if "tech_count" not in state["context"]:
            state["context"]["tech_count"] = 0
        if "project_count" not in state["context"]:
            state["context"]["project_count"] = 0
        if "asked_tech_questions" not in state["context"]:
            state["context"]["asked_tech_questions"] = []
        if "asked_project_questions" not in state["context"]:
            state["context"]["asked_project_questions"] = []
        if "weaknesses" not in state["context"]:
            state["context"]["weaknesses"] = []
        state["context"]["current_question"] = None
        logger.info("Interview intro completed, stage set to TECH")
        return state

    async def _tech_question(self, state: AgentState) -> AgentState:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        asked_questions = "\n".join(state.get("context", {}).get("asked_tech_questions", []))
        weaknesses = state.get("context", {}).get("weaknesses", [])
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        response = await LLMFactory.chat(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": TECH_QUESTION_PROMPT.format(
                    resume_summary=resume_summary,
                    qa_history=qa_history,
                    asked_questions=asked_questions or "暂无",
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        )
        state["final_answer"] = response
        state["context"]["current_question"] = response
        state["context"]["stage"] = "TECH"
        if "asked_tech_questions" not in state["context"]:
            state["context"]["asked_tech_questions"] = []
        state["context"]["asked_tech_questions"].append(response)
        logger.info(f"Tech question generated: {response[:50]}...")
        return state

    async def _tech_evaluate(self, state: AgentState) -> AgentState:
        current_q = state.get("context", {}).get("current_question", "")
        answer = state["query"]

        try:
            result = await LLMFactory.chat(
                messages=[
                    {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": TECH_EVAL_PROMPT.format(
                        question=current_q, answer=answer
                    )},
                ],
                temperature=0.1,
            )
            eval_result = _extract_json(result)
            logger.info(f"Tech eval parsed: tech={eval_result.get('tech_score')}, expr={eval_result.get('expression_score')}")
        except Exception as e:
            logger.error(f"Tech eval parse failed: {e}")
            eval_result = {
                "tech_score": 50,
                "expression_score": 50,
                "feedback": "评估完成",
                "key_points": [],
                "missed_points": [],
                "weakness_tags": [],
            }

        if "qa_history" not in state["context"]:
            state["context"]["qa_history"] = []
        state["context"]["qa_history"].append({
            "stage": "TECH",
            "question": current_q,
            "answer": answer,
            "eval": eval_result,
        })
        if "scores" not in state["context"]:
            state["context"]["scores"] = []
        state["context"]["scores"].append(eval_result)
        state["context"]["tech_count"] = state["context"].get("tech_count", 0) + 1
        state["context"]["current_question"] = None

        weakness_tags = eval_result.get("weakness_tags", [])
        if weakness_tags:
            if "weaknesses" not in state["context"]:
                state["context"]["weaknesses"] = []
            for tag in weakness_tags:
                if tag and tag not in state["context"]["weaknesses"]:
                    state["context"]["weaknesses"].append(tag)
            logger.info(f"Added weakness tags: {weakness_tags}")

        feedback = eval_result.get("feedback", "")
        tech_count = state["context"]["tech_count"]
        state["final_answer"] = f"感谢你的回答。{feedback}\n\n（技术问题 {tech_count}/{self.TECH_QUESTIONS_COUNT}）"
        return state

    async def _project_question(self, state: AgentState) -> AgentState:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        asked_questions = "\n".join(state.get("context", {}).get("asked_project_questions", []))
        weaknesses = state.get("context", {}).get("weaknesses", [])
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        response = await LLMFactory.chat(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": PROJECT_QUESTION_PROMPT.format(
                    resume_summary=resume_summary,
                    qa_history=qa_history,
                    asked_questions=asked_questions or "暂无",
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        )
        state["final_answer"] = response
        state["context"]["current_question"] = response
        state["context"]["stage"] = "PROJECT"
        if "asked_project_questions" not in state["context"]:
            state["context"]["asked_project_questions"] = []
        state["context"]["asked_project_questions"].append(response)
        logger.info(f"Project question generated: {response[:50]}...")
        return state

    async def _project_evaluate(self, state: AgentState) -> AgentState:
        current_q = state.get("context", {}).get("current_question", "")
        answer = state["query"]

        try:
            result = await LLMFactory.chat(
                messages=[
                    {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": PROJECT_EVAL_PROMPT.format(
                        question=current_q, answer=answer
                    )},
                ],
                temperature=0.1,
            )
            eval_result = _extract_json(result)
            logger.info(f"Project eval parsed: tech={eval_result.get('tech_score')}, expr={eval_result.get('expression_score')}")
        except Exception as e:
            logger.error(f"Project eval parse failed: {e}")
            eval_result = {
                "tech_score": 50,
                "expression_score": 50,
                "feedback": "评估完成",
                "depth_analysis": "",
                "expression_analysis": "",
                "weakness_tags": [],
            }

        if "qa_history" not in state["context"]:
            state["context"]["qa_history"] = []
        state["context"]["qa_history"].append({
            "stage": "PROJECT",
            "question": current_q,
            "answer": answer,
            "eval": eval_result,
        })
        if "scores" not in state["context"]:
            state["context"]["scores"] = []
        state["context"]["scores"].append(eval_result)
        state["context"]["project_count"] = state["context"].get("project_count", 0) + 1
        state["context"]["current_question"] = None

        weakness_tags = eval_result.get("weakness_tags", [])
        if weakness_tags:
            if "weaknesses" not in state["context"]:
                state["context"]["weaknesses"] = []
            for tag in weakness_tags:
                if tag and tag not in state["context"]["weaknesses"]:
                    state["context"]["weaknesses"].append(tag)
            logger.info(f"Added weakness tags: {weakness_tags}")

        feedback = eval_result.get("feedback", "")
        project_count = state["context"]["project_count"]
        state["final_answer"] = f"感谢你的回答。{feedback}\n\n（项目问题 {project_count}/{self.PROJECT_QUESTIONS_COUNT}）"
        return state

    async def _generate_report(self, state: AgentState) -> AgentState:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        scores_text = json.dumps(state.get("context", {}).get("scores", []), ensure_ascii=False, indent=2)

        logger.info("Generating interview report...")

        try:
            result = await LLMFactory.chat(
                messages=[
                    {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": REPORT_PROMPT.format(
                        resume_summary=resume_summary,
                        qa_history=qa_history,
                        scores=scores_text,
                    )},
                ],
                temperature=0.1,
            )
            report = _extract_json(result)
            state["context"]["report"] = report
            state["final_answer"] = json.dumps(report, ensure_ascii=False, indent=2)
            logger.info(f"Report generated: overall_score={report.get('overall_score')}")
        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            state["final_answer"] = "面试报告生成失败"
            state["context"]["report"] = {}

        state["context"]["stage"] = "REPORT"
        return state

    def _format_qa_history(self, qa_history: list) -> str:
        if not qa_history:
            return "暂无"
        lines = []
        for qa in qa_history:
            lines.append(f"[{qa['stage']}] Q: {qa['question']}")
            lines.append(f"A: {qa['answer']}")
            if qa.get("eval"):
                lines.append(f"评估: 技术{qa['eval'].get('tech_score', 0)} 表达{qa['eval'].get('expression_score', 0)}")
        return "\n".join(lines)

    async def run(self, state: AgentState) -> AgentState:
        if "context" not in state:
            state["context"] = {}

        stage = state.get("context", {}).get("stage", "INTRO")
        has_current_q = state.get("context", {}).get("current_question") is not None
        logger.info(f"Interview run: stage={stage}, has_current_question={has_current_q}")

        if stage == "INTRO":
            return await self._intro(state)

        elif stage == "TECH":
            if not has_current_q:
                return await self._tech_question(state)
            state = await self._tech_evaluate(state)
            if state["context"]["tech_count"] >= self.TECH_QUESTIONS_COUNT:
                state["context"]["stage"] = "PROJECT"
                state["context"]["current_question"] = None
                logger.info("Tech phase completed, moving to PROJECT")
                return state
            return await self._tech_question(state)

        elif stage == "PROJECT":
            if not has_current_q:
                return await self._project_question(state)
            state = await self._project_evaluate(state)
            if state["context"]["project_count"] >= self.PROJECT_QUESTIONS_COUNT:
                state["context"]["stage"] = "REPORT"
                state["context"]["current_question"] = None
                logger.info("Project phase completed, moving to REPORT")
                return state
            return await self._project_question(state)

        elif stage == "REPORT":
            return await self._generate_report(state)

        return state

    async def stream(self, state: AgentState) -> AsyncIterator[str]:
        if "context" not in state:
            state["context"] = {}

        stage = state.get("context", {}).get("stage", "INTRO")
        has_current_q = state.get("context", {}).get("current_question") is not None
        logger.info(f"Interview stream: stage={stage}, has_current_question={has_current_q}")

        if stage == "INTRO":
            async for chunk in self._stream_intro(state):
                yield chunk
            return

        if stage == "TECH":
            if not has_current_q:
                async for chunk in self._stream_tech_question(state):
                    yield chunk
                return
            state = await self._tech_evaluate(state)
            yield state.get("final_answer", "")
            if state["context"]["tech_count"] >= self.TECH_QUESTIONS_COUNT:
                state["context"]["stage"] = "PROJECT"
                state["context"]["current_question"] = None
                logger.info("Tech phase completed, moving to PROJECT")
                yield "\n\n**技术问题阶段结束，现在进入项目经验阶段**\n\n"
                async for chunk in self._stream_project_question(state):
                    yield chunk
                return
            yield "\n\n"
            async for chunk in self._stream_tech_question(state):
                yield chunk
            return

        if stage == "PROJECT":
            if not has_current_q:
                async for chunk in self._stream_project_question(state):
                    yield chunk
                return
            state = await self._project_evaluate(state)
            yield state.get("final_answer", "")
            if state["context"]["project_count"] >= self.PROJECT_QUESTIONS_COUNT:
                state["context"]["stage"] = "REPORT"
                state["context"]["current_question"] = None
                logger.info("Project phase completed, moving to REPORT")
                return
            yield "\n\n"
            async for chunk in self._stream_project_question(state):
                yield chunk
            return

        if stage == "REPORT":
            async for chunk in self.stream_report(state):
                yield chunk
            return

    async def _stream_intro(self, state: AgentState) -> AsyncIterator[str]:
        resume_summary = state.get("context", {}).get("resume_summary", "暂无简历信息")
        focus_areas = state.get("context", {}).get("focus_areas", [])
        weaknesses = state.get("context", {}).get("weaknesses", [])
        focus_str = "、".join(focus_areas) if focus_areas else "无特别关注"
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        async for chunk in LLMFactory.chat_stream(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": INTRO_PROMPT.format(
                    resume_summary=resume_summary,
                    focus_areas=focus_str,
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        ):
            yield chunk

        state["context"]["stage"] = "TECH"
        if "qa_history" not in state["context"]:
            state["context"]["qa_history"] = []
        if "scores" not in state["context"]:
            state["context"]["scores"] = []
        if "tech_count" not in state["context"]:
            state["context"]["tech_count"] = 0
        if "project_count" not in state["context"]:
            state["context"]["project_count"] = 0
        if "asked_tech_questions" not in state["context"]:
            state["context"]["asked_tech_questions"] = []
        if "asked_project_questions" not in state["context"]:
            state["context"]["asked_project_questions"] = []
        if "weaknesses" not in state["context"]:
            state["context"]["weaknesses"] = []
        state["context"]["current_question"] = None

    async def _stream_tech_question(self, state: AgentState) -> AsyncIterator[str]:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        asked_questions = "\n".join(state.get("context", {}).get("asked_tech_questions", []))
        weaknesses = state.get("context", {}).get("weaknesses", [])
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        full_response = ""
        async for chunk in LLMFactory.chat_stream(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": TECH_QUESTION_PROMPT.format(
                    resume_summary=resume_summary,
                    qa_history=qa_history,
                    asked_questions=asked_questions or "暂无",
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        ):
            full_response += chunk
            yield chunk

        state["context"]["current_question"] = full_response
        state["context"]["stage"] = "TECH"
        if "asked_tech_questions" not in state["context"]:
            state["context"]["asked_tech_questions"] = []
        state["context"]["asked_tech_questions"].append(full_response)
        logger.info(f"Tech question generated: {full_response[:50]}...")

    async def _stream_project_question(self, state: AgentState) -> AsyncIterator[str]:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        asked_questions = "\n".join(state.get("context", {}).get("asked_project_questions", []))
        weaknesses = state.get("context", {}).get("weaknesses", [])
        weakness_str = "、".join(weaknesses) if weaknesses else "暂无"

        full_response = ""
        async for chunk in LLMFactory.chat_stream(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": PROJECT_QUESTION_PROMPT.format(
                    resume_summary=resume_summary,
                    qa_history=qa_history,
                    asked_questions=asked_questions or "暂无",
                    weaknesses=weakness_str
                )},
            ],
            temperature=0.7,
        ):
            full_response += chunk
            yield chunk

        state["context"]["current_question"] = full_response
        state["context"]["stage"] = "PROJECT"
        if "asked_project_questions" not in state["context"]:
            state["context"]["asked_project_questions"] = []
        state["context"]["asked_project_questions"].append(full_response)
        logger.info(f"Project question generated: {full_response[:50]}...")

    async def stream_report(self, state: AgentState) -> AsyncIterator[str]:
        resume_summary = state.get("context", {}).get("resume_summary", "")
        qa_history = self._format_qa_history(state.get("context", {}).get("qa_history", []))
        scores_text = json.dumps(state.get("context", {}).get("scores", []), ensure_ascii=False, indent=2)

        logger.info("Generating interview report stream...")

        full_response = ""
        async for chunk in LLMFactory.chat_stream(
            messages=[
                {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": REPORT_PROMPT.format(
                    resume_summary=resume_summary,
                    qa_history=qa_history,
                    scores=scores_text,
                )},
            ],
            temperature=0.1,
        ):
            full_response += chunk

        try:
            report = _extract_json(full_response)
            state["context"]["report"] = report
            logger.info(f"Report generated: overall_score={report.get('overall_score')}")

            formatted_report = self._format_report(report)
            for char in formatted_report:
                yield char
        except Exception as e:
            logger.error(f"Report parse failed: {e}", exc_info=True)
            state["context"]["report"] = {}
            yield "面试报告生成失败，请重试"

        state["context"]["stage"] = "REPORT"

    def _format_report(self, report: dict) -> str:
        lines = ["## 📋 面试评估报告\n"]

        if report.get("overall_comment"):
            lines.append(f"### 总体评价\n{report['overall_comment']}\n")

        if report.get("overall_score"):
            lines.append(f"### 综合评分\n**{report['overall_score']}分**\n")

        if report.get("strengths"):
            lines.append("### ✅ 优势")
            for s in report["strengths"]:
                lines.append(f"- {s}")
            lines.append("")

        if report.get("weaknesses"):
            lines.append("### ⚠️ 不足")
            for w in report["weaknesses"]:
                lines.append(f"- {w}")
            lines.append("")

        if report.get("suggestions"):
            lines.append("### 💡 改进建议")
            for s in report["suggestions"]:
                lines.append(f"- {s}")
            lines.append("")

        if report.get("detailed_feedback"):
            lines.append(f"### 详细反馈\n{report['detailed_feedback']}\n")

        return "\n".join(lines)
