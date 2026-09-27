# Setup and credentials

## Run locally without credentials

Requirements: Python 3.11–3.13 and Node 22.19 or later. Commands below run from the repository root in PowerShell. Use `npm` instead of `npm.cmd` on macOS/Linux; use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
cd frontend
npm.cmd ci
cd ..
.\.venv\Scripts\python.exe sample_documents/generate.py
```

Terminal 1, from repository root:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```powershell
cd frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173, choose **Start your research**, and upload the three PDFs in `sample_documents/`. The local badge is intentional: this mode uses deterministic word vectors and verbatim excerpts, not an AI model. Data persists in `backend/.local-data/research.sqlite3` when started from `backend/`. This database is excluded from Git.

## Connect the real services

Keep secrets in `backend/.env` on your machine and in Render's backend environment settings. **Do not paste them into chat, commit them, or put them in a `VITE_` variable.** A ChatGPT subscription does not supply API billing.

1. Create a project at [Supabase](https://supabase.com/dashboard). Choose a nearby region. Keep its database password in your password manager; this application does not use it.
2. Open the project's SQL Editor. Run all of `supabase/migrations/001_research.sql` once. Confirm the `documents` and `chunks` tables, `match_chunks` function, and private `research-pdfs` Storage bucket exist. For CLI-managed projects, place this migration in your Supabase project and use `supabase db push` instead. Do not run it twice as a new migration.
3. In project settings, copy the project URL into `SUPABASE_URL`. In API keys, copy the legacy **service_role** server key into `SUPABASE_SERVICE_ROLE_KEY`. This implementation sends it as both the API key and bearer token; do not substitute an anon/publishable key. The service role bypasses RLS, which is why it stays on the server.
4. Create an OpenAI API project and key in [API settings](https://platform.openai.com/api-keys). Configure billing and project budget alerts. Put the key in `OPENAI_API_KEY`. Ensure the project can access `text-embedding-3-small` and `gpt-4.1-mini`.
5. Generate a shared demo passphrase locally: `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Put it in `DEMO_ACCESS_TOKEN`. Share this limited demo passphrase only with intended reviewers, never your service/API keys.
6. In `backend/.env`, set `APP_MODE=live`, `UPLOADS_ENABLED=true`, `DELETES_ENABLED=true`, and the credentials above. Keep dimensions at 1536. Restart FastAPI; enter the demo passphrase in the dashboard.
7. Upload the three fixtures again. Live mode uses Supabase, so it does not reuse the local SQLite library. Ask a known question, open its citation, and inspect the exact physical page.
8. Before allowing anonymous visitors, set uploads and deletes to false. Removing the passphrase makes every stored document and answer publicly readable through the backend. Use only permitted public sample files in this configuration.

Tell your collaborator only that your local environment file is configured. They can test without displaying the values. No Render credentials are needed to build or test locally.

## Environment reference

| Variable | Default / purpose |
| --- | --- |
| `APP_MODE` | `local`; `live` selects Supabase and OpenAI |
| `CORS_ORIGINS` | JSON array of exact frontend origins; no trailing slash |
| `SUPABASE_URL` | Supabase project's HTTPS URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only legacy service role key |
| `OPENAI_API_KEY` | Server-only OpenAI project key |
| `DEMO_ACCESS_TOKEN` | Optional read-access gate; at least 24 characters required for live mutations |
| `UPLOADS_ENABLED` / `DELETES_ENABLED` | Local defaults true; Render defaults false |
| `STORAGE_BUCKET` | `research-pdfs`, must match migration |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSIONS` | `text-embedding-3-small` / 1536 |
| `ANSWER_MODEL` | `gpt-4.1-mini`, must support structured outputs |
| `MAX_FILE_MB` / `MAX_PAGES` | 10 / 150; Storage bucket limit must also match if changed |
| `MAX_DOCUMENTS` | 30 including failed/deleting records |
| `REQUESTS_PER_MINUTE` | 60 per connected client address |
| `QUESTIONS_PER_MINUTE` | 10 globally per process |
| `UPLOADS_PER_HOUR` | 10 globally per process |
| `SIMILARITY_THRESHOLD` | 0.3 cosine similarity in live mode; tune with evaluation |
| `LOCAL_DATA_DIR` | `.local-data` relative to backend process working directory |
| `VITE_API_URL` | Frontend-only public backend URL; rebuild frontend after changing |
| `PORT` | Supplied by Render and read by the deployment start command |

## Troubleshooting

If the API cannot start in live mode, check all three service settings and the passphrase requirement. A 401 means the demo passphrase is missing or incorrect. A 400 on scans is expected: OCR is not implemented. A 429 means the demo's quota window is full; wait before retrying. A failed upload remains visible with an error; delete it and retry. Reloading a restricted dashboard requires entering the passphrase again because it is held only in memory.

The health endpoint reports that the process is running, not that provider credentials or database permissions work. A successful live upload and question are the integration check.
