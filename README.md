# FIREWISE

FIREWISE gives fire-safety evidence for space exploration. It is a web dashboard over the 24 NASA Physical Sciences Informatics (PSI) combustion investigations, built for NASA Space Apps 2026, challenge "Flame in Freefall".

What it does:
- Summarizes each investigation and shows how its tests differed.
- Ranks investigations against a habitat atmosphere.
- Compares investigations.
- Maps where evidence is missing.
- Answers questions with source citations.

Every value keeps its measurement status: measured, derived, reported, set-point, or not documented. Every value also links to the NASA row or text it came from. Missing values are never turned into zero.

**FIREWISE does not produce fire-risk scores and does not predict partial-gravity behaviour.** PSI contains no partial-gravity combustion data.

## Modules
| Page | What it shows | Needs LLM? |
|---|---|---|
| Mission Control | Headline counts, key findings, O₂ × pressure scatter of every documented record, documentation completeness | no |
| Investigation Explorer | Search and filter; verbatim PSI objectives; documented conditions; every test record with its source row | no |
| Scenario Explorer | Habitat atmosphere presets or a custom window; investigations ranked lexicographically by documented tests in and near the window | no |
| Comparison Studio | 2–4 investigations side by side; incompatibilities; documented ranges | no |
| Research Gap Map | Records by fuel class × chamber O₂ × pressure for each gravity level; "not documented" shown explicitly | no |
| Findings | Evidence-graded findings: established, possible implication, or more research needed | no |
| AI Copilot | Cited answers; a validator checks every citation and number; deterministic fallback; saved conversations (switch, rename, delete) and an answer cache | optional |
| **Digital Twin** | 3D habitat (Three.js) + engineering dashboard + NASA evidence twin + physics twin (ideal gas, gas-mixture properties, bulk airflow, convection, conduction) + scenario save/compare/history + scientific report + twin-aware Copilot | no (Copilot optional) |

Digital Twin documentation:
- [architecture](docs/DIGITAL_TWIN_ARCHITECTURE.md)
- [scientific models](docs/DIGITAL_TWIN_SCIENTIFIC_MODELS.md)
- [validation](docs/DIGITAL_TWIN_VALIDATION.md)
- [API](docs/DIGITAL_TWIN_API.md)
- [user guide](docs/DIGITAL_TWIN_USER_GUIDE.md)

## Run locally
Requirements: Python 3.12 and Node 18+.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 -I scripts/load_db.py .            # -> build/firewise.sqlite (~15 s, deterministic)
(cd ui && npm ci && npm run build)         # -> ui/dist
.venv/bin/uvicorn api.main:app --port 8000 # UI at http://127.0.0.1:8000, API at /api/*
```

For UI development with hot reload, run `cd ui && npm run dev`. The dev server proxies `/api` to `VITE_API_PROXY`, which defaults to `http://127.0.0.1:8000`.

**Copilot (optional).** Set `ANTHROPIC_API_KEY` in the backend's environment only; `.env.example` lists the variables. Without a key, the Copilot answers deterministically from the database. The key is never sent to the browser, and `/api/health` only reports whether one is configured.

## Tests
```bash
.venv/bin/python -m pytest tests -q   # 73 tests: DB acceptance 1-12, API, Copilot, Digital Twin physics/evidence/API, conversations and cache
python3 -I scripts/twin_validate.py . # regenerate the Digital Twin model validation records (derived/twin/validation.json)
(cd ui && npm run build && npx playwright test)   # 9 browser tests (system Chrome; starts its own server on :8767)
python3 -I scripts/verify_claims.py . # independent re-derivation of every quantitative claim -> derived/claims_check.json
python3 -I scripts/checksum_data.py Data derived/data_sha256.txt --verify   # original NASA files unchanged
```

## Deploy (single container)
```bash
python3 -I scripts/load_db.py . && (cd ui && npm ci && npm run build)
docker build -t firewise .
docker run -p 8000:8000 -v firewise-state:/app/state firewise                          # deterministic Copilot
docker run -p 8000:8000 -v firewise-state:/app/state -e ANTHROPIC_API_KEY=... firewise  # with the language model
```

**User state.** Digital Twin scenarios, Copilot conversations and the answer cache live in `/app/state`, or `$FIREWISE_STATE_DB` outside Docker; the default there is `state/twin_state.sqlite`. Mount a volume to keep them. The scientific database stays read-only. Scenarios and conversations are scoped to a random per-browser workspace key (`X-Workspace`). That is isolation, not user authentication.

The image contains only the API code, the built UI and the 15 MB SQLite database. It contains no raw NASA data and no secrets. It honours `$PORT`, so it runs on Render, Fly.io or Cloud Run as is.

## Data provenance
- **Source.** All 24 PSI investigation records come from `psi.nasa.gov`, saved in `sources/psi_api/` (CC0). The 22 experimental tables are in `sources/psi_tables/`. A sha256 for each is recorded in `sources/sources.csv`.
- **Pipeline:**
  1. `scripts/build_runs.py` normalizes the tables to `derived/runs.csv`. It keeps row keys, source row numbers and statuses, and adds quality flags. Duplicates are marked, not deleted.
  2. `scripts/coverage.py` computes the coverage bands.
  3. `scripts/load_db.py` builds the database and runs validation rules R1–R7.
- **Originals.** The original files in `Data/` are read-only and checksum-verified on every build.
- **Documentation.** `docs/FINAL_DATA_CONTRACT.md`, `docs/FINAL_API_CONTRACT.md`, and `docs/EXECUTION_STATUS.md` for the current state.

Not an official NASA product.
