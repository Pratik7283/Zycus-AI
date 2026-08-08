from task3.harness import build_report, evaluate_case, TASK1_CASES, TASK2_CASES


def test_task3_has_at_least_five_cases_per_task():
    assert len(TASK1_CASES) >= 5
    assert len(TASK2_CASES) >= 5


def test_task3_report_summary_looks_valid():
    results = [evaluate_case(case) for case in TASK1_CASES[:2] + TASK2_CASES[:2]]
    report = build_report(results)

    assert report["summary"]["total_cases"] == 4
    assert "tasks" in report
    assert "cases" in report

