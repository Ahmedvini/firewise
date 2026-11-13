# FIREWISE — Final Data Contract (canonical)

*Supersedes the schema sections of `DATA_ARCHITECTURE.md` where they differ. Store: **SQLite 3 + FTS5**, one file
`build/firewise.sqlite`, rebuilt from `derived/` by `scripts/load_db.py`. No migrations: the DB is a disposable
build artifact.*

---

## 1. Entity levels (what each table represents)
| Level | Table | One row = |
|---|---|---|
| PSI investigation | `investigation` (+ `investigation_meta`) | one PSI record (24) |
| Source table | `source_table` | one PSI experimental-table CSV (22) |
| Condition record ("run") | `run` | one normalized row of a source table, at the granularity stated in `row_granularity` |
| Experimental conditions | columns of `run` (O₂, P, flow, fuel, geometry, diluent, gravity) | exactly **one** representation per variable |
| Measurements / outcomes | `observation` | one variable of one run (long format) |
| Measurement status | `*_status` columns, `observation.status` | enum §3 |
| Source files / rows | `run.source_table_id`, `run.source_row`, `run.raw_json`, `source_table.sha256` | — |
| Publications | `publication` | one PSI-listed publication |
| Data-quality flags | `quality_flag` | one finding on one run or table |
| Derived values | `observation` with status `derived` (e.g. T_ad, Z_st, Saffire-II O₂) | — |
| Relationships | `relation` | typed edge with evidence (FLEX↔CFI, DAFT→SAME, shared facility…) |
| Claims and evidence | `claim`, `evidence` (+ FTS5 `passage`) | citable units |

---

## 2. Keys and identity
- **`run.row_key`** (PRIMARY KEY, TEXT) = `{investigation_id}:{table_slug}:r{source_row}` plus a `:{split}` suffix
  only where one source row is deliberately split.
  - Example: `PSI-69:flex:r2`.
  - BRE example: `PSI-20:acme-bre:r3:o2=26.5`.
  - `table_slug` = lower-cased text after `Experimental table_` in the file name, with non-alphanumerics → `-`
    (e.g. `cfi-g-normal-flames`).
  - `source_row` = 1-based spreadsheet row number, with the header as row 1.
  - **Stable** as long as the NASA file is unchanged; the file's sha256 is recorded.
- **`run.test_label`** = the investigation's own test identifier (`21265C3`, `FLEX 114 / C11M201`, `S2`). **Not
  unique.** Source tables contain exact duplicates (CFI ×8, E-FIELD ×1, SPICE ×34) and SAME-R reuses #57 for
  two materials.
- **`run.duplicate_of`** = `row_key` of the first identical source row (NULL otherwise). Duplicates are loaded,
  flagged, and **excluded from counts** by default.
- **`investigation.id`** = `PSI-NN`.
- **Evidence IDs** (citations):

  | Pattern | Points to |
  |---|---|
  | `inv:PSI-69#objective` | an investigation record field |
  | `row:<row_key>` | a run row |
  | `obs:<row_key>#<variable>` | one observation |
  | `fact:F06` | a curated fact |
  | `agg:<name>` | a server-computed aggregate with a stored SQL definition |
  | `pdf:<sha12>#p<N>` | a report page |
  | `file:<path>` | a downloaded file |

---

## 3. Enumerations
| Field | Allowed values | Display label |
|---|---|---|
| `*_status` | `measured` | Measured |
| | `derived` (computed from measurements, e.g. Saffire-II O₂ from CO₂, T_ad) | Derived |
| | `reported` (stated approximately or qualitatively, e.g. `~21%`, "approx p") | Reported (approx.) |
| | `specified` (set-point, commanded or design envelope) | **Set-point / specified** |
| | `missing` | **Not documented** |
| `o2_context` | `ambient` (chamber atmosphere) · `burner_stream` (inverse flames: oxidizer issued from the burner) · `envelope` (FLEX-2 design range) | shown next to the value |
| `p_context` | `chamber` · `envelope` | |
| `flow_context` | `forced_duct` · `coflow` · `inlet` · `quiescent` · `fan_setting_uncalibrated` (BASS-II) | |
| `row_granularity` | `test` · `test_point` (SPICE condition within an ignition) · `test_day` · `test_day_o2_level` (BRE) · `test_date` (SLICE) · `condition_envelope` (FLEX-2) · `session` (DAFT) · `material_condition_set` (SAME) · `flow_visualization` (Saffire F-rows) · `figure_reference` (PSI-142) | |
| `gravity_regime` | `microgravity` · `normal_gravity` · `partial_gravity` (PSI currently has **0** rows) | |
| `platform` | `ISS-CIR` · `ISS-MSG` · `ISS-cabin` · `Cygnus` | |
| `fuel_class` | `gaseous` · `solid_emulating_gas_burner` · `liquid_droplet` · `solid` · `smoke_source_nonflaming` · `dust_aerosol` · `none` | |
| `data_class` | `A` raw/telemetry · `B` analyzed · `C` summary table + publications · `D` metadata/docs · `E` not retrievable | |
| `claim.tier` | `measured` · `reported` · `literature` · `interpretation` | |

