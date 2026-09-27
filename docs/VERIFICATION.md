# Verification record

Recorded locally on 2026-09-27. **The local application is verified; the hosted/live integration still needs account configuration and testing.**

| Check | Result |
| --- | --- |
| Production frontend build | Passed with Vite 6.4.3 |
| Backend behavior and service-contract tests | 23 passed |
| Python dependency compatibility | `pip check` passed |
| Frontend dependency audit | Zero known vulnerabilities at check time |
| Installed Python environment audit | Zero known vulnerabilities at check time |
| Browser upload | Sample protocol uploaded through the dashboard; 3 pages, Ready |
| Browser question | Retention question returned the source containing “90 days” |
| Browser citation | Opened physical page 3, “Consent and limitations,” with matching excerpt |
| Dialog keyboard behavior | Escape closed the citation viewer |
| Narrow workspace | Checked at 390px viewport; no horizontal document overflow |
| Sample PDF visual inspection | All nine pages rendered and inspected; no clipped content |
| Offline evaluation | All 24 questions ran without request errors |
| Supabase migration execution | Pending an actual project |
| Real embedding and answer calls | Pending API credentials/billing |
| Render deployment | Not performed; configuration and instructions checked against official docs |

The final backend test run produced one upstream deprecation warning about Starlette's future TestClient preference for `httpx2`. Tests currently work with the explicitly installed `httpx`. This is not a failed test or a production request error.

The Windows machine had an inaccessible existing global pytest temporary folder. Tests ran with a fresh project-local base directory:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q --basetemp='D:/Vertebra Research/tmp/pytest-check-03'
```

On your machine, the ordinary README test command should work. If using `--basetemp`, choose a new dedicated test-only directory: pytest can remove its existing contents. Never point it at a source or personal-data directory.

## Offline evaluation results

- Answer correctness heuristic: **23/24 (95.8%)**.
- Citation precision heuristic: **80%**.
- Mean expected-source recall: **100%** on answerable questions.
- Abstention behavior: **23/24 (95.8%)** overall; **3/4 (75%)** on unanswerable questions.
- False abstention on answerable questions: **0%**.
- Local wall-clock p50 / p95: approximately **3 ms / 3 ms** in this run.
- Model cost: **$0**, because this was the offline adapter.

These are not OpenAI quality or latency measurements. The fallback returns excerpts and can retrieve additional pages or fail to abstain for related-but-unanswered questions. See the saved `evaluation/results.json` for individual outputs and [evaluation limitations](EVALUATION.md). Live quality must be measured separately.

## Exact remaining account steps

1. Create a Supabase project and run `supabase/migrations/001_research.sql`.
2. Put the project's HTTPS URL and legacy service-role key in `backend/.env`.
3. Create an OpenAI project key, configure billing/budget alerts, and put it in the same file.
4. Set live mode and a long demo passphrase; restart the API. Upload the three fixtures and repeat the live upload/question/citation/deletion checks.
5. Run `evaluation/run.py --api-url http://127.0.0.1:8000` against the live library and inspect the actual answers.
6. Push the repository without secrets, create the two Render services from `render.yaml`, and set their actual CORS/API URLs and backend secrets.
7. Complete every deployed-site check in [DEPLOYMENT.md](DEPLOYMENT.md), including persistence after a restart and restricted private-file access.

Until those steps pass, describe this as **locally verified and prepared for deployment**, not a verified hosted Supabase/OpenAI application.
