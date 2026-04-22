import os
import logging
from typing import Optional
import numpy as np
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_model: Optional[any] = None
_type_embeddings: Optional[dict] = None
_model_available: Optional[bool] = None

QUERY_TYPE_LABELS = {
    "chitchat": "闲聊",
    "clear": "明确问题",
    "vague": "模糊问题",
    "broad": "宽泛问题",
}

QUERY_TYPE_DESCRIPTIONS = {
    "chitchat": [
        "你好",
        "您好",
        "早上好",
        "晚上好",
        "再见",
        "拜拜",
        "谢谢",
        "感谢",
        "不好意思",
        "抱歉",
        "你是谁",
        "你叫什么",
        "你是机器人吗",
        "怎么样",
        "好吗",
        "行吗",
        "可以吗",
        "你好呀",
        "嗨",
        "哈喽",
    ],
    "clear": [
        "什么是机器学习",
        "Python中list和tuple的区别是什么",
        "如何使用面向对象编程",
        "解释一下数据库索引",
        "什么是RESTful API",
        "如何配置环境变量",
        "解释一下这个概念",
        "这个函数怎么用",
        "什么是设计模式",
        "如何优化SQL查询",
        "解释一下HTTP协议",
        "什么是微服务架构",
    ],
    "vague": [
        "那个怎么用",
        "关于机器学习的东西",
        "老师讲的那个方法",
        "之前说的那个问题",
        "这个东西是什么",
        "那个功能怎么实现",
        "刚才提到的那个",
        "这个怎么弄",
        "那个怎么搞",
        "关于这个的一些问题",
    ],
    "broad": [
        "介绍一下深度学习",
        "如何学好编程",
        "Web开发都需要学什么",
        "讲讲微服务",
        "说说数据库优化",
        "介绍一下Spring框架",
        "如何设计系统架构",
        "讲讲前端技术栈",
        "介绍一下DevOps",
        "如何进行性能优化",
    ],
}


def _get_model():
    global _model, _model_available
    if _model_available is False:
        logger.debug("问题类型分类模型不可用，跳过加载")
        return None
    if _model is None:
        try:
            logger.info(f"开始加载问题类型分类模型: {settings.INTENT_CLASSIFIER_MODEL}")
            if settings.HF_MIRROR_URL:
                os.environ["HF_ENDPOINT"] = settings.HF_MIRROR_URL
                logger.info(f"使用HuggingFace镜像: {settings.HF_MIRROR_URL}")
            
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.INTENT_CLASSIFIER_MODEL)
            _model_available = True
            logger.info("问题类型分类模型加载成功")
        except Exception as e:
            logger.warning(f"问题类型分类模型加载失败，将使用降级方案: {e}")
            _model_available = False
            return None
    return _model


def _get_type_embeddings():
    global _type_embeddings
    if _type_embeddings is None:
        model = _get_model()
        if model is None:
            return None
        logger.info("开始计算问题类型描述的嵌入向量")
        _type_embeddings = {}
        for query_type, descriptions in QUERY_TYPE_DESCRIPTIONS.items():
            embeddings = model.encode(descriptions, convert_to_numpy=True)
            _type_embeddings[query_type] = embeddings
        logger.info(f"问题类型嵌入向量计算完成，共 {len(_type_embeddings)} 个类型")
    return _type_embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _fallback_classify_query_type(query: str) -> tuple[str, float]:
    logger.info(f"使用规则降级方案进行问题类型分类: {query[:30]}...")
    
    chitchat_patterns = ["你好", "您好", "谢谢", "再见", "拜拜", "嗨", "哈喽", "怎么样", "好吗"]
    for pattern in chitchat_patterns:
        if pattern in query and len(query) <= 15:
            logger.info(f"规则匹配 '{pattern}' -> 类型: {QUERY_TYPE_LABELS['chitchat']}")
            return "chitchat", 0.9
    
    logger.info(f"无规则匹配 -> 默认类型: {QUERY_TYPE_LABELS['clear']}")
    return "clear", 0.5


def classify_query_type(query: str) -> tuple[str, float]:
    logger.info(f"classify_query_type 开始, query: {query[:30]}...")
    try:
        logger.info(f"获取模型...")
        model = _get_model()
        logger.info(f"获取类型嵌入...")
        type_embeddings = _get_type_embeddings()
        
        if model is None or type_embeddings is None:
            logger.info("模型不可用，使用降级方案")
            return _fallback_classify_query_type(query)
        
        logger.debug(f"开始问题类型分类: {query[:50]}...")
        query_embedding = model.encode([query], convert_to_numpy=True)[0]
        
        scores = {}
        for query_type, embeddings in type_embeddings.items():
            similarities = [_cosine_similarity(query_embedding, emb) for emb in embeddings]
            scores[query_type] = sum(similarities) / len(similarities)
        
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        logger.info(
            f"问题类型分类结果: {QUERY_TYPE_LABELS[best_type]} "
            f"(score={best_score:.3f}, all_scores={{{', '.join(f'{QUERY_TYPE_LABELS[k]}:{v:.3f}' for k, v in scores.items())}}})"
        )
        
        return best_type, best_score
    except Exception as e:
        logger.error(f"问题类型分类异常: {e}，使用降级方案", exc_info=True)
        return _fallback_classify_query_type(query)


async def async_classify_query_type(query: str) -> tuple[str, float]:
    return classify_query_type(query)
