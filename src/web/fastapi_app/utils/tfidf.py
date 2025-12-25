"""TF-IDF 向量工具"""
import base64
import numpy as np


def decode_tfidf(encoded_str: str) -> np.ndarray | None:
    """解码 Base64 编码的 TF-IDF 向量（小端序）"""
    if not encoded_str:
        return None
    try:
        b = base64.b64decode(encoded_str)
        vec = np.frombuffer(b, dtype="<f8")
        return vec.astype(np.float64)
    except Exception as e:
        print(f"TF-IDF 解码失败: {e}")
        return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """计算余弦相似度"""
    if vec1 is None or vec2 is None:
        return 0.0
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))
