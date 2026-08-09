from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any
from functools import lru_cache
import numpy as np

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


WORD_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "do",
    "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "is", "it", "its",
    "me", "my", "not", "of", "on", "or", "our", "please", "should", "the", "their", "there",
    "they", "this", "to", "was", "we", "what", "when", "where", "which", "who", "will", "with",
    "would", "you", "your", "help", "need", "like", "want", "know", "thanks", "thank", "hi",
    "hello", "team", "issue", "problem", "support", "customer", "ticket", "question", "understand",
    "today", "currently", "one", "all", "after", "before", "into", "than", "then", "more", "less",
    "about", "that", "we're", "weve", "im", "ive",
}



@lru_cache(maxsize=1)
def _get_embedding_model() -> SentenceTransformer:
    """Load and cache the all-MiniLM-L6-v2 model with CPU-only mode."""
    try:
        return SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise


def _words(text: str) -> list[str]:
    return [word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS and len(word) > 1]


def find_best_kb_match(query: str, kb_dir: str | Path, product_area: str | None = None) -> dict[str, str] | None:
    """Use all-MiniLM-L6-v2 embeddings to find the best KB article match (RAG pipeline).
    
    Args:
        query: The ticket text
        kb_dir: Directory containing KB articles
        product_area: Optional product area hint (not used in embeddings mode)
        
    Returns:
        Dictionary with title and excerpt of best match, or None
    """
    base = Path(kb_dir)
    if not base.exists():
        return None

    files = sorted(base.rglob("*.md"))
    
    if not files:
        return None
    
    return _sentence_embeddings_rag_retrieval(query, files, base)


def _title_from_markdown(path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("_", " ").title()


def _excerpt(content: str, query: str, max_chars: int = 220) -> str:
    query_words = _words(query)
    lowered = content.lower()

    for word in query_words:
        index = lowered.find(word)
        if index != -1:
            start = max(0, index - 80)
            end = min(len(content), index + max_chars)
            return content[start:end].strip()

    return content[:max_chars].strip()


def _sentence_embeddings_rag_retrieval(query: str, files: list[Path], kb_dir: Path) -> dict[str, str] | None:
    """Use all-MiniLM-L6-v2 sentence embeddings for RAG retrieval pipeline.
    
    Args:
        query: The ticket text
        files: List of all KB article files
        kb_dir: Base directory for KB
        
    Returns:
        Dictionary with title and excerpt of best match, or None
    """
    try:
        model = _get_embedding_model()
        
        documents = []
        doc_info = []
        
        for path in files:
            content = path.read_text(encoding="utf-8")
            title = _title_from_markdown(path, content)
            doc_text = f"{title}. {content[:500]}"
            documents.append(doc_text)
            doc_info.append({"path": path, "content": content, "title": title})
        
        doc_embeddings = model.encode(documents, convert_to_numpy=True)
        
        query_embedding = model.encode([query], convert_to_numpy=True)
        
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
        
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        best_doc = doc_info[best_idx]
        
        logger.info(f"RAG retrieval: Best match '{best_doc['title']}' with similarity {best_score:.3f}")
        
        return {
            "title": best_doc["title"],
            "excerpt": _excerpt(best_doc["content"], query),
        }
        
    except Exception as e:
        logger.error(f"Sentence embeddings RAG retrieval failed: {e}")
        return _fallback_keyword_match(query, files)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
    """Calculate cosine similarity between vectors.
    
    Args:
        vec1: First vector(s)
        vec2: Second vector(s)
        
    Returns:
        Cosine similarity matrix
    """
    dot_product = np.dot(vec1, vec2.T)
    norm1 = np.linalg.norm(vec1, axis=1, keepdims=True)
    norm2 = np.linalg.norm(vec2, axis=1, keepdims=True)
    return dot_product / (norm1 * norm2.T + 1e-8)


def _fallback_keyword_match(query: str, files: list[Path]) -> dict[str, str] | None:
    """Fallback keyword-based matching if embeddings fail.
    
    Args:
        query: The ticket text
        files: List of all KB article files
        
    Returns:
        Dictionary with title and excerpt of best match, or None
    """
    query_words = set(_words(query))
    best_score = 0
    best_match = None
    
    for path in files:
        content = path.read_text(encoding="utf-8").lower()
        title = _title_from_markdown(path, content)
        
        matches = sum(1 for word in query_words if word in content)
        score = matches / len(query_words) if query_words else 0
        
        if score > best_score and score > 0.05:
            best_score = score
            best_match = {
                "title": title,
                "excerpt": _excerpt(content, query),
            }
    
    return best_match
