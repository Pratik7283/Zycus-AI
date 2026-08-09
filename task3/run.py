from task3.harness import run_harness

if __name__ == "__main__":
    print("Running evaluation harness...")
    report = run_harness()
    print(f"Evaluation complete!")
    print(f"Total cases: {report['summary']['total_cases']}")
    print(f"Passed cases: {report['summary']['passed_cases']}")
    print(f"Average score: {report['summary']['average_score']}")
    print(f"\nReport saved to output/evals/eval_report.json and eval_report.md")
