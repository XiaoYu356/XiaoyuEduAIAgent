import logging
import re
import asyncio
import hashlib
from typing import AsyncIterator
from langgraph.graph import StateGraph, END
import json

from app.agents.base import BaseAgent, AgentState
from app.services.llm.factory import LLMFactory
from app.mcp.judge0.client import execute_code
from app.core.config import get_settings

logger = logging.getLogger(__name__)

CODE_SYSTEM_PROMPT = """你是一个专业的代码审查专家。你需要分析用户提交的代码，识别错误并提供改进建议。

你的分析包括：
1. 语法错误检测 - 检查代码是否存在语法问题
2. 逻辑错误识别 - 分析代码逻辑是否正确
3. 算法复杂度分析 - 评估时间和空间复杂度
4. 代码风格建议 - 提供代码风格改进建议

输出格式要求：
- 使用结构化错误标签，如"空指针异常→数组越界→时间复杂度O(n²)"
- 提供具体的修改建议和修改后的代码"""

CODE_ANALYSIS_PROMPT = """请分析以下{language}代码：

```{language}
{code}
```

沙箱执行结果：
{execution_result}

请以JSON格式返回分析结果：
{{
  "has_error": true/false,
  "error_types": ["错误类型1", "错误类型2"],
  "error_tags": "结构化错误标签（如：语法错误→缩进错误→时间复杂度O(n²)）",
  "syntax_errors": [
    {{
      "line": 行号,
      "description": "错误描述",
      "original": "原始代码",
      "fix": "修复代码"
    }}
  ],
  "logic_errors": [
    {{
      "description": "逻辑错误描述",
      "original": "原始代码",
      "fix": "修复代码",
      "explanation": "修复说明"
    }}
  ],
  "complexity_analysis": {{
    "time_complexity": "O(?)",
    "space_complexity": "O(?)",
    "suggestion": "优化建议"
  }},
  "style_suggestions": [
    {{
      "description": "风格建议",
      "original": "原始代码",
      "improved": "改进代码"
    }}
  ],
  "improved_code": "完整改进后的代码",
  "summary": "总体评价"
}}"""

CODE_STATIC_ANALYSIS_PROMPT = """请对以下{language}代码进行静态分析（沙箱服务暂时不可用，仅进行静态代码分析）：

```{language}
{code}
```

请以JSON格式返回分析结果：
{{
  "has_error": true/false,
  "error_types": ["错误类型1", "错误类型2"],
  "error_tags": "结构化错误标签（如：语法错误→缩进错误→时间复杂度O(n²)）",
  "syntax_errors": [
    {{
      "line": 行号,
      "description": "错误描述",
      "original": "原始代码",
      "fix": "修复代码"
    }}
  ],
  "logic_errors": [
    {{
      "description": "逻辑错误描述",
      "original": "原始代码",
      "fix": "修复代码",
      "explanation": "修复说明"
    }}
  ],
  "complexity_analysis": {{
    "time_complexity": "O(?)",
    "space_complexity": "O(?)",
    "suggestion": "优化建议"
  }},
  "style_suggestions": [
    {{
      "description": "风格建议",
      "original": "原始代码",
      "improved": "改进代码"
    }}
  ],
  "improved_code": "完整改进后的代码",
  "summary": "总体评价（静态分析，建议稍后重试沙箱执行）"
}}"""

CODE_STREAM_ANALYSIS_PROMPT = """请分析以下{language}代码，直接输出Markdown格式的检查报告：

```{language}
{code}
```

沙箱执行结果：
{execution_result}

请按以下格式输出报告（直接输出Markdown，不要用JSON）：

## 🔍 代码检查报告

**错误标签**：`[结构化错误标签]`

### 错误分析
[如果有错误，列出语法错误和逻辑错误，包括行号、描述、原始代码和修复代码]

### 复杂度分析
- 时间复杂度：O(?)
- 空间复杂度：O(?)
- 优化建议：[建议内容]

### 风格建议
[列出代码风格改进建议]

### 改进后代码
```{language}
[改进后的完整代码]
```

### 总结
[总体评价]"""

CODE_STREAM_STATIC_ANALYSIS_PROMPT = """请对以下{language}代码进行静态分析（沙箱服务暂时不可用），直接输出Markdown格式的检查报告：

```{language}
{code}
```

请按以下格式输出报告（直接输出Markdown，不要用JSON）：

## 🔍 代码检查报告（静态分析）

**错误标签**：`[结构化错误标签]`

### 错误分析
[如果有错误，列出语法错误和逻辑错误，包括行号、描述、原始代码和修复代码]

### 复杂度分析
- 时间复杂度：O(?)
- 空间复杂度：O(?)
- 优化建议：[建议内容]

### 风格建议
[列出代码风格改进建议]

### 改进后代码
```{language}
[改进后的完整代码]
```

### 总结
[总体评价（静态分析，建议稍后重试沙箱执行）]"""

