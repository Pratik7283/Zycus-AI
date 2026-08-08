from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .models import TriageRequest, TriageResponse
from .retrieval import find_best_kb_match


DEFAULT_KB_DIR = Path("knowledge-base")


PRODUCT_RULES = [
    ("Connectors", ["connectors", "connector", "webhook", "integration"]),
    ("Data Ingestion", ["data ingestion", "ingestion", "ingest", "bulk import", "archive entries"]),
    ("Data Sources", ["data sources", "data source", "source"]),
    ("Authentication", ["authentication", "login", "password", "mfa"]),
    ("SSO", ["sso", "saml", "single sign on", "single sign-on"]),
    ("Permissions", ["permission", "permissions", "access denied", "role"]),
    ("Reports", ["reports", "reporting", "report", "analytics"]),
    ("Dashboard", ["dashboard", "widget"]),
    ("Exports", ["export", "csv", "pdf", "download"]),
    ("Pipeline Monitoring", ["outage", "down", "deployment", "incident", "failed"]),
]

ISSUE_RULES = [
    ("Data Loss", ["data loss", "missing data", "lost data", "corrupted", "deleted", "inaccessible"]),
    ("Billing", ["billing", "invoice", "charged", "refund", "payment", "pricing", "subscription"]),
    ("Performance", ["performance", "slow", "latency", "timeout", "lag", "throughput"]),
    ("Integration", ["integration", "integrations", "connector", "webhook", "sync", "api"]),
    ("Onboarding", ["onboarding", "setup", "new user", "new account", "training"]),
    ("How-To", ["how to", "how do i", "can you help", "where do i", "documentation", "guide"]),
    ("Feature Request", ["feature request", "please add", "could you add", "would like", "enhancement", "need the ability"]),
    ("Bug", ["bug", "error", "fails", "failure", "broken", "unexpected", "does not work", "doesn't work", "crash", "exception"]),
]

URGENCY_RULES = [
    ("P1", ["data loss", "security breach", "all users", "all customers", "production down", "system down", "severe outage"]),
    ("P2", ["blocked", "cannot work", "urgent", "major issue", "business impact", "error 500", "status 500", "500", "down", "fails", "failure"]),
    ("P3", ["important", "soon", "today", "delayed", "affecting", "workaround"]),
]

TEAM_BY_AREA = {
    "Connectors": "Data Platform Support",
    "Data Ingestion": "Data Platform Support",
    "Data Sources": "Data Platform Support",
    "Authentication": "Identity and Access",
    "SSO": "Identity and Access",
    "Permissions": "Identity and Access",
    "Reports": "Analytics and Reporting Support",
    "Dashboard": "Analytics and Reporting Support",
    "Exports": "Analytics and Reporting Support",
    "Pipeline Monitoring": "Product Engineering",
}


def triage_ticket(ticket: str | dict[str, Any] | TriageRequest, kb_dir: str | Path = DEFAULT_KB_DIR) -> TriageResponse:
    request = _normalize_ticket(ticket)
    subject = request.subject or ""
    body = request.body or ""
    text = (request.text or f"{subject} {body}").strip()
    lowered = text.lower()

    product_area, product_reason = _match_rule(lowered, PRODUCT_RULES, "Unknown", "Product area could not be identified.")
    issue_category, issue_reason = _match_rule(lowered, ISSUE_RULES, "Bug", "Issue category defaulted to Bug.")
    urgency_tier, urgency_reason = _match_urgency(lowered)
    recommended_team = TEAM_BY_AREA.get(product_area, "Product Engineering")
    kb_match = find_best_kb_match(text, kb_dir, product_area)

    reasoning = [
        product_reason,
        issue_reason,
        urgency_reason,
        f"Recommended responder team: {recommended_team}.",
    ]
    if kb_match:
        reasoning.append(f"Matched knowledge-base doc: {kb_match['title']}.")
    else:
        reasoning.append("No strong knowledge-base match found.")

    draft_response = _draft_response(subject, product_area, issue_category, urgency_tier, recommended_team, kb_match)

    confidence = 0.5
    if product_area != "Unknown":
        confidence += 0.15
    if issue_category != "Bug":
        confidence += 0.1
    if urgency_tier != "P4":
        confidence += 0.1
    if kb_match:
        confidence += 0.15

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


def _match_rule(text: str, rules: list[tuple[str, list[str]]], default_label: str, default_reason: str) -> tuple[str, str]:
    for label, keywords in rules:
        for keyword in keywords:
            if keyword in text:
                return label, f"{label} matched because the ticket mentions '{keyword}'."
    return default_label, default_reason


def _match_urgency(text: str) -> tuple[str, str]:
    for tier, keywords in URGENCY_RULES:
        for keyword in keywords:
            if keyword in text:
                return tier, f"Urgency set to {tier} because the ticket mentions '{keyword}'."
    return "P4", "No strong urgency signal found, so the ticket defaults to P4."


def _draft_response(
    subject: str,
    product_area: str,
    issue_category: str,
    urgency_tier: str,
    recommended_team: str,
    kb_match: Optional[dict[str, str]],
) -> str:
    parts = [
        "Thanks for reaching out.",
        f"We classified this as a {urgency_tier} {issue_category} related to {product_area}.",
        f"I am routing this to {recommended_team}.",
    ]
    if kb_match:
        parts.append(f"A relevant knowledge-base article is {kb_match['title']}.")
    if subject:
        parts.append(f"We are looking at: {subject}.")
    parts.append("If you can share an error message, timestamp, or screenshot, that will help us move faster.")
    return " ".join(parts)

