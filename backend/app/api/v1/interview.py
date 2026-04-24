import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.redis import get_redis, InterviewStateCache
from app.models.database import User, Resume, InterviewReport
from app.models.schemas import ResponseBase, InterviewStartRequest, InterviewRespondRequest, InterviewReportRequest
from app.api.deps import get_current_user
from app.agents.interview.agent import InterviewAgent

router = APIRouter(prefix="/interview", tags=["模拟面试"])
logger = logging.getLogger(__name__)


async def get_interview_cache() -> InterviewStateCache:
    redis = await get_redis()
    return InterviewStateCache(redis)


async def generate_session_id() -> int:
    redis = await get_redis()
    return await redis.incr("interview:session_id")


@router.post("/start", response_model=ResponseBase)
async def start_interview(
    data: InterviewStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume_summary = ""
    if data.resume_id:
        result = await db.execute(
            select(Resume).where(Resume.id == data.resume_id, Resume.user_id == current_user.id)
        )
        resume = result.scalar_one_or_none()
        if resume:
            resume_summary = resume.raw_text[:2000]

    session_id = await generate_session_id()

    agent = InterviewAgent()
    state = {
        "query": "开始面试",
        "context": {
            "resume_summary": resume_summary,
            "stage": "INTRO",
            "focus_areas": data.focus_areas or [],
            "weaknesses": [],
            "qa_history": [],
            "scores": [],
            "tech_count": 0,
            "project_count": 0,
            "asked_tech_questions": [],
            "asked_project_questions": [],
            "current_question": None,
        },
        "messages": [],
        "conversation_id": session_id,
        "user_id": current_user.id,
        "agent_type": "interview",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }
    agent_result = await agent.run(state)

    cache = await get_interview_cache()
    await cache.set(session_id, agent_result.get("context", {}))

    return ResponseBase(data={
        "conversation_id": session_id,
        "message": agent_result.get("final_answer", ""),
        "stage": agent_result.get("context", {}).get("stage", "INTRO"),
    })


@router.post("/respond", response_model=ResponseBase)
async def interview_respond(
    data: InterviewRespondRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache = await get_interview_cache()
    saved_context = await cache.get(data.conversation_id)

    if not saved_context:
        raise ValueError("面试会话不存在或已过期")

    agent = InterviewAgent()
    state = {
        "query": data.message,
        "context": saved_context,
        "messages": [],
        "conversation_id": data.conversation_id,
        "user_id": current_user.id,
        "agent_type": "interview",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }
    agent_result = await agent.run(state)

    new_context = agent_result.get("context", {})
    stage = new_context.get("stage", "TECH")

    await cache.set(data.conversation_id, new_context)

    return ResponseBase(data={
        "conversation_id": data.conversation_id,
        "message": agent_result.get("final_answer", ""),
        "stage": stage,
    })


@router.post("/respond/stream")
async def interview_respond_stream(
    data: InterviewRespondRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache = await get_interview_cache()
    saved_context = await cache.get(data.conversation_id)

    if not saved_context:
        raise ValueError("面试会话不存在或已过期")

    agent = InterviewAgent()
    state = {
        "query": data.message,
        "context": saved_context,
        "messages": [],
        "conversation_id": data.conversation_id,
        "user_id": current_user.id,
        "agent_type": "interview",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }

    async def event_generator():
        full_response = ""
        try:
            async for chunk in agent.stream(state):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            new_context = state.get("context", {})
            stage = new_context.get("stage", "TECH")
            await cache.set(data.conversation_id, new_context)

            yield f"data: {json.dumps({'done': True, 'stage': stage}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Interview stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/history", response_model=ResponseBase)
async def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewReport)
        .where(InterviewReport.user_id == current_user.id)
        .order_by(InterviewReport.created_at.desc())
        .limit(20)
    )
    reports = result.scalars().all()

    history = []
    for r in reports:
        radar_data = {}
        try:
            radar_data = json.loads(r.radar_data) if r.radar_data else {}
        except:
            pass

        suggestions = []
        try:
            suggestions = json.loads(r.suggestions) if r.suggestions else []
        except:
            pass

        history.append({
            "id": r.id,
            "conversation_id": r.conversation_id,
            "tech_score": r.tech_score,
            "expression_score": r.expression_score,
            "overall_score": r.overall_score,
            "radar_data": radar_data,
            "suggestions": suggestions,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return ResponseBase(data=history)


@router.get("/history/{report_id}", response_model=ResponseBase)
async def get_interview_detail(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewReport).where(
            InterviewReport.id == report_id,
            InterviewReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise ValueError("面试报告不存在")

    radar_data = {}
    try:
        radar_data = json.loads(report.radar_data) if report.radar_data else {}
    except:
        pass

    suggestions = []
    try:
        suggestions = json.loads(report.suggestions) if report.suggestions else []
    except:
        pass

    strengths = []
    weaknesses = []
    overall_comment = ""
    detailed_feedback = ""
    
    if report.report_content:
        try:
            report_json = json.loads(report.report_content)
            strengths = report_json.get("strengths", [])
            weaknesses = report_json.get("weaknesses", [])
            overall_comment = report_json.get("overall_comment", "")
            detailed_feedback = report_json.get("detailed_feedback", "")
        except:
            pass

    return ResponseBase(data={
        "id": report.id,
        "conversation_id": report.conversation_id,
        "tech_score": report.tech_score,
        "expression_score": report.expression_score,
        "overall_score": report.overall_score,
        "radar_data": radar_data,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "overall_comment": overall_comment,
        "detailed_feedback": detailed_feedback,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    })


@router.post("/report/stream")
async def stream_interview_report(
    data: InterviewReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache = await get_interview_cache()
    saved_context = await cache.get(data.conversation_id)

    if not saved_context:
        raise ValueError("面试会话不存在或已过期")

    agent = InterviewAgent()
    state = {
        "query": "",
        "context": saved_context,
        "messages": [],
        "conversation_id": data.conversation_id,
        "user_id": current_user.id,
        "agent_type": "interview",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }

    async def generate():
        full_content = ""
        async for chunk in agent.stream_report(state):
            full_content += chunk
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        report = state.get("context", {}).get("report", {})
        if report:
            interview_report = InterviewReport(
                user_id=current_user.id,
                conversation_id=None,
                tech_score=report.get("tech_score", 0),
                expression_score=report.get("expression_score", 0),
                overall_score=report.get("overall_score", 0),
                radar_data=json.dumps(report.get("radar_data", {}), ensure_ascii=False),
                report_content=state.get("final_answer", ""),
                suggestions=json.dumps(report.get("suggestions", []), ensure_ascii=False),
            )
            db.add(interview_report)
            await db.commit()
            await cache.delete(data.conversation_id)

            yield f"data: {json.dumps({'done': True, 'report': report}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'done': True, 'error': '报告解析失败，请重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/history/{report_id}", response_model=ResponseBase)
async def delete_interview_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewReport).where(
            InterviewReport.id == report_id,
            InterviewReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise ValueError("面试报告不存在")

    await db.delete(report)
    await db.commit()

    logger.info(f"Interview report deleted: {report_id}")
    return ResponseBase(message="删除成功")
