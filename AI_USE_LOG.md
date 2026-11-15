# SI (AI) use log

One line per use. Newest at the bottom.

| Date       | Who   | Tool        | What it was used for                                                              |
| :--------- | :---- | :---------- | :-------------------------------------------------------------------------------- |
| 2026-11-14 | Daksh | Claude Code | Created this repository's starting files (README, CHRONICLE, AI_USE_LOG, folders) |
| 2026-11-14 | Daksh | Claude Code | Saved a copy of the PSI-25 table into data/raw while the PSI site was down        |

| Date       | Who     | Tool                  | What it was used for                                                                                                           |
| :--------- | :------ | :-------------------- | :----------------------------------------------------------------------------------------------------------------------------- |
|            |
| 2026-11-14 | Paridhi | Muse                  | Wrote Lane B logic (classifier, number checker, answer builder, sample data, demo answers) — reviewed and tested by Paridhi    |
| 2026-11-14 | Paridhi | Muse                  | Wrote Lane B material cards (PMMA, Nomex, SIBAL) — reviewed and tested by Paridhi                                              |
| 2026-11-14 | Paridhi | Muse                  | Wrote Lane B retrieval (rag.py, embedding search) — reviewed and tested by Paridhi                                             |
| 2026-11-14 | Paridhi | Muse                  | Revised RAG for Daksh's review (router, investigations corpus, embedding cache, score cutoff) — reviewed and tested by Paridhi |
| 2026-11-14 | Paridhi | sentence-transformers | all-MiniLM-L6-v2 embedding model used for Lane B retrieval (free, local, no API key)                                           |

- 2026-11-14 — Muse (Light) — Revised rag.py, answer.py, number_checker.py, cards.py, investigations.csv and demo_answers.json for the second RAG review on PR #1 (router fix, max-oxygen code, Saffire V citation correction, full-data cards, exact lookup, BASS + ACME PSI-20/21). Reviewed by Paridhi Singh.
- 2026-11-14 — sentence-transformers / all-MiniLM-L6-v2 — Embedding model used by rag.py for retrieval over the investigations table and material cards. Free, local, no API key. (For References on the project page.)
