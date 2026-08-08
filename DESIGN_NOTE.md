# Design Note

This project is designed as a small, easy-to-explain workflow rather than a complex AI system. I used simple Python modules, fixed rules, and deterministic formatting so the code is easy to run, test, and present in a short demo.

## Failure modes

The first likely failure mode is incorrect classification in Task 1. A ticket may use unusual wording, so a keyword-based rule can map it to the wrong product area or issue category. I detect this by keeping the output structured and reviewable: the `reasoning` field shows which keyword triggered each decision. If the output looks weak, the next improvement would be to add better synonyms or a small LLM layer behind the same interface.

The second failure mode is weak knowledge-base matching. A broad document may look relevant just because it shares common terms with the ticket. I reduced this risk by filtering stopwords and requiring a minimum amount of overlap before returning a match. In production, I would improve this with embeddings or a stronger retrieval method.

The third failure mode is stale or incomplete account data in Task 2. The dataset intentionally includes missing account IDs and sparse ticket history. I handle that by raising a clear error for missing accounts and by writing summary text that still works even when there are few or no recent tickets. In production, I would log missing records and show a fallback message instead of failing silently.

## Latency vs quality

I chose a fast and simple design over a more complex one. The current code uses rule-based matching and local file reads, so it is quick and predictable. That means the output is not as flexible as a full LLM pipeline, but it is much easier to explain and much cheaper to run.

If latency were the hard constraint, I would keep the same interface but simplify the processing even further. For Task 1, that could mean shorter rule sets and less text scanning. For Task 2, I would precompute account summaries and only refresh them when new tickets arrive. That would reduce per-request work and make the system faster under load.

## Data sensitivity

The provided data may contain sensitive customer information, so the safest design choice is to keep processing local and use only the mock dataset. I did not add external data sources or live scraping. I also avoided sending ticket or account content to third-party APIs in the current version.

If this were a production system, I would add more privacy controls: redact obvious PII before logging, store only the fields needed for the task, and restrict any external model calls to non-sensitive text. I would also make sure the `.env.example` file stays clean and no credentials are committed.

## Scaling

At 10x the current ticket volume, the first thing to slow down would be repeated file scanning and repeated in-memory searches through the JSON data. The code is fine for a take-home assignment, but at larger scale I would move the data into a database or cache the parsed records more aggressively.

The current design would still be easy to extend. Task 1 and Task 2 already have separate service modules, so they can evolve independently. I would keep the public API the same and swap out the internals if better retrieval, better scoring, or better storage became necessary. That makes the project easier to maintain and easier to explain.

## Summary

The main tradeoff in this solution is simplicity over sophistication. That was intentional: the goal was to build something reliable, deterministic, and easy to review in a short time window. The structure leaves room for future upgrades, but the current version stays understandable enough to demo confidently.
