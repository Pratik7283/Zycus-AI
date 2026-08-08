from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import re
from pathlib import Path
from typing import Any

from .models import AccountBriefRequest, AccountBriefResponse, FlaggedTicket


DATA_DIR = Path("data")
ACCOUNTS_PATH = DATA_DIR / "accounts.json"
TICKETS_PATH = DATA_DIR / "tickets.json"

RISK_KEYWORDS = [
    "cancel",
    "cancellation",
    "churn",
    "churning",
    "switch",
    "switched",
    "competing vendor",
    "renewal risk",
    "not renewing",
    "unhappy",
    "frustrated",
    "escalate",
    "escalation",
    "blocked",
    "urgent",
    "severe outage",
    "data loss",
    "cannot access",
]


@lru_cache(maxsize=1)
def load_accounts() -> list[dict[str, Any]]:
    return _load_json_file(ACCOUNTS_PATH)


@lru_cache(maxsize=1)
def load_tickets() -> list[dict[str, Any]]:
    return _load_json_file(TICKETS_PATH)


def generate_account_brief(
    request: str | dict[str, Any] | AccountBriefRequest,
    reference_date: datetime | None = None,
) -> AccountBriefResponse:
    normalized = _normalize_request(request)
    account = _find_account(normalized.account_id)
    if account is None:
        raise ValueError(f"Account not found: {normalized.account_id}")

    ref_date = reference_date or datetime.now(timezone.utc)
    recent_tickets = _get_recent_tickets(account["account_id"], ref_date, days=90)
    flagged_tickets = _flag_risk_tickets(recent_tickets)

    open_risks = _build_open_risks(account, recent_tickets, flagged_tickets, ref_date)
    talking_points = _build_talking_points(account, recent_tickets, flagged_tickets)
    summary = _build_executive_summary(account, recent_tickets, flagged_tickets, ref_date)

    return AccountBriefResponse(
        account_id=account["account_id"],
        company=account["company"],
        tam=account["tam"],
        health_status=account["health_status"],
        usage_trend=account["usage_trend"],
        executive_summary=summary,
        open_risks_and_flagged_issues=open_risks,
        recommended_talking_points=talking_points,
        flagged_tickets=flagged_tickets,
        data_window_days=90,
        raw_account=account,
    )


def _normalize_request(request: str | dict[str, Any] | AccountBriefRequest) -> AccountBriefRequest:
    if isinstance(request, AccountBriefRequest):
        return request
    if isinstance(request, str):
        return AccountBriefRequest(account_id=request)
    if isinstance(request, dict):
        return AccountBriefRequest(account_id=request["account_id"])
    raise TypeError("request must be a string, dict, or AccountBriefRequest")


def _find_account(account_id: str) -> dict[str, Any] | None:
    for account in load_accounts():
        if account["account_id"] == account_id:
            return account
    return None


def _get_recent_tickets(account_id: str, reference_date: datetime, days: int = 90) -> list[dict[str, Any]]:
    cutoff = reference_date - timedelta(days=days)
    recent = []
    for ticket in load_tickets():
        if ticket["account_id"] != account_id:
            continue
        created_at = _parse_dt(ticket["created_at"])
        if created_at >= cutoff:
            recent.append(ticket)
    return sorted(recent, key=lambda item: item["created_at"])


def _flag_risk_tickets(tickets: list[dict[str, Any]]) -> list[FlaggedTicket]:
    flagged: list[FlaggedTicket] = []
    for ticket in tickets:
        text = f"{ticket['subject']} {ticket['body']}".lower()
        matched_keyword = _first_matching_keyword(text, RISK_KEYWORDS)
        if matched_keyword:
            reason = f"Churn or escalation signal found: '{matched_keyword}'."
            quote = _extract_quote(ticket["subject"], ticket["body"], matched_keyword)
            flagged.append(
                FlaggedTicket(
                    ticket_id=ticket["ticket_id"],
                    created_at=ticket["created_at"],
                    urgency=ticket["urgency"],
                    status=ticket["status"],
                    reason=reason,
                    quote=quote,
                )
            )
            continue

        if ticket["urgency"] in {"P1", "P2"}:
            reason = f"High-priority ticket with urgency {ticket['urgency']} and status {ticket['status']}."
            quote = _extract_quote(ticket["subject"], ticket["body"], "")
            flagged.append(
                FlaggedTicket(
                    ticket_id=ticket["ticket_id"],
                    created_at=ticket["created_at"],
                    urgency=ticket["urgency"],
                    status=ticket["status"],
                    reason=reason,
                    quote=quote,
                )
            )
    return flagged


