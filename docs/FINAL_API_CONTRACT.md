# FIREWISE — Final API Contract (P0)

*This contract supersedes the endpoint lists in TECHNICAL_ARCHITECTURE, IMPLEMENTATION_ROADMAP and
PRODUCT_DESIGN.*

**Conventions:**
- Base path `/api`. JSON, UTF-8, **snake_case** on both sides.
- Pydantic models are the single source of truth. Generate TypeScript types from `/openapi.json` with
  `openapi-typescript`; do not hand-write duplicate types.
- **Read-only** except `POST /api/ask`.
- No authentication; no secrets ever leave the backend.

---

## 1. Shared types
```ts
type Status = "measured" | "derived" | "reported" | "specified" | "missing";
interface Quantity {            // the ONLY representation of O2 / pressure / flow anywhere in the API
  min: number | null; max: number | null; unit: "pct" | "atm" | "cm_s";
  status: Status; status_label: string;        // e.g. "Set-point / specified", "Not documented"
  context: "ambient" | "burner_stream" | "envelope" | "chamber" | "forced_duct" | "coflow" | "inlet"
         | "quiescent" | "fan_setting_uncalibrated" | null;
  psia?: { min: number; max: number } | null;  // pressure only, convenience conversion
}
interface Provenance { row_key: string; source_table_id: string; source_file: string; source_row: number;
                       source_sha256: string; psi_url: string; evidence_id: string; }   // "row:<row_key>"
interface Page<T> { items: T[]; total: number; limit: number; offset: number; }
interface ApiError { error: { code: string; message: string; details?: Record<string, unknown> } }
interface BuildInfo { schema_version: number; build_utc: string; n_runs: number; n_flags: number; claims_check_sha256: string }
```
**Pagination:** `limit` (default 50, max 500), `offset` (default 0). Responses include `total`. Ordering is stable,
by the documented sort key with `row_key` as the tiebreak.

**Errors:** `400 invalid_parameter`, `404 not_found`, `422 validation_error`, `500 internal_error`,
`503 copilot_unavailable`, `504 copilot_timeout`. Every error uses the `ApiError` body.

---

## 2. Endpoints
| # | Method / route | Purpose | Key parameters | Response |
|---|---|---|---|---|
| 1 | `GET /api/health` | liveness + DB loaded | — | `{status: "ok", build: BuildInfo, copilot_configured: boolean}` (never exposes the key) |
| 2 | `GET /api/summary` | Mission Control numbers | — | `{investigations: 24, investigations_with_tables: 20, condition_records: 2007, unique_individual_tests: 1386, by_fuel_class, by_granularity, by_data_class, partial_gravity_runs: 0, scenario_counts: {id: n}, flags_total, build}`; each number carries `evidence_id: "agg:<name>"` |
| 3 | `GET /api/investigations` | Explorer list | `q`, `fuel_class[]`, `platform[]`, `data_class[]`, `o2_min`, `o2_max`, `p_min_atm`, `p_max_atm`, `o2_context=ambient` (default), `limit`, `offset`, `sort=id\|acronym\|n_runs` | `Page<InvestigationCard>`: `{id, acronym, title, platform, facility, data_class, fuel_classes, n_condition_records, n_unique_tests, o2: Quantity, pressure: Quantity, flow: Quantity, n_publications, n_flags, psi_url, doi_url}` |
| 4 | `GET /api/investigations/{id}` | Investigation detail | — | card fields + verbatim `objective`, `hypothesis`, `approach`, `research_impacts` (each `{value, evidence_id}`), `publications[]`, `data_products{n_files_listed, listed_gb, total_gb, listing_complete, folders}`, `flags_by_code{}`, `relations[]`, `curated_facts[]`, `local_files[]` |
| 5 | `GET /api/investigations/{id}/runs` | "How tests differed" tab | `granularity[]`, `include_duplicates=false`, `changed_only=true`, `limit`, `offset` | `{varying_columns: string[], constant_columns: {name: value}, page: Page<Run>}`; `Run = {row_key, test_label, row_granularity, duplicate_of, fuel_or_material, fuel_class, geometry, diluent, gravity_regime, platform, o2: Quantity, pressure: Quantity, flow: Quantity, observations: Observation[], flags: string[], provenance: Provenance}` |
| 6 | `GET /api/runs` | cross-investigation filter (scatter, scenario drill-down) | `investigation_id[]`, `fuel_class[]`, `o2_context=ambient`, `o2_min`, `o2_max`, `p_min_atm`, `p_max_atm`, `status_o2[]`, `status_p[]`, `documented_only=true`, `include_duplicates=false`, `limit`, `offset` | `Page<Run>` |
| 7 | `GET /api/distributions` | variable distributions | `variable=o2_pct\|p_atm\|flow_cm_s`, `group_by=fuel_class\|investigation\|status`, `o2_context=ambient`, `bins=20` | `{variable, unit, groups: [{key, n_documented, n_missing, histogram: [{lo, hi, n}], status_counts}]}`. Missing values are **counted, never binned** |
| 8 | `GET /api/scenarios` | preset definitions | — | `[{id, label, o2_window_pct, p_window_psia, gravity, gravity_evidence_runs, source}]` |
| 9 | `GET /api/scenarios/{id}/evidence` (or `POST /api/scenarios/custom/evidence` with a window body) | ranked evidence for a habitat scenario | `fuel_focus=solid\|any` | §3 |
| 10 | `GET /api/compare` | Comparison Studio | `ids=PSI-26,PSI-100` (2–4) | `{investigations: [..cards], features: [{name, type, values: {id: any}, comparable: boolean, distance: number \| null, note}], compared_on: "k/n", incompatibilities: [{a, b, reason}], shared: [...], different: [...], missing: [...]}` |
| 11 | `GET /api/gaps` | Research Gap Map | `dims=gravity_regime,fuel_class,o2_band,p_band` | `{cells: [{key: {...}, runs, investigations, literature_only: string[]}], bands: {o2: [...], p: [...]}, definitions}`; ambient O₂ only |
| 12 | `GET /api/evidence/{evidence_id}` | resolve any citation | — | `{evidence_id, kind, text \| row \| value, provenance, url}`; 404 if unknown |
| 13 | `POST /api/ask` | Copilot | body `{question: string (≤ 1000 chars), scenario_id?: string}` | §4 |

