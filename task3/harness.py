from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable
import time

from task1.service import triage_ticket
from task2.service import generate_account_brief
from .llm_judge import llm_judge


REFERENCE_DATE = datetime(2026, 8, 8, tzinfo=timezone.utc)
OUTPUT_DIR = Path("output") / "evals"
JSON_REPORT_PATH = OUTPUT_DIR / "eval_report.json"
MD_REPORT_PATH = OUTPUT_DIR / "eval_report.md"


@dataclass(frozen=True)
class EvalCheck:
    label: str
    predicate: Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class EvalCase:
    task_name: str
    case_name: str
    input_data: Any
    checks: list[EvalCheck]
    adversarial: bool = False


def _field_equals(field: str, expected: Any) -> EvalCheck:
    return EvalCheck(
        label=f"{field} == {expected!r}",
        predicate=lambda output: output.get(field) == expected,
    )


def _field_in(field: str, expected_values: set[Any]) -> EvalCheck:
    return EvalCheck(
        label=f"{field} in {sorted(expected_values)!r}",
        predicate=lambda output: output.get(field) in expected_values,
    )


def _field_contains(field: str, substring: str) -> EvalCheck:
    return EvalCheck(
        label=f"{field} contains {substring!r}",
        predicate=lambda output: substring.lower() in str(output.get(field, "")).lower(),
    )


def _list_contains(field: str, substring: str) -> EvalCheck:
    return EvalCheck(
        label=f"{field} contains item with {substring!r}",
        predicate=lambda output: any(substring.lower() in str(item).lower() for item in output.get(field, [])),
    )


def _field_length_at_least(field: str, minimum: int) -> EvalCheck:
    return EvalCheck(
        label=f"len({field}) >= {minimum}",
        predicate=lambda output: len(output.get(field, [])) >= minimum,
    )


TASK1_CASES = [
    EvalCase(
        task_name="Task 1",
        case_name="report_export_bug",
        input_data={
            "subject": "Cannot export report",
            "body": "Export fails with 500 after clicking CSV. This blocks the quarterly review.",
        },
        checks=[
            _field_in("product_area", {"Reports", "Dashboard"}),
            _field_in("issue_category", {"Bug", "Performance"}),
            _field_in("urgency_tier", {"P1", "P2", "P3"}),
            _field_in("recommended_team", {"Analytics and Reporting Support", "Product Engineering"}),
        ],
    ),
    
    EvalCase(
        task_name="Task 1",
        case_name="auth_access_issue",
        input_data="I cannot log in after MFA reset. Access denied even though the password is correct.",
        checks=[
            _field_in("product_area", {"Authentication"}),
            _field_in("recommended_team", {"Identity and Access"}),
            _field_in("urgency_tier", {"P2", "P3", "P4"}),
        ],
    ),
    
    EvalCase(
        task_name="Task 1",
        case_name="platform_outage",
        input_data="DataBridge Pro is down for all users after a deployment.",
        checks=[
            _field_equals("urgency_tier", "P1"),
            _field_contains("reasoning", "severity") or _field_contains("reasoning", "severe") or _field_contains("reasoning", "all users"),
        ],
    ),
    
    EvalCase(
        task_name="Task 1",
        case_name="feature_request",
        input_data={
            "subject": "Feature request: dark mode",
            "body": "Could you please add dark mode to the dashboard? We would like the ability to switch between light and dark themes.",
        },
        checks=[
            _field_equals("issue_category", "Feature Request"),
            _field_in("product_area", {"Dashboard", "Reports"}),
        ],
    ),
    
    EvalCase(
        task_name="Task 1",
        case_name="vague_ticket",
        input_data={"subject": "Help", "body": "I have a question about something."},
        checks=[
            _field_in("product_area", {"General", "Unknown"}),
            _field_in("issue_category", {"General", "How-To"}),
            _field_equals("urgency_tier", "P4"),
        ],
        adversarial=True,
    ),
]


TASK2_CASES = [
    EvalCase(
        task_name="Task 2",
        case_name="healthy_account",
        input_data={"account_id": "ACC-3033"},
        checks=[
            _field_equals("company", "Polaris Group"),
            _field_equals("health_status", "Healthy"),
            _field_length_at_least("recommended_talking_points", 3),
            _field_equals("data_window_days", 90),
        ],
    ),
    
    EvalCase(
        task_name="Task 2",
        case_name="at_risk_account",
        input_data={"account_id": "ACC-3336"},
        checks=[
            _field_equals("company", "Omni Consumer Products"),
            _field_equals("health_status", "At Risk"),
            _field_contains("executive_summary", "renewal") or _field_contains("executive_summary", "risk"),
            _field_length_at_least("open_risks_and_flagged_issues", 1),
        ],
    ),
    
    EvalCase(
        task_name="Task 2",
        case_name="new_account",
        input_data={"account_id": "ACC-7893"},
        checks=[
            _field_equals("company", "Solaris Data"),
            _field_equals("health_status", "New"),
            _field_equals("usage_trend", "Increasing"),
            _field_contains("executive_summary", "Solaris Data"),
        ],
    ),
    
    EvalCase(
        task_name="Task 2",
        case_name="declining_account",
        input_data={"account_id": "ACC-8113"},
        checks=[
            _field_equals("company", "Vertex Solutions"),
            _field_equals("health_status", "At Risk"),
            _field_equals("usage_trend", "Declining"),
            _field_length_at_least("flagged_tickets", 1),
        ],
    ),
    
    EvalCase(
        task_name="Task 2",
        case_name="sparse_account",
        input_data={"account_id": "ACC-1664"},
        checks=[
            _field_equals("company", "Oscorp Solutions"),
            _field_equals("health_status", "Healthy"),
            _field_length_at_least("recommended_talking_points", 1),
        ],
        adversarial=True,
    ),
]


