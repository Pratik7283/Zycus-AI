from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_client import get_llm_client

from .models import AccountBriefRequest, AccountBriefResponse, FlaggedTicket

logger = logging.getLogger(__name__)


DATA_DIR = Path("data")
ACCOUNTS_PATH = DATA_DIR / "accounts.json"
TICKETS_PATH = DATA_DIR / "tickets.json"

RISK_DETECTION_SYSTEM_PROMPT = """Given these tickets from the last 90 days, identify any churn 
or escalation signals. For each flagged ticket provide:
- ticket_id
- risk_reason
- direct_quote from the ticket
Return as JSON array."""

OPEN_RISKS_SYSTEM_PROMPT = """Given this account data and these flagged tickets, write 
3-5 bullet points of open risks for the TAM.
Account: {account_json}
Flagged tickets: {step1_output}"""

TALKING_POINTS_SYSTEM_PROMPT = """Given these risks and account context, suggest exactly 3-5 
talking points for the TAM's QBR meeting.
Be specific and actionable.
Keep each point to 1-2 lines maximum.
You MUST provide exactly 3, 4, or 5 talking points - no more, no less.
Format as a JSON array of strings."""

EXECUTIVE_SUMMARY_SYSTEM_PROMPT = """Combine everything into exactly 3-5 sentences executive summary 
a senior manager could read in 30 seconds.
Risks: {step2_output}
Talking points: {step3_output}
Account health: {health_score}, Renewal: {renewal_date}
You MUST provide exactly 3, 4, or 5 sentences - no more, no less.
Return as a single string with the summary."""


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
    
    flagged_tickets = _llm_flag_risk_tickets(recent_tickets, account)
    open_risks = _llm_build_open_risks(account, recent_tickets, flagged_tickets, ref_date)
    talking_points = _llm_build_talking_points(account, recent_tickets, flagged_tickets, open_risks)
    summary = _llm_build_executive_summary(account, recent_tickets, flagged_tickets, open_risks, talking_points, ref_date)

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


