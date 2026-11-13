# FIREWISE — Change Log

## 2026-11-13 night: Digital Twin, Copilot conversations, UI simplification, deployment packaging
- **Digital Twin:**
  - backend: `api/twin/*`, a state store with migrations 1–3, and schema v2 with the `twin_*` tables
  - UI: `ui/src/twin/*`
  - tests: 42 pytest and 8 Playwright
  - docs: `docs/DIGITAL_TWIN_*.md`
- **Copilot:**
  - saved conversations (`/api/conversations`) and an answer cache; twin entries are scoped to the whole context and the workspace
  - new claim tiers: calculation, model_prediction, unknown
  - citations now picked in a deterministic order
- **Security fixes:**
  - the 422 handler crashed on validator errors and echoed request bodies
  - scenario and conversation routes are now workspace-scoped
  - the cache key covers user-written twin text
- **UI simplification** (`docs/UI_AUDIT.md`):
  - 6 destinations; the Findings page merged into Research Gaps; Compare became a mode of Investigations
  - a design system and progressive disclosure
  - removed the per-page banner and the decorative layers
  - fixed mobile overflow
- **Deployment:**
  - self-contained multi-stage `Dockerfile` with `deploy/firewise.sqlite` (the prebuilt database is committed so hosts can build from git)
  - `render.yaml`, `scripts/package_deploy.sh`, GitHub Actions CI
- **Tests:** `tests/conftest.py` makes pytest location-independent and isolates the state store per test.


## 2026-11-13 evening: hackathon execution (Phases 0–6)
**Not modified:** `Data/` (checksums verified on every DB build), `sources/` (except `sources.csv`, which the telemetry download still running appends to). Background downloads were left running.

### Added
| Path | Purpose |
|---|---|
| `scripts/load_db.py`, `tests/test_load_db.py` | Deterministic SQLite + FTS5 build with validation rules R1–R7; acceptance criteria 1–12 |
| `api/` (`main`, `services`, `copilot`, `db`, `models`), `tests/test_api.py` | FastAPI backend; evidence-grounded Copilot with validator and deterministic fallback |
| `ui/` | The team's FLARE UI (imported unmodified as commit `8c32ee3`), rebranded FIREWISE and wired to the API; new Scenario Explorer and Research Gap Map pages |
| `README.md`, `ui/README.md`, `Dockerfile`, `.dockerignore`, `.env.example` | Run, test and deploy instructions; a single container image |
| `docs/EXECUTION_STATUS.md` | Live status |

### Modified
| File | Change | Reason |
|---|---|---|
| `scripts/build_runs.py` | Rewritten to the data contract: `row_key`, true CSV `source_row`, `row_granularity`, `duplicate_of`, `o2_context`, flag severity | Readiness audit D0 |
| `scripts/coverage.py` | Ambient O₂ only; psia bands with edges at 8.2 and 10.2 | Readiness audit D0 |
| `scripts/verify_claims.py` | Rewritten against the new fields | Schema change |
| `derived/validation.jsonl` | Evidence IDs migrated to schema v1; V11 trap narrowed to pentane *cool-flame* claims (backup in `derived/_superseded/`) | The old trap rejected any mention of pentane, which also appears in the planned-fuels text |
| `derived/curated_facts.json` | **F17**: denominator corrected to 2,007 combustion/aerosol rows (was a stale 1,989) | Stale count |
| `ui/src/data/sampleData.js` | Deleted | Placeholders must not reach the demo |

### Decisions
- The abandoned Next.js prototype (`web/`) was moved out of the repo after the user supplied the FLARE UI.
- Data series colours are `#3987e5` / `#d95926` / `#199e70`, validated against the dark surfaces. FLARE's ember/amber pair failed the normal-vision separation check, so ember is kept for UI chrome only.


## 2026-11-13 ~19:30–20:15 EET: Final readiness audit
**Not modified:**
- `Data/` (checksums verified OK)
- `sources/`
- the pipeline scripts `harvest_psi`, `inventory_*`, `fetch_psi_files`, `build_runs`, `coverage`, `build_records`
- the derived pipeline outputs `runs.*`, `coverage*`, `investigations*`, `psi_*`
- the three background download processes (PIDs 197030, 197088, 241974), left running