CODE_EXECUTION_TIMEOUT = 15


def _extract_json(text: str) -> dict:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def _compute_code_hash(code: str, language: str) -> str:
    return hashlib.sha256(f"{language}:{code}".encode()).hexdigest()


class CodeAgent(BaseAgent):
    agent_type = "code"
    agent_name = "代码检查专家"
    agent_description = "通过沙箱执行代码，识别语法/逻辑/复杂度问题，输出结构化错误标签"

    async def _execute_code(self, state: AgentState) -> AgentState:
        code = state["query"]
        if state.get("context", {}).get("code"):
            code = state["context"]["code"]
        language = state.get("context", {}).get("language", "python")
        
        logger.info(f"开始执行代码: language={language}, code_length={len(code)}")

        try:
            result = await asyncio.wait_for(
                execute_code(code, language),
                timeout=CODE_EXECUTION_TIMEOUT,
            )
            state["context"]["execution_result"] = result
            state["context"]["sandbox_available"] = True
            logger.info(f"代码执行完成: status={result.get('status')}, time={result.get('time')}s, memory={result.get('memory')}KB")
        except asyncio.TimeoutError:
            logger.warning(f"代码执行超时: timeout={CODE_EXECUTION_TIMEOUT}s")
            state["context"]["execution_result"] = {
                "status": "Time Limit Exceeded",
                "stderr": f"代码执行超时（超过{CODE_EXECUTION_TIMEOUT}秒），可能存在死循环或效率问题",
                "stdout": "",
                "time": f"{CODE_EXECUTION_TIMEOUT}",
                "memory": 0,
            }
            state["context"]["sandbox_available"] = True
        except Exception as e:
            logger.warning(f"代码执行失败: {e}")
            state["context"]["execution_result"] = {
                "status": "Sandbox Unavailable",
                "stderr": f"沙箱服务暂时不可用: {str(e)}",
                "stdout": "",
                "time": "0",
                "memory": 0,
            }
            state["context"]["sandbox_available"] = False

        return state

    async def _analyze(self, state: AgentState) -> AgentState:
        code = state["query"]
        if state.get("context", {}).get("code"):
            code = state["context"]["code"]
        language = state.get("context", {}).get("language", "python")
        exec_result = state.get("context", {}).get("execution_result", {})
        sandbox_available = state.get("context", {}).get("sandbox_available", True)
        settings = get_settings()

        logger.info(f"开始分析代码: language={language}, sandbox_available={sandbox_available}, model={settings.CODE_ANALYSIS_MODEL}")
        
        try:
            if sandbox_available:
                exec_text = f"状态: {exec_result.get('status', 'Unknown')}\n"
                if exec_result.get("stdout"):
                    exec_text += f"标准输出: {exec_result['stdout']}\n"
                if exec_result.get("stderr"):
                    exec_text += f"错误输出: {exec_result['stderr']}\n"
                if exec_result.get("compile_output"):
                    exec_text += f"编译输出: {exec_result['compile_output']}\n"
                exec_text += f"执行时间: {exec_result.get('time', '0')}s\n"
                exec_text += f"内存使用: {exec_result.get('memory', 0)}KB"
                
                prompt = CODE_ANALYSIS_PROMPT.format(
                    language=language, code=code, execution_result=exec_text
                )
            else:
                prompt = CODE_STATIC_ANALYSIS_PROMPT.format(language=language, code=code)
            
            result = await LLMFactory.chat(
                messages=[
                    {"role": "system", "content": CODE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model_name=settings.CODE_ANALYSIS_MODEL,
                temperature=0.1,
            )
            
            analysis = _extract_json(result.strip())
            if analysis is None:
                logger.warning(f"JSON解析失败，使用正则提取: {result[:100]}...")
                analysis = {
                    "has_error": True,
                    "error_types": ["分析结果解析失败"],
                    "error_tags": "解析失败",
                    "summary": result,
                }
            
            state["context"]["analysis"] = analysis
            logger.info(f"代码分析完成: has_error={analysis.get('has_error')}, error_types={analysis.get('error_types', [])}")
        except Exception as e:
            logger.error(f"代码分析异常: {e}")
            state["context"]["analysis"] = {
                "has_error": True,
                "error_types": ["分析失败"],
                "error_tags": "分析失败",
                "summary": f"代码分析过程出现异常: {str(e)}",
            }

        return state

    async def _format_output(self, state: AgentState) -> AgentState:
        analysis = state.get("context", {}).get("analysis", {})
        output_parts = []

        output_parts.append("🔍 **代码检查报告**\n")

        error_tags = analysis.get("error_tags", "无错误")
        output_parts.append(f"**错误标签**：`{error_tags}`\n")

        if analysis.get("has_error"):
            output_parts.append("❌ **发现错误**\n")

            for err in analysis.get("syntax_errors", []):
                output_parts.append(f"- 语法错误（第{err.get('line', '?')}行）：{err.get('description', '')}")
                if err.get("original"):
                    output_parts.append(f"  原始：`{err['original']}`")
                if err.get("fix"):
                    output_parts.append(f"  修复：`{err['fix']}`")

            for err in analysis.get("logic_errors", []):
                output_parts.append(f"- 逻辑错误：{err.get('description', '')}")
                if err.get("explanation"):
                    output_parts.append(f"  说明：{err['explanation']}")
                if err.get("fix"):
                    output_parts.append(f"  修复：`{err['fix']}`")
        else:
            output_parts.append("✅ **未发现语法和逻辑错误**\n")

        complexity = analysis.get("complexity_analysis", {})
        if complexity:
            output_parts.append(f"\n📊 **复杂度分析**：")
            output_parts.append(f"- 时间复杂度：{complexity.get('time_complexity', 'N/A')}")
            output_parts.append(f"- 空间复杂度：{complexity.get('space_complexity', 'N/A')}")
            if complexity.get("suggestion"):
                output_parts.append(f"- 优化建议：{complexity['suggestion']}")

        style_suggestions = analysis.get("style_suggestions", [])
        if style_suggestions:
            output_parts.append(f"\n💡 **风格建议**：")
            for s in style_suggestions:
                output_parts.append(f"- {s.get('description', '')}")
                if s.get("improved"):
                    output_parts.append(f"  改进：`{s['improved']}`")

        if analysis.get("improved_code"):
            output_parts.append(f"\n📝 **改进后代码**：\n```{state.get('context', {}).get('language', 'python')}\n{analysis['improved_code']}\n```")

        if analysis.get("summary"):
            output_parts.append(f"\n📋 **总结**：{analysis['summary']}")

        state["final_answer"] = "\n".join(output_parts)
        logger.info(f"输出格式化完成，报告长度: {len(state['final_answer'])}")
        return state

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("execute_code", self._execute_code)
        graph.add_node("analyze", self._analyze)
        graph.add_node("format_output", self._format_output)

        graph.set_entry_point("execute_code")
        graph.add_edge("execute_code", "analyze")
        graph.add_edge("analyze", "format_output")
        graph.add_edge("format_output", END)

        return graph.compile()

    async def run(self, state: AgentState) -> AgentState:
        if "context" not in state:
            state["context"] = {}
        graph = self._build_graph()
        result = await graph.ainvoke(state)
        return result

    async def stream(self, state: AgentState) -> AsyncIterator[str]:
        if "context" not in state:
            state["context"] = {}
        
        code = state["query"]
        if state.get("context", {}).get("code"):
            code = state["context"]["code"]
        language = state.get("context", {}).get("language", "python")
        settings = get_settings()
        
        yield "⏳ **正在提交代码到沙箱执行...**\n\n"
        
        state = await self._execute_code(state)
        
        exec_result = state.get("context", {}).get("execution_result", {})
        exec_status = exec_result.get("status", "Unknown")
        sandbox_available = state.get("context", {}).get("sandbox_available", True)
        
        if exec_status == "Time Limit Exceeded":
            yield "⚠️ **代码执行超时**\n\n"
        elif exec_status == "Sandbox Unavailable":
            yield "⚠️ **沙箱服务暂时不可用，将进行静态代码分析**\n\n"
        elif exec_status == "Accepted":
            yield f"✅ **代码执行成功**（耗时: {exec_result.get('time', '0')}s, 内存: {exec_result.get('memory', 0)}KB）\n\n"
        else:
            yield f"⚠️ **代码执行状态**: {exec_status}\n\n"
        
        if sandbox_available:
            yield "🤖 **正在分析代码...**\n\n"
            exec_text = f"状态: {exec_result.get('status', 'Unknown')}\n"
            if exec_result.get("stdout"):
                exec_text += f"标准输出: {exec_result['stdout']}\n"
            if exec_result.get("stderr"):
                exec_text += f"错误输出: {exec_result['stderr']}\n"
            if exec_result.get("compile_output"):
                exec_text += f"编译输出: {exec_result['compile_output']}\n"
            exec_text += f"执行时间: {exec_result.get('time', '0')}s\n"
            exec_text += f"内存使用: {exec_result.get('memory', 0)}KB"
            prompt = CODE_STREAM_ANALYSIS_PROMPT.format(
                language=language, code=code, execution_result=exec_text
            )
        else:
            yield "🤖 **正在进行静态代码分析...**\n\n"
            prompt = CODE_STREAM_STATIC_ANALYSIS_PROMPT.format(language=language, code=code)
        
        async for chunk in LLMFactory.chat_stream(
            messages=[
                {"role": "system", "content": CODE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model_name=settings.CODE_ANALYSIS_MODEL,
            temperature=0.1,
        ):
            yield chunk
        
        state["final_answer"] = "完成"
        state["context"]["code_hash"] = _compute_code_hash(code, language)
