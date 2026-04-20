import os
import logging
from typing import Optional
from enum import Enum
import numpy as np
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    QA = "qa"
    RESUME = "resume"
    INTERVIEW = "interview"
    CODE = "code"


INTENT_LABEL_NAMES_ZH = {
    AgentType.QA: "智能问答",
    AgentType.RESUME: "简历审查",
    AgentType.INTERVIEW: "模拟面试",
    AgentType.CODE: "代码检查",
}

INTENT_DESCRIPTIONS = {
    AgentType.QA: [
        "我想问一个问题",
        "什么是机器学习",
        "请解释一下Python",
        "这个知识点是什么意思",
        "帮我解答一个问题",
        "课程内容讲解",
        "学习资料查询",
        "技术概念解释",
    ],
    AgentType.RESUME: [
        "帮我看看简历",
        "审查一下我的简历",
        "简历有什么问题",
        "优化我的简历",
        "简历修改建议",
        "检查简历格式",
        "简历内容评估",
    ],
    AgentType.INTERVIEW: [
        "模拟面试",
        "我想练习面试",
        "面试模拟",
        "进行一次面试练习",
        "帮我准备面试",
        "面试问题练习",
        "技术面试模拟",
    ],
    AgentType.CODE: [
        "检查我的代码",
        "代码有什么问题",
        "帮我调试代码",
        "优化这段代码",
        "代码审查",
        "找出代码bug",
        "代码质量检查",
    ],
}

_model: Optional[any] = None
_intent_embeddings: Optional[dict] = None
_model_available: Optional[bool] = None


def _get_model():
    global _model, _model_available
    if _model_available is False:
        logger.debug("意图分类模型不可用，跳过加载")
        return None
    if _model is None:
        try:
            logger.info(f"开始加载意图分类模型: {settings.INTENT_CLASSIFIER_MODEL}")
            if settings.HF_MIRROR_URL:
                os.environ["HF_ENDPOINT"] = settings.HF_MIRROR_URL
                logger.info(f"使用HuggingFace镜像: {settings.HF_MIRROR_URL}")
            
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.INTENT_CLASSIFIER_MODEL)
            _model_available = True
            logger.info("意图分类模型加载成功")
        except Exception as e:
            logger.warning(f"意图分类模型加载失败，将使用降级方案: {e}")
            _model_available = False
            return None
    return _model


def _get_intent_embeddings():
    global _intent_embeddings
    if _intent_embeddings is None:
        model = _get_model()
        if model is None:
            return None
        logger.info("开始计算意图描述的嵌入向量")
        _intent_embeddings = {}
        for agent_type, descriptions in INTENT_DESCRIPTIONS.items():
            embeddings = model.encode(descriptions, convert_to_numpy=True)
            _intent_embeddings[agent_type] = embeddings
        logger.info(f"意图嵌入向量计算完成，共 {len(_intent_embeddings)} 个意图类型")
    return _intent_embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _fallback_classify_intent(query: str) -> AgentType:
    logger.info(f"使用关键词降级方案进行意图分类: {query[:30]}...")
    query_lower = query.lower()
    
    resume_keywords = ["简历", "简历审查", "简历优化", "简历修改"]
    for kw in resume_keywords:
        if kw in query_lower:
            logger.info(f"关键词匹配 '{kw}' -> 意图: {INTENT_LABEL_NAMES_ZH[AgentType.RESUME]}")
            return AgentType.RESUME
    
    interview_keywords = ["面试", "模拟面试", "面试练习", "面试准备"]
    for kw in interview_keywords:
        if kw in query_lower:
            logger.info(f"关键词匹配 '{kw}' -> 意图: {INTENT_LABEL_NAMES_ZH[AgentType.INTERVIEW]}")
            return AgentType.INTERVIEW
    
    code_keywords = ["代码", "代码检查", "代码审查", "调试", "bug", "优化代码"]
    for kw in code_keywords:
        if kw in query_lower:
            logger.info(f"关键词匹配 '{kw}' -> 意图: {INTENT_LABEL_NAMES_ZH[AgentType.CODE]}")
            return AgentType.CODE
    
    logger.info(f"无关键词匹配 -> 默认意图: {INTENT_LABEL_NAMES_ZH[AgentType.QA]}")
    return AgentType.QA


async def classify_intent(query: str) -> AgentType:
    try:
        model = _get_model()
        intent_embeddings = _get_intent_embeddings()
        
        if model is None or intent_embeddings is None:
            logger.info("模型不可用，使用降级方案")
            return _fallback_classify_intent(query)
        
        logger.debug(f"开始意图分类: {query[:50]}...")
        query_embedding = model.encode([query], convert_to_numpy=True)[0]
        
        scores = {}
        for agent_type, embeddings in intent_embeddings.items():
            similarities = [_cosine_similarity(query_embedding, emb) for emb in embeddings]
            avg_score = sum(similarities) / len(similarities)
            scores[agent_type] = avg_score
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        logger.info(
            f"意图分类结果: {INTENT_LABEL_NAMES_ZH[best_intent]} "
            f"(score={best_score:.3f}, all_scores={{{', '.join(f'{INTENT_LABEL_NAMES_ZH[k]}:{v:.3f}' for k, v in scores.items())}}})"
        )
        
        return best_intent
    except Exception as e:
        logger.error(f"意图分类异常: {e}，使用降级方案")
        return _fallback_classify_intent(query)
