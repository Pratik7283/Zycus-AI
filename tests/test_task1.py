from task1.service import triage_ticket


def test_triage_identifies_reporting_export_issue():
    result = triage_ticket(
        {
            "subject": "Cannot export quarterly report",
            "body": "Export fails with 500 after clicking CSV. This blocks the quarterly review.",
        }
    )

    assert result.product_area == "Reports"
    assert result.issue_category == "Bug"
    assert result.urgency_tier == "P2"
    assert result.recommended_team == "Analytics and Reporting Support"
    assert result.known_issue_match is True
    assert result.matched_kb_doc is not None


def test_triage_identifies_auth_issue_from_raw_text():
    result = triage_ticket(
        "I cannot log in after MFA reset. Access denied even though the password is correct."
    )

    assert result.product_area == "Authentication"
    assert result.issue_category == "Bug"
    assert result.recommended_team == "Identity and Access"
    assert result.urgency_tier in {"P2", "P3", "P4"}


def test_triage_returns_deterministic_response():
    payload = {
        "subject": "Webhook delays for CRM sync",
        "body": "Records are stale and the integration is delaying updates by 2 hours.",
    }

    first = triage_ticket(payload)
    second = triage_ticket(payload)

    assert first.model_dump() == second.model_dump()


def test_triage_handles_ambiguous_ticket():
    result = triage_ticket({"subject": "Question", "body": "Can you help me understand the dashboard?"})

    assert result.product_area == "Dashboard"
    assert result.draft_first_response
    assert 0.0 <= result.confidence <= 1.0

