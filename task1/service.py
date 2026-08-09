from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .models import TriageRequest, TriageResponse
from .retrieval import find_best_kb_match

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import get_llm_client

logger = logging.getLogger(__name__)


DEFAULT_KB_DIR = Path("knowledge-base")

CLASSIFICATION_SYSTEM_PROMPT = """You are a support ticket triage agent. Given a support ticket, 
classify it into:
- product_area: one of [Reporting, Authentication, Data Ingestion, 
  Billing, Integrations, Performance, General]
- issue_category: one of [Bug, Feature Request, Access Issue, 
  Performance, Data Quality, General]
- urgency_tier: one of [P1, P2, P3, P4]
- reasoning: 2-3 sentences explaining your classification

Respond ONLY in valid JSON. No extra text."""

DRAFT_RESPONSE_SYSTEM_PROMPT = """You are a support agent. Write a professional first response 
to this ticket. Keep it under 100 words. Be empathetic and clear.
Reference this KB article if relevant: {kb_excerpt}"""

TEAM_BY_AREA = {
    "Reporting": "Analytics and Reporting Support",
    "Authentication": "Identity and Access",
    "Data Ingestion": "Data Platform Support",
    "Billing": "Billing Support",
    "Integrations": "Data Platform Support",
    "Performance": "Product Engineering",
    "General": "Product Engineering",
}


def triage_ticket(ticket: str | dict[str, Any] | TriageRequest, kb_dir: str | Path = DEFAULT_KB_DIR) -> TriageResponse:
    request = _normalize_ticket(ticket)
    subject = request.subject or ""
    body = request.body or ""
    text = (request.text or f"{subject} {body}").strip()

    llm_result = _llm_classify_ticket(subject, body)
    product_area = llm_result.get("product_area", "General")
    issue_category = llm_result.get("issue_category", "General")
    urgency_tier = llm_result.get("urgency_tier", "P4")
    llm_reasoning = llm_result.get("reasoning", "")
    
    recommended_team = TEAM_BY_AREA.get(product_area, "Product Engineering")
    kb_match = find_best_kb_match(text, kb_dir)

    reasoning = [
        f"LLM classified as {product_area}. {llm_reasoning}",
        f"Issue category: {issue_category}",
        f"Urgency: {urgency_tier}",
        f"Recommended responder team: {recommended_team}.",
    ]
    if kb_match:
        reasoning.append(f"Matched knowledge-base doc: {kb_match['title']}.")
    else:
        reasoning.append("No strong knowledge-base match found.")

    draft_response = _llm_draft_response(subject, product_area, issue_category, urgency_tier, kb_match)

    confidence = 0.7
    if kb_match:
        confidence += 0.2

    return TriageResponse(
        product_area=product_area,
        issue_category=issue_category,
        urgency_tier=urgency_tier,
        reasoning=reasoning,
        known_issue_match=kb_match is not None,
        matched_kb_doc=kb_match["title"] if kb_match else None,
        matched_kb_excerpt=kb_match["excerpt"] if kb_match else None,
        recommended_team=recommended_team,
        draft_first_response=draft_response,
        confidence=round(min(confidence, 0.98), 2),
        raw_input=request.model_dump(),
    )


def _normalize_ticket(ticket: str | dict[str, Any] | TriageRequest) -> TriageRequest:
    if isinstance(ticket, TriageRequest):
        return ticket
    if isinstance(ticket, str):
        return TriageRequest(text=ticket)
    if isinstance(ticket, dict):
        return TriageRequest(subject=ticket.get("subject"), body=ticket.get("body"), text=ticket.get("text"))
    raise TypeError("ticket must be a string, dict, or TriageRequest")


def _llm_classify_ticket(subject: str, body: str) -> dict[str, str]:
    """Use LLM to classify ticket.
    
    Args:
        subject: Ticket subject
        body: Ticket body
        
    Returns:
        Dictionary with product_area, issue_category, urgency_tier, reasoning
    """
    llm_client = get_llm_client()
    
    user_prompt = f"""Ticket subject: {subject}
Ticket body: {body}"""
    
    result = llm_client.call_llm(
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=512,
        prompt_version="v1.0"
    )
    
    return result


def _llm_draft_response(
    subject: str,
    product_area: str,
    issue_category: str,
    urgency_tier: str,
    kb_match: Optional[dict[str, str]],
) -> str:
    """Use LLM to generate a professional draft response.
    
    Args:
        subject: Ticket subject
        product_area: Classified product area
        issue_category: Classified issue category
        urgency_tier: Classified urgency tier
        kb_match: Knowledge base match if available
        
    Returns:
        Draft response text from LLM
    """
    llm_client = get_llm_client()
    
    kb_excerpt = kb_match["excerpt"] if kb_match else "None"
    system_prompt = DRAFT_RESPONSE_SYSTEM_PROMPT.format(kb_excerpt=kb_excerpt)
    
    user_prompt = f"""Ticket subject: {subject}
Classification: {urgency_tier} {issue_category} related to {product_area}"""
    
    result = llm_client.call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=256,
        prompt_version="v1.0"
    )
    
    if isinstance(result, dict) and "text" in result:
        return result["text"]
    return str(result)
