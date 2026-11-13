# FIREWISE — P0 Acceptance Criteria

**Scope (frozen):**
- **6 screens**: Mission Control, Scenario Explorer, Investigation Explorer (with the Run Table tab), Comparison
  Studio, Research Gap Map, Copilot.
- Five of them must work **with the LLM disabled**.
- The expected numbers below come from `derived/claims_check.json`. If the data changes, regenerate the file and
  update these numbers in the same commit.

---

## 1. Screen requirements

### S1 Mission Control
| Item | Requirement |
|---|---|
| Purpose / user | One-glance state of NASA combustion evidence. All users |
| Data / API | `/api/summary`, `/api/distributions?variable=o2_pct&group_by=fuel_class`, `/api/runs?documented_only=true` (O₂ × P scatter, ambient only) |
| Visuals | KPI tiles: 24 investigations · 2,007 condition records · 1,386 unique tests · **0 partial-g**. Fuel-class bar. O₂ × P scatter coloured by fuel class, shaped by status. Data-class (A–E) bar |
| States | Loading skeletons. Error: "Data service unavailable" with retry. Empty is impossible (abort the build if the DB is empty) |
| Acceptance | KPI values equal `claims_check.json`. Each tile links to its `agg:` evidence. Hover on a point shows status, source file and row. Inverse-flame points are not plotted as atmosphere |

### S2 Scenario Explorer
| Item | Requirement |
|---|---|
| Purpose / user | Which investigations hold evidence for a habitat atmosphere. Fire-safety engineer |
| Data / API | `/api/scenarios`, `/api/scenarios/{id}/evidence`, `/api/runs` (drill-down) |
| Visuals | Preset chips + custom window form (O₂ %, psia). Ranked table with columns: in-window, near-window, undocumented, material match, gravity evidence. Banner with the gravity statement. Label: "Evidence relevance — not fire risk" |
| States | No in-window evidence → explicit "0 documented tests in this window" plus the near-window list |
| Acceptance | `exploration_envelope` → **0 in-window**. `moon_base_challenge` → **20 in-window, all PSI-159**, partial-g evidence 0. `fm2_point` → **10**. Missing pressure never counted. The ranking method text is visible |

### S3 Investigation Explorer (+ Run Table tab)
| Item | Requirement |
|---|---|
| Purpose / user | Find and understand investigations; see how tests differed. Scientists, students |
| Data / API | `/api/investigations`, `/api/investigations/{id}`, `/api/investigations/{id}/runs`, `/api/evidence/{id}` |
| Visuals | Filterable cards. Detail page: verbatim objective, tested ranges with status chips, data products, publications, flags. Run Table tab: varying columns shown, constant columns collapsed, duplicates hidden by default (toggle), flags inline, "source row" link |
| States | No matches → "No investigation matches; clear filters". Investigation with 0 rows (PSI-60/62/115/117) → "No experimental table in PSI" |
| Acceptance | All 24 investigations listed. CFI shows **87 rows / 79 unique tests**. FLEX run table shows 274 rows with varying O₂, P, diluent and fuel. Every value resolves to its source row |

### S4 Comparison Studio
| Item | Requirement |
|---|---|
| Purpose / user | Compare 2–4 investigations. Scientists |
| Data / API | `/api/compare` |
| Visuals | Side-by-side features with comparable / not-comparable markers, a "compared on k/n features" line, overlaid O₂ and P ranges, an incompatibility banner |
| States | Fewer than 2 selected → prompt. Incompatible pair → banner stating why (e.g. normal vs inverse flames; dust vs smoke) |
| Acceptance | BASS vs Saffire-III shows: MSG vs Cygnus, sizes, flow up to 40 vs 30 cm/s, O₂ not documented vs not documented, pressure not documented for both. DAFT vs SAME shows the incompatibility "dust vs pyrolysis smoke" and the relation "qualified instrument for". The word "equivalent" is never displayed |

### S5 Research Gap Map
| Item | Requirement |
|---|---|
| Purpose / user | Where NASA PSI has no documented runs. Planners, scientists |
| Data / API | `/api/gaps` |
| Visuals | Heatmap of gravity × fuel class × O₂ band × P band, ambient O₂ only. Bands labeled in **atm and psia correctly**. Literature-only overlays (LUCI, FM2) drawn dashed. Click → runs or "0 documented runs" |
| States | Every cell renders, including 0 |
| Acceptance | partial_gravity row = 0 everywhere. Solid × any pressure band = 0. The cell (30–36%, 8.2–10.2 psia) = 0 for every fuel class. Text uses "not documented in PSI", never "not measured" |