**`inferred` is not a permitted data status.** Inference exists only as a `claim.tier = interpretation`.

---

## 4. Schema (DDL, schema_version = 1)
```sql
PRAGMA foreign_keys = ON;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);       -- schema_version, build_utc, input sha256s, counts
CREATE TABLE investigation (
  id TEXT PRIMARY KEY CHECK (id GLOB 'PSI-[0-9]*'),
  acronym TEXT, title TEXT NOT NULL, doi TEXT, psi_url TEXT NOT NULL, license TEXT,
  project_type TEXT NOT NULL,                                       -- 'Microgravity Investigation' | 'Ground Investigation'
  platform TEXT, hardware TEXT, sub_research_area TEXT, start_date TEXT, end_date TEXT,
  objective TEXT, hypothesis TEXT, approach TEXT, research_impacts TEXT,   -- verbatim PSI text
  n_files_listed INTEGER NOT NULL, listed_gb REAL NOT NULL, total_gb REAL NOT NULL,
  listing_complete INTEGER NOT NULL CHECK (listing_complete IN (0,1)),
  record_sha256 TEXT NOT NULL                                       -- of sources/psi_api/PSI-NN.json
);
CREATE TABLE investigation_meta (                                   -- curated, from derived/investigation_meta.json (D0)
  investigation_id TEXT PRIMARY KEY REFERENCES investigation(id),
  data_class TEXT NOT NULL CHECK (data_class IN ('A','B','C','D','E')),
  facility TEXT, insert_hw TEXT, primary_fuel_class TEXT, row_granularity_default TEXT, notes TEXT, source TEXT NOT NULL
);
CREATE TABLE source_table (
  id TEXT PRIMARY KEY,                                              -- '{investigation}:{table_slug}'
  investigation_id TEXT NOT NULL REFERENCES investigation(id),
  file_name TEXT NOT NULL, local_path TEXT NOT NULL, sha256 TEXT NOT NULL, n_source_rows INTEGER NOT NULL
);
CREATE TABLE run (
  row_key TEXT PRIMARY KEY,
  investigation_id TEXT NOT NULL REFERENCES investigation(id),
  source_table_id TEXT NOT NULL REFERENCES source_table(id),
  source_row INTEGER NOT NULL CHECK (source_row >= 2),
  test_label TEXT, row_granularity TEXT NOT NULL, duplicate_of TEXT REFERENCES run(row_key),
  date_text TEXT, fuel_or_material TEXT, fuel_class TEXT NOT NULL, geometry TEXT, diluent TEXT,
  gravity_regime TEXT NOT NULL, platform TEXT NOT NULL,
  o2_min_pct REAL, o2_max_pct REAL, o2_status TEXT NOT NULL, o2_context TEXT,
  p_min_atm REAL, p_max_atm REAL, p_status TEXT NOT NULL, p_context TEXT,
  flow_min_cm_s REAL, flow_max_cm_s REAL, flow_status TEXT NOT NULL, flow_context TEXT,
  outcome_text TEXT, raw_json TEXT NOT NULL,
  CHECK ((o2_min_pct IS NULL) = (o2_status = 'missing')),
  CHECK ((p_min_atm IS NULL) = (p_status = 'missing')),
  CHECK ((flow_min_cm_s IS NULL) = (flow_status = 'missing')),
  CHECK (o2_min_pct IS NULL OR (o2_min_pct >= 0 AND o2_max_pct <= 100 AND o2_min_pct <= o2_max_pct)),
  CHECK (p_min_atm IS NULL OR (p_min_atm > 0 AND p_min_atm <= p_max_atm))
);
CREATE INDEX run_inv ON run(investigation_id);
CREATE INDEX run_o2 ON run(o2_context, o2_min_pct, o2_max_pct);
CREATE INDEX run_p ON run(p_min_atm, p_max_atm);
CREATE TABLE observation (
  row_key TEXT NOT NULL REFERENCES run(row_key), variable TEXT NOT NULL,
  value_num REAL, value_text TEXT, unit TEXT, status TEXT NOT NULL, gravity_regime TEXT NOT NULL,
  source_column TEXT NOT NULL,
  PRIMARY KEY (row_key, variable, gravity_regime)
);
CREATE TABLE quality_flag (
  id INTEGER PRIMARY KEY, row_key TEXT REFERENCES run(row_key), source_table_id TEXT REFERENCES source_table(id),
  investigation_id TEXT NOT NULL REFERENCES investigation(id), code TEXT NOT NULL, message TEXT NOT NULL
);
CREATE TABLE publication (id INTEGER PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigation(id),
  title TEXT NOT NULL, authors TEXT, doi TEXT, status TEXT);
CREATE TABLE data_file (investigation_id TEXT NOT NULL REFERENCES investigation(id), folder TEXT, file_name TEXT NOT NULL,
  bytes INTEGER, ext TEXT, downloaded INTEGER NOT NULL DEFAULT 0, local_path TEXT, sha256 TEXT,
  PRIMARY KEY (investigation_id, file_name));
CREATE TABLE relation (id INTEGER PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL,
  evidence_id TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('verified','inferred')));
CREATE TABLE claim (id TEXT PRIMARY KEY, field TEXT, value TEXT NOT NULL, status TEXT, tier TEXT NOT NULL,
  source TEXT NOT NULL, locator TEXT, confidence TEXT, caveat TEXT);
CREATE TABLE claim_investigation (claim_id TEXT REFERENCES claim(id), investigation_id TEXT, PRIMARY KEY (claim_id, investigation_id));
CREATE TABLE aggregate (name TEXT PRIMARY KEY, sql TEXT NOT NULL, value_json TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE coverage_cell (gravity_regime TEXT, fuel_class TEXT, o2_band TEXT, p_band TEXT, o2_context TEXT,
  runs INTEGER NOT NULL, investigations TEXT, PRIMARY KEY (gravity_regime, fuel_class, o2_band, p_band, o2_context));
CREATE VIRTUAL TABLE passage USING fts5(evidence_id UNINDEXED, investigation_id UNINDEXED, kind UNINDEXED, text,
  tokenize = 'porter unicode61');
```

