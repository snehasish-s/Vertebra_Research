# Deploy on Render with Supabase persistence

Instructions and free-tier figures checked on **2026-09-27** against the official sources linked below. No hosted deployment is claimed until the account-dependent checklist has been completed.

## Account setup and deployment

1. Complete the Supabase/OpenAI steps in [SETUP.md](SETUP.md), including the SQL migration. The PDFs and vectors live in Supabase, never on Render's filesystem. Test the live integration locally first.
2. Create a Git repository containing this project and push it to a Git provider supported by Render. Confirm `.env`, `.local-data`, and API keys are absent from the commit. Commit `frontend/package-lock.json`.
3. Sign into [Render](https://dashboard.render.com), connect that repository, and create a **Blueprint** from `render.yaml`. It defines one Python web service and one static site. If preferred, create both manually using the settings below.
4. Enter the backend's `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, and `DEMO_ACCESS_TOKEN` privately in Render. Keep uploads and deletion disabled initially. Use a passphrase even for a read-only interview if you want to limit access and API use.
5. Once Render assigns the frontend URL, set the backend's `CORS_ORIGINS` to a JSON array containing that exact origin, for example `["https://vertebra-research-xxxx.onrender.com"]`. Replace the example with the actual assigned hostname; no trailing slash or wildcard. Add your custom domain explicitly if used. Redeploy the backend after changes.
6. Set the static site's `VITE_API_URL` to the actual public API URL, for example `https://vertebra-api-xxxx.onrender.com`, with no path suffix. Rebuild the static site after changes. These two URLs cannot be known until the services are created; do not leave example hostnames in place.
7. To seed the library, either upload from the locally configured live backend into the same Supabase project, or temporarily enable uploads on Render with the access passphrase configured. Restore uploads and deletes to false afterwards. Review the bucket and tables before sharing the link.
8. Run the deployed checks below. Keep the backend awake by opening it shortly before an interview; free cold starts can take about a minute.

## Manual service settings

| Setting | Backend | Frontend |
| --- | --- | --- |
| Type | Web service, Python, Free | Static site |
| Root directory | `backend` | `frontend` |
| Build | `pip install -r requirements.txt` | `npm ci && npm run build` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-proxy-headers` | Not applicable |
| Publish directory | Not applicable | `dist` relative to frontend root |
| Health path | `/health` | Not applicable |
| Routing | FastAPI routes | Rewrite `/*` to `/index.html` |
| Runtime | Python 3.13.7 | Node 22.19.0 |

The frontend rewrite is a **rewrite**, not a redirect. It lets refreshing `/research` serve the React entry point. Existing asset files are served normally. Keep one API worker: the demo's locks, quotas, and interrupted-upload recovery assume one process. Forwarded client headers are deliberately disabled; clients behind the Render proxy may share one IP rate-limit bucket. The independent global model-call cap still applies.

## Current free-tier limitations

Render's free web service sleeps after 15 minutes without inbound traffic and takes about a minute to resume. Local files disappear on spin-down, restart, or redeploy. A workspace receives 750 free instance hours per month. Bandwidth and build minutes have separate workspace allowances; check the dashboard rather than assuming unlimited use. Free static sites do not need a running backend process. These tiers are suitable for previews, not production reliability. [Render free-service documentation](https://render.com/docs/free).

Supabase Free currently includes a 500 MB database, 1 GB file storage, 5 GB egress and 5 GB cached egress. Free projects may pause after one inactive week, and there is a limit of two active free projects. Automatic backups are not included. Resume a paused project before the interview and keep your permitted source PDFs separately. [Supabase pricing](https://supabase.com/pricing).

OpenAI calls are separately billed; neither Render nor Supabase's free tier makes model inference free. Configure project budget alerts and review spend. Rate limits are not a hard dollar budget and reset when the API restarts. See [model costs](EVALUATION.md).

## Test the deployed site

- Visit the API `/health`; expect `status: ok` and `mode: live`. This is liveness, not a provider connectivity check.
- Open the landing page at desktop and phone widths. Scroll all seven stages. Enable reduced motion; verify content remains visible.
- Open `/research`, refresh the browser, and confirm the route still loads.
- With the passphrase configured, confirm the library and PDF endpoints return 401 without it. The configuration and health routes intentionally remain public.
- Enter the passphrase. Upload a small permitted PDF with uploads temporarily enabled; observe processing and Ready. A wrong type, oversized file, locked PDF, or scan should show a helpful error.
- Ask “How long are raw coded observations retained?” with the samples loaded. Check “90 days,” open the protocol citation, and verify physical page 3 and the excerpt.
- Ask for an absent fact, such as the funder's name. Verify abstention and no citations. Evaluate more than one example; model behavior can vary.
- Delete a disposable document with deletion temporarily enabled. Confirm it disappears, its PDF route returns 404, its chunks are gone, and its Storage object is gone. Disable mutations again.
- Confirm browser network traffic contains only the public API URL and the limited demo passphrase, never service-role/OpenAI keys. Direct anonymous Storage access must fail.
- Call from an unlisted browser origin; confirm no CORS permission is returned. Remember CORS does not stop non-browser clients.
- Restart/redeploy the API and confirm documents remain in Supabase. A interrupted upload must appear as an error rather than Ready.
- Run the external evaluation against the live API, save the report, and review citation correctness manually. Expect several minutes because the evaluator respects request limits.

Official configuration references: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Render static sites](https://render.com/docs/static-sites), [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control), [Supabase pgvector](https://supabase.com/docs/guides/database/extensions/pgvector).
