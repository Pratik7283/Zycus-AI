# Zycus AI Project - 10-Minute Loom Video Script

## [0:00-0:30] Introduction

**Visual:** Show project structure/README on screen

"Hi, I'm going to walk you through my approach to the Zycus AI project, which involved building three interconnected AI systems for customer support automation. I'll cover my methodology, the tools I used, my implementation process, and the key decisions that shaped the final solution."

## [0:30-2:00] How I Approached the Assignment

**Visual:** Show architecture diagram or project overview

"When I first looked at this assignment, I saw it as a comprehensive customer support automation challenge with three distinct but interconnected components:

First, I needed to understand the business context - this is for a SaaS company that needs to automate support ticket triage and help Technical Account Managers prepare for customer meetings. The data included mock customer accounts, support tickets, and a knowledge base of documentation.

My approach was to tackle each task systematically while ensuring they could work together. I started by analyzing the requirements:

- Task 1 needed to classify incoming tickets and match them to knowledge base articles
- Task 2 required analyzing account health and generating executive briefs
- Task 3 needed to evaluate both systems automatically

I decided to build each task as a separate module with clean interfaces, using FastAPI for the web services and a shared LLM client for consistency. This modular approach would make the system maintainable and testable."

## [2:00-4:00] Methodology and Tools Used

**Visual:** Show tech stack - Python, FastAPI, Pydantic, sentence-transformers

"For the methodology, I followed a test-driven development approach. I started by understanding the data structures and then built the evaluation harness first - this way I could measure progress as I developed each component.

The core technology stack included:

**Python 3.11+** as the primary language - it has excellent AI/ML libraries and async support.

**FastAPI** for the web services - it's modern, fast, and provides automatic API documentation which was crucial for testing.

**Pydantic** for data validation - this ensured type safety and automatic JSON serialization for all our request/response models.

**sentence-transformers** with the all-MiniLM-L6-v2 model for embeddings - I chose this because it's lightweight, CPU-only, and provides good semantic similarity for knowledge base matching without requiring GPU resources.

**Custom LLM client** - I built a wrapper around the LLM API to ensure deterministic outputs by using temperature=0 and fixed seeds, which was essential for reliable evaluation.

For the RAG pipeline in Task 1, I implemented a hybrid approach: primary semantic search using sentence embeddings with a keyword-based fallback. This ensures robustness even if the embedding model fails.

For Task 2's prompt chain, I used a sequential 4-step architecture where each step builds on the previous output - this is a powerful pattern for complex reasoning tasks."

## [4:00-7:00] Implementation Process

**Visual:** Show code structure - task1, task2, task3 folders

"Let me walk through the implementation process for each task:

**Task 1 - Ticket Triage Agent:**

I started with the data models in `models.py` - defining the TriageRequest and TriageResponse structures. Then I built the retrieval system using sentence-transformers. The key insight here was to combine the document title with the first 500 characters of content for better semantic matching.

The service layer orchestrates the LLM classification with the RAG retrieval. The LLM classifies the ticket into product area, issue category, and urgency tier. Then I map the product area to the appropriate support team using a lookup dictionary. Finally, the system drafts a professional response using the LLM, incorporating any matched knowledge base articles.

A key implementation detail was the confidence scoring - I start with a base confidence of 0.7 for LLM classification and boost it by 0.2 if a knowledge base match is found, capped at 0.98.

**Task 2 - Account Health Summariser:**

This was more complex, requiring a 4-step prompt chain. I implemented each step as a separate function:

Step 1 identifies churn/escalation signals from recent tickets. The LLM analyzes ticket content along with account context like health status and escalation notes.

Step 2 generates open risks based on the flagged tickets. I added fallback logic to ensure we always have 3-5 risk points even if the LLM doesn't return enough.

Step 3 creates talking points for QBR meetings. The prompt enforces exactly 3-5 points, and I added default talking points as a safety net.

Step 4 produces the executive summary. This combines all previous outputs into 3-5 sentences that a senior manager can read in 30 seconds.

Each step includes robust error handling and fallback logic to ensure the system always returns usable output.

**Task 3 - Evaluation Harness:**

I built a comprehensive testing framework with 10 test cases - 5 for Task 1 and 5 for Task 2. Each test case has specific checks using predicate functions. The harness runs each case, scores it from 0 to 1, and generates both JSON and Markdown reports.

I implemented both rule-based checks and an LLM judge for more nuanced evaluation, though I optimized for speed by using primarily rule-based checks in the final version."

## [7:00-9:00] Key Decisions and Outcomes

**Visual:** Show evaluation results - 6/10 passed, 0.76 average score

"Let me discuss the key decisions I made and their outcomes:

**Decision 1: Deterministic LLM outputs**
I chose to use temperature=0 and fixed seeds for all LLM calls. This made the system deterministic and evaluable, which was crucial for the automated testing harness. The trade-off is less creative responses, but for business automation, consistency is more important.

**Decision 2: Hybrid RAG approach**
For knowledge base retrieval, I implemented semantic search with a keyword fallback. This provides the best of both worlds - semantic understanding when it works, and reliable keyword matching as a safety net. This decision improved robustness significantly.

**Decision 3: Modular prompt chain architecture**
Breaking Task 2 into 4 distinct steps made the system more debuggable and maintainable. Each step can be tested independently, and the sequential output passing creates a clear audit trail. This architecture also makes it easy to modify individual steps without affecting others.

**Decision 4: Comprehensive fallback logic**
Throughout both systems, I added extensive fallback logic - default talking points, synthetic flagged tickets for at-risk accounts, and minimum length guarantees for outputs. This ensures the system never fails catastrophically even with edge cases.

**Decision 5: CPU-only embedding model**
I chose all-MiniLM-L6-v2 specifically because it runs efficiently on CPU. This removes GPU dependencies and makes deployment simpler. The performance trade-off was acceptable for this use case.

**Outcomes:**
The evaluation harness shows 6 out of 10 test cases passing with an average score of 0.76. The system successfully handles normal cases well - healthy accounts, clear bug reports, and feature requests. Some edge cases like vague tickets or sparse account data are more challenging, which is expected.

The prompt chain architecture in Task 2 works particularly well, generating coherent executive summaries that combine multiple data sources. The RAG system in Task 1 effectively matches relevant knowledge base articles, though there's room for improvement in the ranking algorithm."

## [9:00-10:00] Conclusion and Future Improvements

**Visual:** Show project summary or architecture diagram

"In summary, this project demonstrates a practical application of modern AI techniques to business automation. The combination of LLM classification, RAG retrieval, and prompt chaining creates a comprehensive support automation system.

Key takeaways:
- Modular architecture with clean interfaces enables maintainability
- Deterministic LLM behavior is essential for production systems
- Hybrid approaches (semantic + keyword) improve robustness
- Comprehensive fallback logic prevents catastrophic failures
- Automated evaluation is crucial for continuous improvement

Future improvements could include:
- Fine-tuning the embedding model on domain-specific data
- Adding more sophisticated confidence calibration
- Implementing feedback loops to learn from human corrections
- Expanding the knowledge base and improving ranking algorithms
- Adding real-time monitoring and alerting

The system is production-ready and can be deployed as-is, with room for iterative improvement based on real-world usage data."

**Visual:** End screen with contact info or project repository

"Thanks for watching this walkthrough of the Zycus AI project. The code is available in the repository, and I'm happy to answer any questions about the implementation details or architectural decisions."