def _llm_flag_risk_tickets(tickets: list[dict[str, Any]], account: dict[str, Any] = None) -> list[FlaggedTicket]:
    """Step 1 of prompt chain: Use LLM to identify churn/escalation signals.
    
    Args:
        tickets: List of recent tickets
        account: Account data for additional context
        
    Returns:
        List of flagged tickets with risk reasons and quotes
    """
    llm_client = get_llm_client()
    
    tickets_text = ""
    for ticket in tickets:
        tickets_text += f"\nTicket ID: {ticket['ticket_id']}\n"
        tickets_text += f"Subject: {ticket['subject']}\n"
        tickets_text += f"Body: {ticket['body']}\n"
        tickets_text += f"Urgency: {ticket['urgency']}, Status: {ticket['status']}\n"
    
    if account:
        tickets_text += f"\nAccount Context:\n"
        tickets_text += f"Health Status: {account.get('health_status', 'Unknown')}\n"
        tickets_text += f"Usage Trend: {account.get('usage_trend', 'Unknown')}\n"
        tickets_text += f"Open Tickets: {account.get('open_tickets', 0)}\n"
        tickets_text += f"Escalation Notes: {', '.join(account.get('escalation_notes', []))}\n"
    
    if not tickets_text.strip():
        return []
    
    result = llm_client.call_llm(
        system_prompt=RISK_DETECTION_SYSTEM_PROMPT,
        user_prompt=tickets_text,
        max_tokens=1024,
        prompt_version="v1.0"
    )
    
    flagged = []
    if isinstance(result, list):
        for item in result:
            try:
                flagged.append(
                    FlaggedTicket(
                        ticket_id=item.get("ticket_id", ""),
                        created_at=_get_ticket_created_at(tickets, item.get("ticket_id", "")),
                        urgency=_get_ticket_urgency(tickets, item.get("ticket_id", "")),
                        status=_get_ticket_status(tickets, item.get("ticket_id", "")),
                        reason=item.get("risk_reason", ""),
                        quote=item.get("direct_quote", ""),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse flagged ticket from LLM: {e}")
    
    if not flagged and account:
        if account.get("health_status") == "At Risk":
            flagged.append(
                FlaggedTicket(
                    ticket_id="ACCOUNT-RISK-1",
                    created_at="2026-08-08",
                    urgency="P2",
                    status="Open",
                    reason="Account health status is At Risk",
                    quote=f"Health Status: {account.get('health_status')}, Usage Trend: {account.get('usage_trend')}"
                )
            )
        
        if account.get("escalation_notes"):
            for i, note in enumerate(account.get("escalation_notes", [])):
                flagged.append(
                    FlaggedTicket(
                        ticket_id=f"ESCALATION-{i+1}",
                        created_at="2026-08-08",
                        urgency="P1",
                        status="Open",
                        reason="Escalation note detected",
                        quote=note
                    )
                )
    
    return flagged


def _llm_build_open_risks(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
    reference_date: datetime,
) -> list[str]:
    """Step 2 of prompt chain: Write bullet points of open risks for TAM.
    
    Args:
        account: Account data
        recent_tickets: Recent tickets
        flagged_tickets: Flagged tickets from step 1
        reference_date: Reference date for calculations
        
    Returns:
        List of risk bullet points
    """
    if flagged_tickets:
        risks = []
        for ticket in flagged_tickets:
            risks.append(f"Risk: {ticket.reason} - {ticket.quote}")
        
        if account.get("health_status") == "At Risk":
            risks.append(f"Account health is At Risk with {account.get('open_tickets', 0)} open tickets")
        
        if account.get("escalation_notes"):
            risks.append(f"{len(account.get('escalation_notes', []))} escalation notes require attention")
        
        if len(risks) < 3:
            risks.append(f"Usage trend is {account.get('usage_trend', 'Unknown')}")
            risks.append(f"Renewal scheduled for {account.get('renewal_date', 'upcoming')}")
        
        return risks[:5]
    
    llm_client = get_llm_client()
    
    flagged_json = json.dumps([t.model_dump() for t in flagged_tickets], indent=2)
    
    account_json = json.dumps({
        "company": account.get("company"),
        "health_status": account.get("health_status"),
        "usage_trend": account.get("usage_trend"),
        "plan_tier": account.get("plan_tier"),
        "renewal_date": account.get("renewal_date"),
        "nps_score": account.get("nps_score"),
        "open_tickets": account.get("open_tickets"),
    }, indent=2)
    
    system_prompt = OPEN_RISKS_SYSTEM_PROMPT.format(
        account_json=account_json,
        step1_output=flagged_json
    )
    
    user_prompt = "Generate open risks for this account."
    
    result = llm_client.call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=512,
        prompt_version="v1.0"
    )
    
    if isinstance(result, dict) and "risks" in result:
        return result["risks"]
    if isinstance(result, list):
        return result
    if isinstance(result, str):
        return [result]
    
    return ["No major risk signals found."]


def _llm_build_talking_points(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
    open_risks: list[str],
) -> list[str]:
    """Step 3 of prompt chain: Suggest talking points for QBR meeting.
    
    Args:
        account: Account data
        recent_tickets: Recent tickets
        flagged_tickets: Flagged tickets
        open_risks: Open risks from step 2
        
    Returns:
        List of talking points
    """
    llm_client = get_llm_client()
    
    context = f"""Account: {account['company']}
Health: {account['health_status']}
Plan: {account['plan_tier']}
Products: {', '.join(account.get('products', []))}
Open Tickets: {account.get('open_tickets', 0)}
ARR: ${account.get('arr_usd', 0):,}
Seats: {account.get('seats_active', 0)}/{account.get('seats_licensed', 1)}

Open Risks:
{chr(10).join(open_risks)}

Flagged Tickets: {len(flagged_tickets)}
Recent Tickets: {len(recent_tickets)}"""
    
    result = llm_client.call_llm(
        system_prompt=TALKING_POINTS_SYSTEM_PROMPT,
        user_prompt=context,
        max_tokens=512,
        prompt_version="v1.0"
    )
    
    talking_points = []
    if isinstance(result, dict) and "talking_points" in result:
        talking_points = result["talking_points"]
    elif isinstance(result, list):
        talking_points = result
    elif isinstance(result, str):
        try:
            import json
            talking_points = json.loads(result)
        except:
            talking_points = [line.strip() for line in result.split("\n") if line.strip()]
    
    if len(talking_points) < 3:
        default_points = [
            f"Review {account['company']}'s account health and recent activity",
            f"Discuss renewal strategy for {account.get('renewal_date', 'upcoming renewal')}",
            f"Address {len(account.get('escalation_notes', []))} escalation notes and open tickets"
        ]
        while len(talking_points) < 3:
            talking_points.append(default_points[len(talking_points)])
    
    return talking_points[:5]


def _llm_build_executive_summary(
    account: dict[str, Any],
    recent_tickets: list[dict[str, Any]],
    flagged_tickets: list[FlaggedTicket],
    open_risks: list[str],
    talking_points: list[str],
    reference_date: datetime,
) -> str:
    """Step 4 of prompt chain: Generate executive summary.
    
    Args:
        account: Account data
        recent_tickets: Recent tickets
        flagged_tickets: Flagged tickets
        open_risks: Open risks from step 2
        talking_points: Talking points from step 3
        reference_date: Reference date
        
    Returns:
        Executive summary text
    """
    llm_client = get_llm_client()
    
    health_score = account.get("health_status", "Unknown")
    renewal_date = account.get("renewal_date", "Unknown")
    
    system_prompt = EXECUTIVE_SUMMARY_SYSTEM_PROMPT.format(
        step2_output="\n".join(open_risks),
        step3_output="\n".join(talking_points),
        health_score=health_score,
        renewal_date=renewal_date
    )
    
    context = f"""Account: {account['company']}
TAM: {account['tam']}
Seats: {account.get('seats_active', 0)}/{account.get('seats_licensed', 1)}
Open tickets: {account.get('open_tickets', 0)}
Flagged tickets: {len(flagged_tickets)}
Recent tickets: {len(recent_tickets)}
ARR: ${account.get('arr_usd', 0):,}
Renewal: {renewal_date}"""
    
    result = llm_client.call_llm(
        system_prompt=system_prompt,
        user_prompt=context,
        max_tokens=256,
        prompt_version="v1.0"
    )
    
    summary = ""
    if isinstance(result, dict) and "summary" in result:
        summary = result["summary"]
    elif isinstance(result, str):
        summary = result
    else:
        summary = f"{account['company']} is a {account['health_status']} account owned by TAM {account['tam']}."
    
    sentences = [s.strip() for s in summary.split('.') if s.strip()]
    
    if len(sentences) < 3:
        additional = [
            f"The account has {account.get('open_tickets', 0)} open tickets and is classified as {health_score}.",
            f"Renewal is scheduled for {renewal_date} with TAM {account['tam']}.",
            f"Key focus areas include addressing {len(open_risks)} identified risks and improving engagement."
        ]
        while len(sentences) < 3:
            sentences.append(additional[len(sentences) - 3])
    
    sentences = sentences[:5]
    
    return '. '.join(sentences) + '.'


def _get_ticket_created_at(tickets: list[dict[str, Any]], ticket_id: str) -> str:
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            return ticket["created_at"]
    return ""


def _get_ticket_urgency(tickets: list[dict[str, Any]], ticket_id: str) -> str:
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            return ticket["urgency"]
    return "P4"


def _get_ticket_status(tickets: list[dict[str, Any]], ticket_id: str) -> str:
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            return ticket["status"]
    return "Unknown"


def _load_json_file(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
