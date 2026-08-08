from __future__ import annotations

from pathlib import Path
import re


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

DOC_HINTS = {
    "Reports": ["analyticshub"],
    "Dashboard": ["analyticshub"],
    "Exports": ["analyticshub"],
    "Data Ingestion": ["databridge-pro"],
    "Data Sources": ["analyticshub", "databridge-pro"],
    "Connectors": ["databridge-pro", "cloudsync"],
    "Authentication": ["authentication-sso", "securevault"],
    "SSO": ["authentication-sso"],
    "Permissions": ["authentication-sso", "securevault"],
    "Pipeline Monitoring": ["databridge-pro", "performance-and-integrations"],
    "Billing": ["billing-and-plans"],
    "Onboarding": ["onboarding-guide"],
}


def _words(text: str) -> list[str]:
    return [word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS and len(word) > 1]


def find_best_kb_match(query: str, kb_dir: str | Path, product_area: str | None = None) -> dict[str, str] | None:
    base = Path(kb_dir)
    if not base.exists():
        return None

    query_words = set(_words(query))
    files = sorted(base.rglob("*.md"))

    # If we already know the product area, only inspect the most likely docs.
    if product_area in DOC_HINTS:
        hints = DOC_HINTS[product_area]
        preferred = [path for path in files if any(hint in path.stem.lower() for hint in hints)]
        if preferred:
            files = preferred

    best_score = 0
    best_title = ""
    best_content = ""

    for path in files:
        content = path.read_text(encoding="utf-8")
        title = _title_from_markdown(path, content)
        title_words = set(_words(title))
        content_words = set(_words(content))

        # Title hits count more than body hits.
        score = (2 * len(query_words & title_words)) + len(query_words & content_words)
        if score > best_score:
            best_score = score
            best_title = title
            best_content = content

    if best_score < 2:
        return None

    return {
        "title": best_title,
        "excerpt": _excerpt(best_content, query),
    }


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