def _build_open_risks(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
    reference_date: datetime,
) -> list[str]:
    risks: list[str] = []

    if account["health_status"] in {"At Risk", "Churning"}:
        risks.append(f"Account health is marked {account['health_status']}.")
    if account["usage_trend"] in {"Declining", "Inactive"}:
        risks.append(f"Usage trend is {account['usage_trend']}, which suggests adoption is weakening.")
    if account.get("p1_tickets_last_30d", 0) > 0:
        risks.append(f"There were {account['p1_tickets_last_30d']} P1 tickets in the last 30 days.")
    if account.get("open_tickets", 0) >= 5:
        risks.append(f"The account currently has {account['open_tickets']} open tickets.")
    if account.get("nps_score") is not None and account["nps_score"] <= 6:
        risks.append(f"NPS is low at {account['nps_score']}.")
    if account.get("renewal_date"):
        days_to_renewal = (_parse_date(account["renewal_date"]) - reference_date.date()).days
        if days_to_renewal <= 120:
            risks.append(f"Renewal is coming up in {days_to_renewal} days.")

    for note in account.get("escalation_notes", []):
        risks.append(f"Account note: {note}.")

    for item in flagged_tickets[:5]:
        risks.append(f"Ticket {item.ticket_id}: {item.reason} Quote: \"{item.quote}\"")

    if not risks:
        risks.append("No major risk signals found in the account or recent ticket history.")

    return risks


def _build_talking_points(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
) -> list[str]:
    points = [
        f"Review product adoption across {', '.join(account.get('products', []))}.",
        f"Ask whether the main contact {account['primary_contact']['name']} has seen improvement in support responsiveness.",
        f"Confirm if the team still has the right number of active seats for {account['plan_tier']} usage.",
    ]

    if account.get("renewal_date"):
        points.append(f"Discuss renewal readiness for {account['renewal_date']}.")
    if recent_tickets:
        ticket_label = "ticket" if len(recent_tickets) == 1 else "tickets"
        points.append(f"Review the {len(recent_tickets)} {ticket_label} raised in the last 90 days and any repeat themes.")
    if flagged_tickets:
        points.append("Walk through the flagged tickets and confirm whether any of them are contributing to churn risk.")
    if account.get("integrations_active"):
        points.append(f"Check whether active integrations like {', '.join(account['integrations_active'])} are still healthy.")

    return points


def _build_executive_summary(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
    reference_date: datetime,
) -> str:
    seats_active = account.get("seats_active", 0)
    seats_licensed = account.get("seats_licensed", 0) or 1
    seat_usage = round((seats_active / seats_licensed) * 100, 1)
    renewal_days = None
    if account.get("renewal_date"):
        renewal_days = (_parse_date(account["renewal_date"]) - reference_date.date()).days

    ticket_label = "ticket" if len(recent_tickets) == 1 else "tickets"
    sentences = [
        f"{account['company']} is an {account['health_status']} account in {account['plan_tier']} plan tier, owned by TAM {account['tam']}." if account['health_status'][0].lower() in "aeiou" else f"{account['company']} is a {account['health_status']} account in {account['plan_tier']} plan tier, owned by TAM {account['tam']}.",
        f"Usage trend is {account['usage_trend']} and seat usage is {seat_usage}% ({seats_active}/{seats_licensed}).",
        f"The account has {account.get('open_tickets', 0)} open tickets, with {len(recent_tickets)} {ticket_label} in the last 90 days and {len(flagged_tickets)} flagged risk tickets.",
    ]
    if renewal_days is not None:
        sentences.append(f"Renewal is in {renewal_days} days.")
    if account.get("nps_score") is not None:
        sentences.append(f"Current NPS is {account['nps_score']}.")
    return " ".join(sentences)


def _extract_quote(subject: str, body: str, keyword: str) -> str:
    text = f"{subject}\n{body}".strip()
    lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]

    if keyword:
        for line in lines:
            if keyword in line.lower():
                return line

    return lines[0] if lines else subject


def _first_matching_keyword(text: str, keywords: list[str]) -> str:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return ""


def _load_json_file(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_date(value: str):
    return datetime.fromisoformat(value).date()