### S6 Copilot
| Item | Requirement |
|---|---|
| Purpose / user | Grounded Q&A over the evidence base |
| Data / API | `POST /api/ask`, `/api/evidence/{id}` |
| Visuals | Question box + 6 suggested questions. Answer sections: Evidence / Literature / Interpretation / Limitations / Gaps. Citation chips open the evidence drawer. A "cached answer" or "evidence-only" badge when applicable |
| States | Progress indicator up to 45 s. `503` / `504` → fallback content plus the reason. `insufficient_evidence` → shows what was searched |
| Acceptance | Validation set passes the thresholds in §3. No crash with the API key unset. No uncited claim is ever displayed |

---

## 2. Backend requirements
| Gate | Criterion |
|---|---|
| DB build | `python3 -I scripts/load_db.py` passes all FINAL_DATA_CONTRACT §8 rules; two consecutive builds give identical table checksums |
| Endpoints | Every route in FINAL_API_CONTRACT returns schema-valid JSON (pytest + `schemathesis` or Pydantic round-trip); unknown IDs → 404 `ApiError`; invalid ranges → 400 |
| Performance | Non-LLM endpoints P95 < 150 ms on a laptop |
| Secrets | `ANTHROPIC_API_KEY` read only by the backend from the environment; absent from the repo, the frontend bundle, logs and API responses (`grep` check in CI) |

---

## 3. Scientific and AI gates (automated, `tests/test_science.py`, `tests/test_copilot.py`)
| Gate | Expected |
|---|---|
| Counts | 2,007 condition records; 1,386 unique tests; 264 solid tests; 0 solids with pressure; solid O₂ max 22.2%; 0 partial-g |
| Envelopes (ambient) | exploration 0; Moon-base 20 (all PSI-159); FM2 point 10; bracket 27 (CFI-G 10 + FLEX 17) |
| CFI-G | cool flame yes = 7 (all "30% butane", X_O₂ 0.385–0.399, 2.0266 bar); no = 1; not recorded = 171; "pentane" in 0 rows |
| Relations | DAFT → SAME `qualified_instrument_for` (verified); FLEX ↔ CFI `shares_test_number_series` (inferred) |
| Semantics | missing ≠ 0 (no NULL → 0 coercion anywhere); inverse rows have `o2_context = burner_stream`; duplicates excluded from counts |
| Copilot (35-item `validation.jsonl`, Batch API) | retrieval recall@5 ≥ 0.8; citation validity 1.0 (validator); numeric grounding ≥ 0.95; `must_not_contain` violations 0; unsupported questions (partial-g prediction, fire risk) → refusal or insufficient-evidence |

---

## 4. Frontend tests (Playwright smoke, ~10 tests)
| Area | Test |
|---|---|
| Navigation | all 6 routes render |
| Filtering | fuel_class = solid shows 5 investigations |
| Comparison | select BASS + Saffire-III |
| Empty states | the gap-map zero cell |
| Offline | backend stopped → error card, no crash; LLM disabled → 5 screens fully functional |
| Responsive | 1280 px and 768 px layouts |
| Accessibility | status shown by shape + text (not colour alone); keyboard navigation of tables |

---

## 5. Definition of done (P0)
- All gates in §2–§4 are green in CI.
- The deployed URL passes the smoke test from a private browser window.
- The submission page is complete in English, with:
  - a public demo link
  - the NASA data used: the PSI records and tables, with DOIs
  - references
  - the SI-use description (code and data acknowledged as SI-assisted where applicable)

---

## 6. Demo (per the official Submission Guide)
- **Format: 7-slide deck (recommended) or a video of ≤ 30 seconds**, in English, at a public link with no login.
- **Deck outline:**
  1. Title
  2. Problem: habitat atmospheres and NASA's scattered evidence
  3. What FIREWISE does: 6 screens, with evidence statuses
  4. Key finding: **0** PSI tests in the 30–36% O₂ / 8.2–10.2 psia envelope; 0 solids with documented pressure;
     0 partial-g
  5. Copilot answer with citations (CFI-G cool flames)
  6. Data honesty: 475 flags, duplicates, inverse-flame semantics
  7. Next steps: FM2 / LUCI data; links
- No NASA logos or insignia in SI-generated media; any SI-generated image carries a visible watermark.
