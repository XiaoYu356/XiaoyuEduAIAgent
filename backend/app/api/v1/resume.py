import logging
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.core.database import get_db
from app.models.database import User, Resume
from app.models.schemas import ResponseBase
from app.api.deps import get_current_user
from app.core.minio import upload_file
from app.agents.resume.agent import ResumeAgent
from app.services.document_loaders import DocumentLoader

router = APIRouter(prefix="/resume", tags=["简历审查"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=ResponseBase)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Uploading resume: {file.filename}, content_type: {file.content_type}")

    file_data = await file.read()
    logger.info(f"File size: {len(file_data)} bytes")

    object_name = f"resumes/{current_user.id}/{file.filename}"
    await upload_file(object_name, file_data, file.content_type or "application/octet-stream")
    logger.info(f"File uploaded to MinIO: {object_name}")

    try:
        raw_text = DocumentLoader.load_from_bytes(file_data, file.filename or "")
        logger.info(f"DocumentLoader extracted {len(raw_text)} characters")
    except Exception as e:
        logger.error(f"DocumentLoader failed: {e}", exc_info=True)
        return ResponseBase(message=f"文档解析失败: {str(e)}", data={"error": str(e)})

    resume = Resume(
        user_id=current_user.id,
        file_path=object_name,
        raw_text=raw_text,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return ResponseBase(
        data={
            "resume_id": resume.id,
            "filename": file.filename,
            "text_length": len(raw_text),
        }
    )


@router.post("/review", response_model=ResponseBase)
async def review_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Reviewing resume: {resume_id}")

    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise ValueError("简历不存在")

    agent = ResumeAgent()
    state = {
        "query": resume.raw_text,
        "context": {"resume_text": resume.raw_text},
        "messages": [],
        "conversation_id": 0,
        "user_id": current_user.id,
        "agent_type": "resume",
        "intermediate_results": [],
        "final_answer": "",
        "confidence": 0.0,
        "metadata": {},
        "error": None,
    }
    agent_result = await agent.run(state)

    report = agent_result.get("context", {}).get("report", {})
    resume.review_result = agent_result.get("final_answer", "")
    resume.radar_data = json.dumps(report.get("radar_data", {}), ensure_ascii=False)
    await db.commit()

    logger.info(f"Resume review completed: {resume_id}")
    return ResponseBase(data=agent_result.get("final_answer", ""))
