from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    subject: Optional[str] = Field(default=None, description="Ticket subject line")
    body: Optional[str] = Field(default=None, description="Ticket body text")
    text: Optional[str] = Field(default=None, description="Raw ticket text")


class TriageResponse(BaseModel):
    product_area: str
    issue_category: str
    urgency_tier: str
    reasoning: list[str]
    known_issue_match: bool
    matched_kb_doc: Optional[str] = None
    matched_kb_excerpt: Optional[str] = None
    recommended_team: str
    draft_first_response: str
    confidence: float
    raw_input: dict[str, Any]

