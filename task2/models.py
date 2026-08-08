from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AccountBriefRequest(BaseModel):
    account_id: str = Field(..., description="Account identifier from accounts.json")


class FlaggedTicket(BaseModel):
    ticket_id: str
    created_at: str
    urgency: str
    status: str
    reason: str
    quote: str


class AccountBriefResponse(BaseModel):
    account_id: str
    company: str
    tam: str
    health_status: str
    usage_trend: str
    executive_summary: str
    open_risks_and_flagged_issues: list[str]
    recommended_talking_points: list[str]
    flagged_tickets: list[FlaggedTicket]
    data_window_days: int
    raw_account: dict[str, Any]

