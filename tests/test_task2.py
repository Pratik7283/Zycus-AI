from datetime import datetime, timezone

from task2.service import generate_account_brief


def test_account_brief_returns_sections():
    result = generate_account_brief({"account_id": "ACC-3336"}, reference_date=datetime(2026, 8, 8, tzinfo=timezone.utc))

    assert result.account_id == "ACC-3336"
    assert result.company == "Omni Consumer Products"
    assert result.executive_summary
    assert isinstance(result.open_risks_and_flagged_issues, list)
    assert isinstance(result.recommended_talking_points, list)


def test_account_brief_is_deterministic():
    reference_date = datetime(2026, 8, 8, tzinfo=timezone.utc)
    first = generate_account_brief({"account_id": "ACC-3336"}, reference_date=reference_date)
    second = generate_account_brief({"account_id": "ACC-3336"}, reference_date=reference_date)

    assert first.model_dump() == second.model_dump()


def test_account_brief_includes_flagged_quotes_when_present():
    result = generate_account_brief({"account_id": "ACC-3336"}, reference_date=datetime(2026, 8, 8, tzinfo=timezone.utc))

    if result.flagged_tickets:
        assert result.flagged_tickets[0].quote