**`relation` (P0 seed):**

| Source | Target | Type | Evidence | Status |
|---|---|---|---|---|
| PSI-47 | PSI-102 | `qualified_instrument_for` | `inv:PSI-47#objective` | verified |
| PSI-69 | PSI-39 | `shares_test_number_series` | `fact:F11` | inferred |
| PSI-101 | PSI-102 | `reflight_of` | `inv:PSI-101#objective` | verified |
| 6 ACME investigations | ACME | `uses_insert` | — | verified |
| BASS/BASS-II/SPICE/SLICE | MSG | `uses_facility` | — | verified |

---

## 5. Units and conversions (single representation per variable)
| Variable | Stored unit | Conversion from source |
|---|---|---|
| O₂ | mole % | mole fraction × 100; `NNNN%` artifacts ÷ 100 (flagged) |
| Pressure | atm | mmHg ÷ 760; bar × 0.986923; psia ÷ 14.6959. **UI shows atm and psia** |
| Flow | cm/s | as reported. Fan display units are **not** converted (flow_status `missing`, the raw value goes to an observation) |
| Lengths and times | as reported (mm, cm, s) | none |

---

## 6. Missing-value semantics
- `NULL` together with status `missing` means "not documented in the PSI source". It is never 0, never "ambient", and
  never imputed.
- Categorical blanks (CFI-G `Cool flame?`) are stored as `value_text = 'not_recorded'` with status `missing`.
  They must **never** be counted as "no".
- `RAMPED`, `n/a`, `Insignificant`, `�`: kept in `raw_json`, normalized to missing (or to a text observation) and
  flagged.

---

## 7. Scenario definitions (data, versioned in `aggregate` and `/api/scenarios`)
| id | Label | Window (ambient O₂ only) | Gravity | Source |
|---|---|---|---|---|
| `iss` | ISS cabin | 20–22% O₂, 14.2–15.2 psia | microgravity | ISS nominal |
| `exploration_envelope` | Exploration envelope (FIREWISE definition) | 30–36% O₂, 8.2–10.2 psia | (none: atmosphere only) | spans FM2 34% / 8.2 psia and the challenge's ≤10.2 psi |
| `moon_base_challenge` | Moon base (challenge text) | ≥30% O₂, ≤10.2 psia | partial g 0.16 g → **0 PSI evidence** | challenge page |
| `fm2_point` | FM2 elevated-O₂ test point | 32–36% O₂, 7.2–9.2 psia | lunar g (planned) | NTRS 20240015307 |
| `mars` | Mars habitat | user-set atmosphere | partial g 0.38 g → **0 PSI evidence** | — |

**Expected counts** (acceptance tests; source `claims_check.json`):

| Scenario | Runs |
|---|---|
| `exploration_envelope` | **0** |
| `moon_base_challenge` | **20** (all CFI-G) |
| `fm2_point` | **10** (all CFI-G) |

---

