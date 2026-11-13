# FIREWISE: Execution Status

_Updated 2026-11-13, evening. Concise and live; the newest state wins._

## Completed
| Phase | Result | Commit |
|---|---|---|
| 0: Environment and data correction | `.venv` with pinned `requirements.txt`. Pipeline rewritten to the data contract: 2,019 rows, 1,220 flags (111 anomaly), 43 duplicates marked, 0 orphan flags. `verify_claims.py` recomputes every number | `78c7cc6` |
| 1: Database | `load_db.py` builds `build/firewise.sqlite` deterministically (~14 s) with rules R1–R7; 1,233 NASA report pages indexed | `ff33402` |
| 2+4: Backend + Copilot | FastAPI with 14 routes. Copilot: intent routing, evidence pack, Claude `claude-opus-5-5` with structured output, then a validator (citations must resolve; numbers must appear in the cited evidence), deterministic fallback, and risk / partial-gravity refusal | `5ca8db6`, `d3a0238` |
| 3+5: Frontend, 7 modules | The team's FLARE UI imported (`8c32ee3`), rebranded FIREWISE and wired to the API. Placeholder data deleted. New Scenario Explorer and Research Gap Map | `eadc235` + follow-ups |
| 6: Validation and packaging | Root README; `Dockerfile` (304 MB image, smoke-tested); `.env.example`; contract and changelog updated | this commit |

## Test results (latest run)
- `pytest tests -q`: **27 passed** (11 DB acceptance + 16 API/Copilot).
- Copilot validation set (35 items, no LLM): **recall@5 = 0.85 (29/34)**, recall@10 = 0.94, trap violations **0**.
- Acceptance checks against the live API:

| Check | Result |
|---|---|
| Exploration envelope | **0** |
| Moon-base | **20** (all PSI-159) |
| FM2 point | **10** |
| ISS | 174 |
| CFI | 87 rows / 79 unique |
| FLEX | 274 rows |
| `fuel_class=solid` | 5 investigations |
| DAFT vs SAME | incompatibility shown, plus the verified relation `qualified_instrument_for` |

- UI: `vite build` OK. Headless Chrome on all 7 routes: **0 console errors**, every page renders data.
- Container: `/api/health`, `/` and `/api/ask` all work with no API key.
- `Data/` checksums: **unchanged** (verified on every build).

## Current state
- Running locally at `http://127.0.0.1:8765`, with API and UI on one origin. Ports 8000 and 5173 are taken by other processes on this machine, which were left untouched.
- The Copilot runs in **deterministic mode**: no `ANTHROPIC_API_KEY` is set on this host. The LLM path is covered by tests (mocked success, API failure, and fabrication rejection) but has not been exercised with a live key.

## Blockers and decisions for the team
1. **Public deployment** needs a hosting account (Render, Fly.io or Cloud Run). This is the team's action: `docker build -t firewise . && docker run -p 8000:8000 firewise` works as is.
2. **Copilot key (optional):** set `ANTHROPIC_API_KEY` on the backend host only, then re-run the validation set in LLM mode.
3. **Eligibility (`docs/OPEN_DECISIONS.md` D1/D2):** the team reports that its local competition permits this work and AI tools. Keep the SI-use statement in the submission.
4. The telemetry download is still running in the background, so `sources/sources.csv` is still changing and is intentionally left uncommitted. Re-run `load_db.py` after it finishes. The DB does not depend on telemetry.

## Next actions
1. Deploy the container and run the smoke test from a private window (P0 definition of done).
2. Review the 7-slide deck and add team names and the demo URL.
3. Optional: add a key, run the 35-item validation in LLM mode, and record the citation-validity and numeric-grounding rates.
4. Optional P1: a Playwright smoke suite, code-splitting the 600 KB JS bundle, and an ACME frame strip.

## Decisions log
- **UI:** use the team's FLARE app (user instruction). The Next.js prototype was abandoned.
- **Naming:** the product is named FIREWISE.
- **Colours:** data series use validated colours; FLARE's ember is used for chrome only.
- **Scenario ranking:** lexicographic order (in window, then near window, then material). No weighted score and no risk score.
- **Missing data:** missing pressure never matches a window. Inverse-flame O₂ is kept separate as burner stream.
- **Gap Map:** shows "not documented" as an explicit row and column, never as zero.
- **BASS airflow:** the "up to 40 cm/s" value appears only in record text, so it is shown as a *reported* fact under Compare → "Reported in NASA record text" and is excluded from the table-based similarity.
- **Fact F17:** corrected the stale denominator (now 2,007).
