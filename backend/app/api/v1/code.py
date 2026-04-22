import hashlib
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.redis import get_redis
from app.models.database import User, CodeCheckRecord
from app.models.schemas import ResponseBase, CodeCheckRequest
from app.api.deps import get_current_user
from app.agents.code.agent import CodeAgent, _compute_code_hash
from app.mcp.judge0.client import get_supported_languages, check_health

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/code", tags=["代码检查"])

CACHE_EXPIRE_SECONDS = 3600 * 24  # 24小时


async def _get_cached_result(code_hash: str, user_id: int) -> dict | None:
    try:
        redis = await get_redis()
        cache_key = f"code_check:{user_id}:{code_hash}"
        cached = await redis.get(cache_key)
        if cached:
            await redis.expire(cache_key, CACHE_EXPIRE_SECONDS)
            logger.info(f"Redis缓存命中并刷新过期时间: {cache_key[:40]}...")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis读取失败: {e}")
    return None


async def _set_cache_result(code_hash: str, user_id: int, result: dict):
    try:
        redis = await get_redis()
        cache_key = f"code_check:{user_id}:{code_hash}"
        await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=CACHE_EXPIRE_SECONDS)
        logger.info(f"Redis缓存已设置: {cache_key[:40]}...")
    except Exception as e:
        logger.warning(f"Redis写入失败: {e}")


@router.get("/languages", response_model=ResponseBase)
async def get_languages():
    languages = get_supported_languages()
    return ResponseBase(data=languages)


@router.get("/health", response_model=ResponseBase)
async def get_health():
    health = await check_health()
    return ResponseBase(data=health)


@router.post("/check")
async def check_code(
    data: CodeCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code_hash = _compute_code_hash(data.code, data.language)
    
    cached_result = await _get_cached_result(code_hash, current_user.id)
    
    if cached_result and cached_result.get("success", True):
        async def cached_generator():
            cache_msg="📦 从缓存加载结果...\\n\\n"
            yield f"data: {json.dumps({'content': cache_msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'content': cached_result['final_report']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'cached': True}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            cached_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    
    agent = CodeAgent()
    state = {
        "query": data.code,
        "context": {"code": data.code, "language": data.language},
        "messages": [],
        "conversation_id": data.conversation_id or 0,
        "user_id": current_user.id,
        "agent_type": "code",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }
    
    async def event_generator():
        full_answer = ""
        exec_result_data = {}
        analysis_result_data = {}
        has_error = False
        
        try:
            async for chunk in agent.stream(state):
                full_answer += chunk
                event_data = json.dumps({"content": chunk}, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            has_error = True
            logger.error(f"代码检查异常: {e}")
            error_msg = f"\n\n❌ **检查过程中发生错误**\n\n错误信息：{str(e)}\n\n请稍后重试，或检查代码是否有问题。"
            yield f"data: {json.dumps({'content': error_msg}, ensure_ascii=False)}\n\n"
            full_answer += error_msg

        try:
            exec_result_data = state.get("context", {}).get("execution_result", {})
            analysis_result_data = state.get("context", {}).get("analysis", {})
            exec_status = exec_result_data.get("status", "Unknown")
            
            if exec_status in ("Time Limit Exceeded", "Execution Failed", "Internal Error"):
                has_error = True
            
            analysis_has_error = analysis_result_data.get("has_error", False)
            if analysis_has_error:
                has_error = True
            
            record = CodeCheckRecord(
                user_id=current_user.id,
                code=data.code,
                language=data.language,
                code_hash=code_hash,
                execution_status=exec_status,
                execution_result=json.dumps(exec_result_data, ensure_ascii=False),
                analysis_result=json.dumps(analysis_result_data, ensure_ascii=False),
                final_report=full_answer,
            )
            db.add(record)
            await db.commit()
            logger.info(f"代码检查记录已保存: record_id={record.id}")
            
            if not has_error:
                await _set_cache_result(code_hash, current_user.id, {
                    "final_report": full_answer,
                    "execution_status": exec_status,
                    "record_id": record.id,
                    "success": True,
                })
            else:
                logger.info(f"检查失败，不缓存结果")
                
        except Exception as e:
            logger.error(f"保存代码检查记录失败: {e}")
            save_error_msg = "\n\n⚠️ 保存记录失败，但不影响查看结果"
            yield f"data: {json.dumps({'content': save_error_msg}, ensure_ascii=False)}\n\n"

        done_data = json.dumps({"done": True, "has_error": has_error}, ensure_ascii=False)
        yield f"data: {done_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/history", response_model=ResponseBase)
async def get_check_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CodeCheckRecord)
        .where(CodeCheckRecord.user_id == current_user.id)
        .order_by(CodeCheckRecord.created_at.desc())
        .limit(20)
    )
    records = result.scalars().all()
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "language": r.language,
            "code_preview": r.code[:100] + "..." if len(r.code) > 100 else r.code,
            "execution_status": r.execution_status,
            "created_at": r.created_at.isoformat(),
        })
    
    return ResponseBase(data=items)


@router.get("/history/{record_id}", response_model=ResponseBase)
async def get_check_detail(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CodeCheckRecord).where(
            CodeCheckRecord.id == record_id,
            CodeCheckRecord.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("记录不存在")
    
    return ResponseBase(data={
        "id": record.id,
        "code": record.code,
        "language": record.language,
        "execution_status": record.execution_status,
        "execution_result": json.loads(record.execution_result) if record.execution_result else {},
        "analysis_result": json.loads(record.analysis_result) if record.analysis_result else {},
        "final_report": record.final_report,
        "created_at": record.created_at.isoformat(),
    })


@router.delete("/history/{record_id}", response_model=ResponseBase)
async def delete_check_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CodeCheckRecord).where(
            CodeCheckRecord.id == record_id,
            CodeCheckRecord.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("记录不存在")
    
    await db.delete(record)
    await db.commit()
    logger.info(f"代码检查记录已删除: record_id={record_id}, user_id={current_user.id}")
    
    return ResponseBase(message="记录已删除")
