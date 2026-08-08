# Zycus AI Project

This repo currently includes Task 1, Task 2, Task 3, and Task 4 built against the company-provided mock dataset.

## Prerequisites

- Python 3.11 or newer
- `pip`
- No external API key is required for the current deterministic implementation

The company files are already wired into the repo:

- `data/tickets.json`
- `data/accounts.json`
- `knowledge-base/`

## Task 1

Task 1 is an intelligent ticket triage agent.

What it does:

- Accepts raw text or `{"subject": ..., "body": ...}`
- Classifies product area, issue category, and urgency
- Matches the ticket against the knowledge base
- Suggests a responder team
- Returns a draft first-response message

Run the Task 1 API:

```bash
uvicorn task1.api:app --reload
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/triage ^
  -H "Content-Type: application/json" ^
  -d "{\"subject\":\"Cannot export report\",\"body\":\"Export fails with 500 after clicking CSV. This blocks the quarterly review.\"}"
```

## Task 2

Task 2 is an account health summariser.

What it does:

- Accepts an `account_id`
- Loads the account from `data/accounts.json`
- Pulls the last 90 days of tickets from `data/tickets.json`
- Produces a 3-part brief with executive summary, risks, and talking points
- Flags risk tickets and includes direct quotes

Run the Task 2 API:

```bash
uvicorn task2.api:app --reload
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/account-brief ^
  -H "Content-Type: application/json" ^
  -d "{\"account_id\":\"ACC-3336\"}"
```


## Task 3

Task 3 is the evaluation harness.

What it does:

- Runs 5 test cases for Task 1 and 5 test cases for Task 2
- Scores each case from 0 to 1
- Marks each case pass/fail
- Writes a JSON report and a Markdown report

Run the Task 3 harness:

```bash
python -m task3.run
```

Reports are written to:

- `output/evals/eval_report.json`
- `output/evals/eval_report.md`

## Task 4

Task 4 is the design note.

Read it here:

- [`DESIGN_NOTE.md`](C:/Users/Pratik%20More/Downloads/Zycus-ai-project/DESIGN_NOTE.md)

## Run tests

```bash
python -m pytest
```

## Notes

- The implementation is intentionally deterministic so it can be evaluated reliably.
- The retriever automatically scans the `knowledge-base/` folder for Markdown docs.
- If you later add extra evaluation or LLM features, keep them optional so the clean install still works.