## 8. Validation rules (enforced by `load_db.py`; any failure aborts the build)
1. Every `run` has `source_table_id` + `source_row` + `raw_json`, and the source file's sha256 matches `sources/sources.csv`.
2. `row_key` is unique. `duplicate_of` is set for exact duplicate source rows (except the BRE intentional split).
3. Status/value consistency (the CHECK constraints above). Statuses come only from the §3 enum.
4. Every `quality_flag.row_key` exists (**no orphans**).
5. `o2_context = 'burner_stream'` for every Flame Design / CFI-G inverse row. Scenario matching and the gap map use
   `ambient` only.
6. Counts reproduce `derived/claims_check.json`:
   - `combustion_aerosol_rows` = 2,007
   - `unique_individual_tests` = 1,386
   - solids = 264
   - `ambient_A` = 0, `ambient_B` = 20, `ambient_D` = 27
   - partial-g = 0
7. `Data/` checksums are unchanged (`checksum_data.py --verify`).

---

## 9. Import process
**Prerequisites:**
- **D0 pipeline corrections** (before `load_db.py`, ~1.5 h):
  - `build_runs.py` emits `row_key`, `test_label`, `row_granularity`, `o2_context`, `p_context`, `flow_context`,
    `gravity_regime`, `platform` and `duplicate_of`
  - generic duplicate detection
  - flags keyed by `row_key` after splits
  - `coverage.py`: ambient-only, correctly labelled pressure bands
  - new `derived/investigation_meta.json` (data class, facility, insert; source = DATASET_AUDIT §3)
  - re-run `verify_claims.py`
- **`load_db.py` steps** (deterministic):
  1. Delete and recreate `build/firewise.sqlite`; apply the DDL; write `meta.schema_version = 1`.
  2. Load `investigation` from `sources/psi_api/*.json` sorted by number. Then `investigation_meta`, `publication`,
     `data_file` (from `derived/psi_files.csv`, marking downloaded files via `sources/sources.csv`).
  3. Load `source_table` (with sha256), then `run` sorted by `row_key`, then `observation` (P0 variable map below),
     then `quality_flag`.
  4. Load `claim` from `curated_facts.json`; `relation` seed; `aggregate` rows (SQL text + computed value);
     `coverage_cell`.
  5. Fill the FTS5 `passage` table: investigation text fields, facts, one summary sentence per (investigation,
     run group) generated from SQL, and report pages (D2, P0 optional).
  6. Run the validation rules (§8). Write the counts and input sha256s to `meta`. Then `VACUUM`.
- **Determinism:** identical inputs give identical table contents. `build_utc` is the only volatile value and is
  excluded from the rebuild-equality test.

**P0 observation map (minimum):**

| Investigation | Variables |
|---|---|
| FLEX | `droplet_d0_mm`, `extinction_d_mm`, `burning_rate` (unit = header text, unverified), `burn_time_s`, `test_end` |
| CFI-G | `cool_flame`, `hot_ignition`, `burn_time_s`, `end_mode`, `tad_K` (derived), `zst` (derived) |
| Flame Design | `tad_K`, `zst` (derived) |
| Saffire | `burn_time_s`, `flow_direction`; Saffire-II `burn_length` and `spread` × {microgravity, normal_gravity} |
| BASS-II | `o2_final_pct`, `co2_initial/final_pct`, `co_initial/final_ppm` (measured) |
| SAME / SAME-R | `weight_loss_mg_min`, `aging_s`, `rt_r0` (status reported; meaning unverified) |
| Test-day tables | `flames_ignited` (count, reported) |


---

## Schema v2 addendum (2026-11-13): Digital Twin
**Scientific database** (`build/firewise.sqlite`, deterministic, read-only), new tables loaded by `scripts/load_db.py`:
| Table | Content | Source | Rule |
|---|---|---|---|
| `twin_environment(id, name, body_json)` | habitat templates (geometry, zones, slots, monitoring points, equipment) | `derived/twin/environments.json` | R8: zones tile `[0,1]` without gaps |
| `twin_zone(environment_id, id, name, x_start, x_end, purpose)` | zone fractions along the habitat axis | same | CHECK `0 ≤ x_start < x_end ≤ 1` |
| `twin_validation(id, model_id, output, kind, status, reference, record_json)` | physics model verification/validation records | `derived/twin/validation.json` (from `scripts/twin_validate.py` + `derived/twin/reference_data.json`) | R9: no record with status `failed` |

**User-state store** (`$FIREWISE_STATE_DB`, default `state/twin_state.sqlite`, never committed). It holds no scientific records. Versioned migrations:
1. scenarios, versions, simulation runs
2. workspace owner hash
3. Copilot conversations, messages and answer cache

See `docs/DIGITAL_TWIN_ARCHITECTURE.md`.

**Twin value statuses:** `user_defined`, `measured`, `derived`, `reported`, `specified`, `simulated`, `not_documented`. NASA statuses are kept when a record's conditions are imported. `null` is never zero.