Pre-audit copies of every modified file are in `docs/_superseded/` and `derived/_superseded/`.

### Added
| File | Purpose |
|---|---|
| `scripts/verify_claims.py` | Recomputes every quantitative claim from `derived/runs.csv` and raw PSI tables (read-only) |
| `derived/claims_check.json` | Output of the above; source of truth for numbers in docs and tests |
| `docs/FINAL_READINESS_AUDIT.md` | Verdict, issues with root causes, claim-validation matrix, eligibility |
| `docs/FINAL_DATA_CONTRACT.md` | Canonical schema, keys, enums, import process |
| `docs/FINAL_API_CONTRACT.md` | Endpoints, schemas, error and fallback behaviour |
| `docs/P0_ACCEPTANCE_CRITERIA.md` | Screen, backend, science, AI and frontend gates; demo format |
| `docs/KICKOFF_CHECKLIST.md` | Environment, team, dependency graph, `load_db.py` spec and tests |
| `docs/OPEN_DECISIONS.md` | Decisions requiring approval |
| `docs/CHANGELOG.md` | This file |

### Modified data artifacts (hand-curated, not pipeline output)
| File | Change | Reason |
|---|---|---|
| `derived/curated_facts.json` | **F18** rewritten (envelope: 0 / 20 / 27 on an ambient-O₂ basis) | The earlier "35 runs" used a mislabeled pressure band (0.5–0.75 atm ≠ 8.2–10.2 psia) and counted 8 inverse-flame burner-stream O₂ rows |
| | **F01** "never flown" → "absent from 333 documented tests; publication confirms" | Overstatement |
| | **F02** "n-butane" → table term "30% butane"; added the 1 "no" and 171 blank | Precision |
| | **F11** FLEX→CFI numbering → inference stated explicitly; confidence medium | Inference stated as fact |
| | **F06** O₂ marked as derived from CO₂ | Precision |
| | **added F19** (inverse-flame O₂ semantics), **F20** (duplicate rows in NASA tables) | New verified findings |
| `derived/validation.jsonl` | **V02**, **V08**, **V11**, **V12** expected answers corrected | Same reasons as above |
| | **added V33–V35** (inverse O₂, CFI duplicates, missing ≠ zero) | New traps |

### Modified documents (minimal factual corrections + dated banner)
| Document | Change |
|---|---|
| EXECUTIVE_SUMMARY | 35 → 0 envelope finding with bracket and challenge definitions; "test runs across 20 investigations" → "condition records (1,386 unique tests) from 19 flight investigations"; solids wording; pentane wording; FLEX/CFI wording; demo format; scenario naming |
| DATASET_AUDIT | headline 5 corrected; CFI 87 rows (79 unique); E-FIELD 21 rows (20 unique) |
| SCIENTIFIC_ANALYSIS | CFI row; FLEX→CFI paragraph; O₂ documented count split ambient vs burner stream; gap item 7 |
| PROJECT_UNDERSTANDING | counts wording; solids wording |
| RISKS_AND_VALIDATION | 35-item validation set; envelope numbers |
| AI_ARCHITECTURE | false example sentence replaced by a verified one; banner: ranking and streaming superseded |
| PRODUCT_DESIGN | banner (6 screens, Scenario Explorer); demo marked superseded; scenario and pentane lines corrected |
| IMPLEMENTATION_ROADMAP | banner (D0, eligibility gate); demo deliverable → 7-slide deck / ≤ 30 s video |
| TECHNICAL_ARCHITECTURE, DATA_ARCHITECTURE | banners pointing to the FINAL contracts |

### Known items deliberately NOT changed (pending D0 at kickoff)
- `scripts/build_runs.py`:
  - add `row_key`, `test_label`, `row_granularity`, the `*_context` fields, `gravity_regime`/`platform` and
    `duplicate_of`
  - generic duplicate detection
  - emit flags after the BRE split
- `scripts/coverage.py`: the pressure-band label `0.5-0.75 atm (8.2-10.2 psia)` is wrong (the band is
  7.35–11.0 psia), and inverse flames must be excluded. **`derived/coverage_summary.json` currently contains the
  superseded value 35**; use `claims_check.json` until D0 is done.
