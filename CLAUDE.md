# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt        # deps live here, NOT in pyproject.toml
uvicorn app.main:app --reload          # REST API on http://127.0.0.1:8000 (docs at /docs)
python -m app.mcp_server               # MCP server over stdio
pytest                                 # full suite (~5s)
pytest tests/test_api.py::test_health  # single test
```

`python app/mcp_server.py` fails — the module uses absolute `app.*` imports, so it must be
run as a module from the repo root.

`pyproject.toml` declares `dependencies = []`; it exists only for the `[tool.pytest.ini_options]`
block (`asyncio_mode = "auto"`, which is why tests need no `@pytest.mark.asyncio` decorator —
`tests/test_api.py` sets `pytestmark` at module level).

## Architecture

Two independent front doors over one service layer:

```
app/main.py (FastAPI REST)  ──┐
                              ├──> app/service.py (EvaluationService)
app/mcp_server.py (MCP)     ──┘
```

**Each front door builds its own `EvaluationService()` instance**, so their in-memory stores
are separate — an evaluation created over REST is invisible to the MCP tools and vice versa.
This is fine while storage is a dict, but any move to shared/persistent state needs a single
service instance (or a real backing store) wired into both.

**The service layer knows nothing about HTTP.** `service.py` raises domain exceptions
(`EvaluationNotFound`, `InvalidStateTransition`); `main.py` is the only place that translates
them into status codes (404 and 409 respectively), and `mcp_server.py` translates its own
lookup failure into `ValueError`. Keep FastAPI imports out of `service.py`.

**Evaluations are plain dicts inside the service**, not Pydantic models. `app/models.py` is
the boundary layer only — endpoints and tools hydrate `EvaluationResponse(**evaluation)` or
build `EvaluationSummary(...)` field-by-field on the way out. `EvaluationSummary` deliberately
drops `skills` and is what `/run` and both MCP tools return.

### Evaluation lifecycle

`pending → running → completed`. Only `pending` may be run; a second `/run` raises
`InvalidStateTransition` → HTTP 409. IDs are generated as `E001`, `E002`, … from
`len(self.evaluations) + 1`, so the scheme assumes evaluations are never deleted.

### Concurrency

`run_evaluation` fans out `analyze_skills` / `analyze_resume` / `analyze_experience` through
`asyncio.gather` and averages their scores. These are stubs: each sleeps 1s and returns a fixed
80 / 90 / 85, averaging to exactly **85**. Two tests are pinned to that behaviour —
`test_run_evaluation_completes_with_score_85` asserts the score, and
`test_run_evaluation_runs_concurrently` asserts wall-clock `< 2.0s` to prove the analyzers
overlap rather than run sequentially (~3s). Replacing the stubs with real analysis means
updating both.

### Middleware

`RequestMiddleware` (Starlette `BaseHTTPMiddleware`) stamps every response with `X-Request-ID`
and `X-Process-Time` and logs `METHOD /path - status - elapsed`. It calls `logging.basicConfig`
at import time, so importing `app.main` configures root logging as a side effect.

## Testing

`tests/conftest.py` has an autouse fixture that clears `app.main.evaluation_service.evaluations`
around every test, so tests may rely on the first created evaluation being `E001`. Tests drive
the app in-process via `httpx.ASGITransport` — no live server needed. The MCP tools currently
have no test coverage.
