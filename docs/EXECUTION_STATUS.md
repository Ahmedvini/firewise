# FIREWISE: Execution Status

_Updated 2026-11-13, night. Concise and live; the newest state wins._

## Completed
| Work | Result |
|---|---|
| Data pipeline + scientific DB | 2,019 rows and 1,220 flags. Deterministic `load_db.py`, now **schema v2**, adding the twin reference tables (rules R8, R9). |
| FastAPI backend + Copilot | Evidence-grounded answers with a validator and a deterministic fallback, plus **saved conversations** and an **answer cache**. |
| UI (team's FLARE app, rebranded FIREWISE) | Wired to the API. |
| **Digital Twin** (`api/twin/*`, `ui/src/twin/*`) | - One shared scenario state across the 3D habitat (React Three Fiber), the 2D engineering view, NASA evidence (exact plus transparent nearest), physics (Models A–D with metadata), scenarios (save, version, duplicate, compare, history, simulation runs) and reports. - The twin-aware Copilot answers all 8 example questions without a key. - Scenarios are scoped to a workspace key. Docs: `docs/DIGITAL_TWIN_*.md`. |
| Model validation | - **Model B transport properties are validated** against independent air correlations: max deviation 0.51% (viscosity) and 1.03% (conductivity), within the ±2% reference accuracy over 250–400 K. - Models A, C and D are verified. - No combustion model is implemented. |
| **UI simplification** | 6 destinations; a design system (`components/ui.jsx`, tokens); progressive disclosure on every page; mobile overflow fixed. See `docs/UI_AUDIT.md`. |
| Deployment packaging | - Self-contained multi-stage `Dockerfile` (builds the UI, ships `deploy/firewise.sqlite`). - `render.yaml` Blueprint. - GitHub Actions CI (backend tests, UI build, Docker smoke test). |
| GitHub | Private repo https://github.com/Ahmedvini/firewise (`main`). First CI run passed all three jobs: backend, frontend, docker. |

## Test results (latest run)
- `pytest tests -q`: **73 passed**: 11 DB acceptance, 16 API/Copilot, 42 Digital Twin, 4 conversations and cache.
- CI-equivalent run (`FIREWISE_DB=deploy/firewise.sqlite`, without the DB-build tests): **62 passed**.
- Playwright on system Chrome: **10/10**. Coverage:
  - every page
  - 3D zone click, orbit, zoom, pan, cameras and overlays
  - shared 3D/2D state; invalid input rejected
  - evidence matches equal the API; source rows open; record import keeps NASA status
  - Calculations view
  - save, reload, duplicate, compare, history, simulation run, report and delete
  - twin Copilot
  - conversations: switch, reload, cache, rename, delete
  - six-item navigation, legacy links, collapsed sections, no overflow at 390 px
  - render loop
- `scripts/twin_validate.py`: 0 failed records. `Data/` checksums are unchanged.
- **Docker:** the self-contained image (307 MB) builds from a clean context; health, UI and Copilot pass.
- **Performance:** the habitat view runs at 60 fps on an Intel UHD GPU and about 22 fps under software WebGL.
- **Security:** no secrets in git, the UI bundle or the image. Scenario and conversation routes are workspace-scoped. Twin cache entries are scoped to the full context and the workspace. 422 errors never echo request bodies.

## Current state
- Runs locally at `http://127.0.0.1:8765`.
- The Copilot runs in deterministic mode, because no API key is configured. The LLM path is covered by mocked tests only.

## Blockers and decisions for the team
1. **Hosting account (the only open deployment step).** No hosting credentials exist on the build machine. In Render: sign in with GitHub → New → Blueprint → grant access to `Ahmedvini/firewise` → Apply. The service builds from `render.yaml` and serves at `https://firewise-<id>.onrender.com`. Account creation and OAuth consent are the team's action.
2. **Free-plan limits.** The service sleeps when idle, and saved scenarios and conversations reset on restart. Add a paid disk at `/app/state` if persistence matters.
3. **Optional `ANTHROPIC_API_KEY`** on the host only.
4. **Telemetry download.** It stopped (DNS failures) and was intentionally not restarted. `sources/sources.csv` carries its partial manifest additions and is left uncommitted.

## Remaining opportunities
- Combustion models (droplet d²-law against FLEX data, extinction, flame spread) with validation.
- Model B validation at O₂-enriched compositions.
- Real-gas check for Model A.
- User accounts for cross-device scenarios.
- UX items listed in `docs/UI_AUDIT.md`.