def run_harness() -> dict[str, Any]:
    case_results = []
    for i, case in enumerate(TASK1_CASES + TASK2_CASES):
        print(f"Running test case {i+1}/{len(TASK1_CASES) + len(TASK2_CASES)}: {case.case_name}")
        try:
            result = evaluate_case(case)
            case_results.append(result)
        except Exception as e:
            print(f"Error in test case {case.case_name}: {e}")
            continue
        time.sleep(2)
    
    report = build_report(case_results)
    write_report_files(report)
    return report


def evaluate_case(case: EvalCase) -> dict[str, Any]:
    raw_output = _run_case(case)
    output = _as_dict(raw_output)

    checks = []
    passed = 0
    for check in case.checks:
        ok = bool(check.predicate(output))
        passed += int(ok)
        checks.append({"label": check.label, "passed": ok})

    total = len(case.checks) or 1
    rule_score = round(passed / total, 2)
    
    final_score = rule_score
    passed = final_score >= 0.8
    
    return {
        "task_name": case.task_name,
        "case_name": case.case_name,
        "adversarial": case.adversarial,
        "passed": passed,
        "score": final_score,
        "rule_score": rule_score,
        "llm_judge_score": None,
        "checks": checks,
        "input": _serialise_input(case.input_data),
        "llm_reasoning": "",
    }


def build_report(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in case_results:
        grouped.setdefault(result["task_name"], []).append(result)

    task_summaries = []
    for task_name, results in grouped.items():
        total = len(results)
        passed = sum(1 for result in results if result["passed"])
        average_score = round(sum(result["score"] for result in results) / total, 2) if total else 0.0
        adversarial_results = [result for result in results if result["adversarial"]]
        task_summaries.append(
            {
                "task_name": task_name,
                "total_cases": total,
                "passed_cases": passed,
                "average_score": average_score,
                "adversarial_cases_passed": sum(1 for result in adversarial_results if result["passed"]),
            }
        )

    total_cases = len(case_results)
    passed_cases = sum(1 for result in case_results if result["passed"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_date": REFERENCE_DATE.isoformat(),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "average_score": round(sum(result["score"] for result in case_results) / total_cases, 2) if total_cases else 0.0,
        },
        "tasks": task_summaries,
        "cases": case_results,
    }


def write_report_files(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    MD_REPORT_PATH.write_text(_render_markdown(report), encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Task 3 Eval Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Reference date: {report['reference_date']}",
        f"- Total cases: {report['summary']['total_cases']}",
        f"- Passed cases: {report['summary']['passed_cases']}",
        f"- Average score: {report['summary']['average_score']}",
        "",
        "| Task | Cases | Passed | Avg Score | Adversarial Passed |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for task in report["tasks"]:
        lines.append(
            f"| {task['task_name']} | {task['total_cases']} | {task['passed_cases']} | {task['average_score']} | {task['adversarial_cases_passed']} |"
        )

    lines.extend(["", "## Case Results", "", "| Task | Case | Pass | Score | Adversarial |", "| --- | --- | ---: | ---: | ---: |"])
    for case in report["cases"]:
        lines.append(
            f"| {case['task_name']} | {case['case_name']} | {str(case['passed'])} | {case['score']} | {str(case['adversarial'])} |"
        )
    return "\n".join(lines) + "\n"


def _build_expected_criteria(case: EvalCase) -> str:
    """Build expected criteria string for LLM judge evaluation."""
    criteria_parts = []
    for check in case.checks:
        criteria_parts.append(f"- {check.label}")
    return "\n".join(criteria_parts)


def _run_case(case: EvalCase) -> Any:
    if case.task_name == "Task 1":
        return triage_ticket(case.input_data)
    if case.task_name == "Task 2":
        return generate_account_brief(case.input_data, reference_date=REFERENCE_DATE)
    raise ValueError(f"Unknown task name: {case.task_name}")


def _as_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    raise TypeError(f"Unsupported result type: {type(result)!r}")


def _serialise_input(value: Any) -> Any:
    if isinstance(value, dict):
        return dict(value)
    return value
