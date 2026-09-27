# Vertebra Research

**Evidence, connected.** A document research assistant with a scroll-illuminated spine illustration, a PDF library, retrieval-grounded answers, and source excerpts linked to exact physical PDF pages.

React + Vite frontend. FastAPI backend. Supabase Postgres with pgvector and private Storage in live mode. Small provider interfaces keep the model choice replaceable.

## Start here

1. Follow [local setup](docs/SETUP.md) to run the app without credentials.
2. Open `http://127.0.0.1:5173` and upload the three tiny, original [sample PDFs](sample_documents/README.md).
3. Ask “How long are raw coded observations retained?” Open the citation and check the protocol's physical page 3.
4. Follow the same guide to configure Supabase and OpenAI privately in `backend/.env`. Never send service keys in chat or put them in frontend settings.

**Local mode is an offline demonstration, not AI RAG.** It uses word matching and returns source excerpts. Live mode uses real embeddings and an answer model. A conspicuous dashboard banner identifies local mode.

## Repository map

```text
frontend/                 React application, API client, CSS, PDF page viewer
backend/app/              FastAPI, settings, models, safety boundaries
backend/app/services/     PDF extraction, chunking, upload and question workflows
backend/app/providers/    Model interfaces, offline and OpenAI implementations
backend/app/repositories/ Local SQLite and Supabase adapters
backend/tests/            API behavior and provider/storage contract tests
supabase/migrations/      Tables, private bucket, pgvector search, grants
sample_documents/         Three original CC0 PDFs, source text, generator
evaluation/               24 questions and a metrics/report script
docs/                     Setup, teaching guide, deployment, evaluation
render.yaml               Static site + single-worker API deployment
```

Read [the staged architecture walkthrough and request-flow diagram](docs/ARCHITECTURE.md) for what each file does and how data travels through it. See [verification evidence](docs/VERIFICATION.md) for tested behavior and account-dependent checks still outstanding.

## Verification commands

From the repository root in PowerShell:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ../frontend
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe evaluation/run.py
```

The evaluation reports heuristic correctness, citation precision/source recall, abstention, latency, and estimated cost. [Evaluation limitations and model prices](docs/EVALUATION.md) explain why a passing score is not a guarantee of factual accuracy.

## Demo safeguards and boundaries

The backend checks file extension, content type, PDF signature, size, page count, extracted-text volume, document count, and question length. It rejects encrypted/empty scans, limits concurrent work and requests, restricts CORS, keeps files private in Storage, and validates citation IDs. React renders answer text without interpreting HTML. PDF.js renders pages with eval disabled. No model has tools or permission to act on document instructions.

This is a **shared library**, not a multi-user privacy system. With no passphrase, anyone who can reach the API can read every ready document and spend the question quota. A private Storage bucket does not change that backend behavior. A shared passphrase gates the entire library, but does not separate users or assign ownership. Never upload confidential records. PDFs can include malicious or resource-intensive content; size caps and concurrency limits reduce risk but are not sandboxing, malware scanning, or comprehensive denial-of-service protection.

Render defaults to `UPLOADS_ENABLED=false` and `DELETES_ENABLED=false`. Live mutations additionally require a passphrase of at least 24 characters. Set `DEMO_ACCESS_TOKEN` to restrict reads and questions too. Keep only permitted public samples for an anonymous read-only interview. Limits are process-local and restart with the service; use one worker. Production needs authentication, per-user authorization, durable jobs, distributed quotas, parser isolation, backups, and a richer evaluation set.

An interrupted upload becomes an error on startup; it is not automatically retried. Failed uploads may retain partial server-side data until deleted. Deletion is retryable and hides the record before removing bytes and cascading passages. CORS is a browser policy, not authentication. An answer with a real citation can still misrepresent its source; inspect the excerpt.

## How to explain this project in an interview

“I built a retrieval-augmented document assistant. Instead of sending every PDF to a model, I extract text page by page, split it into overlapping passages, and store their embeddings in pgvector. A question retrieves a small set of relevant passages. The model answers from those passages, and the backend verifies the source IDs before adding real document titles and page numbers.”

Explain these choices with concrete examples:

- **Page-aware chunks:** a claim about 90-day retention points to physical page 3 even if the PDF has an unnumbered cover. Overlap helps preserve context, but small chunks can still lose information across page boundaries.
- **Grounding and abstention:** an absent funder name should produce “not enough information.” Source-ID validation prevents invented links; it does not prove that a real source entails the claim.
- **Replaceable boundaries:** model and repository protocols separate retrieval logic from OpenAI and Supabase. Offline adapters make tests reproducible without credentials.
- **Persistence and deletion:** Render can discard local files, so live PDFs and vectors are external. Deletion hides the record first, removes its object, and cascades passages, with safe retries after partial failure.
- **Measured limits:** show the evaluation's actual misses, not only a score. Discuss keyword scoring's blind spots and the next step of human entailment review.
- **Honest scope:** no OCR, per-user authentication, distributed job queue, or production abuse protection. The shared passphrase and read-only switches suit a controlled interview, not a sensitive multi-tenant service.

A useful live demo takes two minutes: upload a fixture, ask a fact, open its source page, ask an unanswerable question, and explain one failure mode. For scaling, prioritize authenticated ownership, durable ingestion, richer evaluation, hybrid retrieval/reranking, and measured vector indexing improvements.

## Deployment

[Render deployment instructions](docs/DEPLOYMENT.md) cover environment values, frontend routing, current free-tier limits, persistence, and a deployed-site test checklist. Account setup and a real live smoke test are required before calling the hosted integration complete.
