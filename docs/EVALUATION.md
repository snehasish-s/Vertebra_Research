# Evaluation and model costs

From the repository root:

```powershell
.\.venv\Scripts\python.exe evaluation/run.py
```

This creates a temporary offline library, uploads all three fixtures, asks 24 questions, and writes `evaluation/results.json`. It does not modify the dashboard library. To evaluate a running live backend, first upload exactly the three fixtures through the dashboard, set `DEMO_ACCESS_TOKEN` in the shell environment if needed, then run:

```powershell
.\.venv\Scripts\python.exe evaluation/run.py --api-url http://127.0.0.1:8000 --output evaluation/results-live.json
```

The live run can incur API costs. Its default 6.2-second delay respects 10 questions/minute, assuming no other traffic. Do not use duplicate fixture names or unrelated documents for the baseline. Keep per-question outputs to inspect regressions; do not tune expected answers to make a failing model appear successful.

## Metrics and limits

- **Answer correctness heuristic:** all required keyword groups must appear for answerable questions; abstention is required for unanswerable questions. Paraphrases can fail, negated or unrelated keyword matches can pass, and verbose excerpts can game this metric.
- **Citation precision heuristic:** each returned citation must name an expected document/page and quote text found on that actual PDF page. This does not prove that the cited passage supports every answer claim.
- **Expected-source recall:** fraction of expected pages cited, helping expose abstentions hidden by high precision on a small number of returned citations.
- **Abstention accuracy:** behavior across all questions; unanswerable abstention rate and false-abstention rate are reported separately.
- **Latency:** wall-clock p50 and p95, including the HTTP request for external runs, excluding the intentional delay and initial uploads.
- **Estimated question cost:** token-usage-based cost returned by the backend, excluding upload embeddings, retries whose usage is unavailable, network/storage charges, and failed requests. Treat it as an estimate, not billing reconciliation.

The set is small, English-only, synthetic, and mostly single-fact retrieval. It is not representative of long academic PDFs, tables, multilingual text, adversarial documents, or genuine cross-document synthesis. Add those cases and have a person score factual support, completeness, and citation entailment before claiming reliable quality. Compare models on the same corpus and questions. Local word-matching results measure plumbing only; they cannot validate live RAG quality.

## Chosen models

Pricing checked against official documentation on 2026-09-27:

| Operation | Default model | Estimate per million tokens |
| --- | --- | --- |
| Embeddings | `text-embedding-3-small`, 1,536 dimensions | $0.02 input |
| Answer | `gpt-4.1-mini` | $0.40 input; $1.60 output |

For 3,000 answer input tokens and 400 output tokens, estimate $0.00184 plus a tiny query-embedding charge. Embedding 50,000 input tokens costs approximately $0.001. Twenty-four questions at that example size cost about $0.0442, excluding retries and ingestion. Actual passage sizes, outputs, account pricing, and model changes affect cost. The code assumes these default rates; update its rate constants if changing models. It conservatively ignores prompt-cache discounts.

Sources: [embedding model pricing](https://developers.openai.com/api/docs/models/text-embedding-3-small), [answer model pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

To replace a model vendor, implement `EmbeddingProvider` or `AnswerProvider` and wire it in `create_app`. The answer adapter must return `ModelAnswer`. Changing embeddings requires re-embedding the entire library even if dimensions stay the same; mixing vector spaces breaks similarity. Changing dimensions additionally requires a reviewed database migration and matching configuration validation. Never silently reinterpret existing vectors.