---

## 3. Scenario evidence ranking: semantics (not risk)
```json
{
  "scenario": {"id": "moon_base_challenge", "o2_window_pct": [30, 100], "p_window_psia": [0, 10.2], "gravity": "partial_gravity"},
  "gravity_evidence": {"matching_runs": 0, "statement": "PSI contains no partial-gravity combustion runs; all evidence below is microgravity."},
  "ranking_method": "lexicographic: (1) in_window_tests desc, (2) near_window_tests desc, (3) material_match desc, (4) id asc",
  "items": [{
    "investigation_id": "PSI-159",
    "in_window_tests": {"n": 20, "o2_status": {"measured": 20}, "p_status": {"reported": 20}, "evidence_id": "agg:scenario:moon_base_challenge:PSI-159"},
    "near_window_tests": {"n": 0, "tolerance": "±2 pts O2, ±1 psia"},
    "undocumented": {"o2_missing": 0, "p_missing": 0},
    "material_match": {"value": "gaseous", "matches_focus": false},
    "gravity_match": "none (microgravity only)"
  }],
  "label": "Evidence relevance — not a fire-risk or flammability prediction"
}
```
**Rules:**
- A run counts as in-window **only if both** ambient O₂ and pressure are documented and inside the window.
- Missing pressure **never** matches; those runs are counted under `undocumented`.
- Inverse-flame burner-stream O₂ is excluded.
- Gravity is never blended into a score. It is reported separately as a count (0 for partial g).
- There is no composite number, so there are no hidden weights.

---

## 4. Copilot `/api/ask`

**Response (HTTP 200).** Returned only after the server-side validator passes; it is **not streamed**.
```json
{
  "status": "answered | insufficient_evidence | partial",
  "claims": [{"text": "...", "tier": "measured|reported|literature|interpretation",
              "evidence_ids": ["row:PSI-159:cfi-g-normal-flames:r34"],
              "numbers": [{"value": 0.39, "unit": "mole fraction", "aggregation": "range over 7 tests", "evidence_id": "agg:cfig_cool_flames"}]}],
  "limitations": ["..."], "gaps": ["..."], "related_investigations": ["PSI-39"],
  "evidence": [{"evidence_id": "...", "kind": "...", "snippet": "...", "url": "..."}],
  "model": {"id": "claude-opus-5-5", "effort": "medium"}, "latency_ms": 0, "cached": false
}
```
**Model call:**
- Anthropic Python SDK, `client.messages.parse(model="claude-opus-5-5", max_tokens=16000,
  output_config={"effort": "medium"}, output_format=CopilotAnswer, …)`.
- Thinking is adaptive and always on for this model; **omit the `thinking` parameter**.
- No `temperature`.
- Prompt caching on the frozen system prompt + catalog.
- Server-side refusal fallback: beta `server-side-fallback-2026-07-01`, `fallbacks: "default"`.
- Client `timeout=45s`, `max_retries=1`.

**Validator, which must pass before returning:**
1. Every `evidence_id` exists in this request's evidence pack.
2. Every number in `claims[].text` equals (within rounding) a value in a cited item, with a matching unit.
3. **Aggregates (counts, ranges, percentages) may only come from `agg:*` items computed by SQL.** The model may not
   compute them.
4. A `measured` tier requires all cited items to have status `measured`. Interpretation claims cite the evidence
   they interpret.
5. No claim mentions partial-g, lunar or Martian behaviour except as "no evidence in PSI".

**Deterministic failure behaviour:**

| Condition | Behaviour |
|---|---|
| `ANTHROPIC_API_KEY` missing / API down / 5xx / connection error | `503 copilot_unavailable` + `fallback`: cached validated answer if the question matches a canonical intent, else an evidence-only list (`status: "insufficient_evidence"`, no prose) |
| Timeout (> 45 s) | `504 copilot_timeout` + the same fallback |
| Malformed / schema-invalid output | one retry; then evidence-only response |
| Claim fails validation | drop the claim; add a limitation "1 statement removed: unsupported citation"; if none remain → `insufficient_evidence` |
| Retrieval returns < 2 evidence items | no model call; `insufficient_evidence` with what was searched |
| `stop_reason == "refusal"` (after fallback) | evidence-only response |

The UI never crashes on any of these; the other 5 screens never call the LLM.
