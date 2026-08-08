from __future__ import annotations

from .harness import JSON_REPORT_PATH, MD_REPORT_PATH, run_harness


def main() -> None:
    report = run_harness()
    print(f"Task 3 report written to {JSON_REPORT_PATH}")
    print(f"Markdown report written to {MD_REPORT_PATH}")
    print(f"Passed {report['summary']['passed_cases']} of {report['summary']['total_cases']} cases")


if __name__ == "__main__":
    main()

