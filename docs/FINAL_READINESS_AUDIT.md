# FIREWISE — Final Readiness Audit

*Audit date: 2026-11-13, ~19:30 EET (kickoff: Sat 2026-11-14 09:00 local).*

**Method:** inspected the repository, scripts, derived data, PSI sources, environment, running processes and the
official Space Apps rules. All quantitative statements below are reproducible with:

```bash
python3 -I scripts/verify_claims.py .
```

That command writes `derived/claims_check.json`. Read it as the source of truth over any prose document.

---

## 1. Verdict

| Dimension | Status | Summary |
|---|---|---|
| **Eligibility** | 🔴 **BLOCKED pending written clarification** | The official FAQ says *"Teams are not allowed to begin working on the challenges prior to the hackathon."* Most existing artifacts are challenge-specific work done before kickoff (§3) |
| **Scientific claims** | 🟠 **Corrected in this audit** | The headline lunar-atmosphere claim ("35 runs inside 30–36% O₂ / 8.2–10.2 psia") was wrong; the correct value is **0**. Six other claims were overstated or imprecise. All are now fixed in docs, facts and the validation set |
| **Data / technical** | 🟠 **Ready after D0 (~1.5 h)** | Run IDs are not unique (10 IDs, 20 rows). 20 flags are orphaned. O₂ context (ambient vs burner stream), row granularity and the gravity field must be added before `load_db.py` |
| **Architecture** | 🟢 **Approved with changes** (§6) | SQLite + FastAPI + Next.js stands. Changes: ranking method, non-streamed validated Copilot, a unified API contract, 6 screens |
| **Environment** | 🟠 | No git repo, no `.gitignore`, no tests, no venv; FastAPI, anthropic, pydantic and pytest are not installed; `ANTHROPIC_API_KEY` is not set (expected; set it on the backend host only) |

**Technical readiness is conditional on D0 + environment setup.** Whether the existing artifacts can be used at all
is a separate question: an **eligibility** decision that only the organizers can make (see `OPEN_DECISIONS.md` D1, D2).

---

## 2. What actually exists (verified state, not the docs' description)
| Item | Actual state |
|---|---|
| `Data/` (7 files, 460 MB) | sha256 baseline verified: `OK: 7 files unchanged` |
| PSI records | 24/24 in `sources/psi_api/` (PSI-23 imported from a `curl --compressed` fetch; manifest row records this) |
| Experimental tables | 22 CSV / 20 investigations in `sources/psi_files/*/Experimental table/` |
| Scripts | `harvest_psi`, `inventory_psi`, `inventory_local`, `fetch_psi_files`, `build_runs`, `coverage`, `build_records`, `checksum_data`, **`verify_claims` (added by this audit)** |
| `derived/runs.csv` | 2,019 rows = 2,007 combustion/aerosol condition records + 4 Saffire flow-visualization rows + 8 PSI-142 figure-reference rows |
| `derived/runs_flags.csv` | 475 flags. **20 reference run IDs that no longer exist** (BRE rows renamed when split by O₂ level) |
| Curated facts / validation set | 23 facts / 35 items (corrected and extended by this audit; previous versions kept in `derived/_superseded/`) |
| Database | **none yet** (`load_db.py` not written) |
| Tests | **none** (`tests/` absent) |
| Git | **not a repository**; no `.gitignore`, no `.env` |
| Literature PDFs | **`sources/papers/` is empty**. Literature facts are URL-only |
| Background downloads | 3 jobs running since ~18:40, **not terminated**. Documents 144/478; raw telemetry 2,229/7,259 (≈4 files/min, will not finish by kickoff); s-Flame 1,434/1,837; 22 `.part` files in flight |

---

## 3. Eligibility: separate from technical readiness

**Verified rules (fetched 2026-11-13):**

| Source | Rule |
|---|---|
| Participant FAQ (dated Nov 13, 2026) | *"Resources for each challenge will be published on November 13. **Teams are not allowed to begin working on the challenges prior to the hackathon.**"* |
| Project Submission Guide | *"SI should not be used to (come up with your idea of how to solve the challenge)."*<br>*"Code and data: Must acknowledge SI generation in descriptive text and metadata."*<br>Teams must tick **"Confirm All Work is Original"** |
| Judging & Awards Guide | Attestation: *"…the submitted project represents my team's original work and that all external resources including code, text and images … are listed in the References field…"* |
| Participant Terms (updated Aug 7, 2026) | Event starts Nov 14. Original content must be open-source (Apache-2.0 by default); third-party materials must be publicly available |
| Demo format | **7-slide deck or a video of ≤ 30 seconds**. The existing docs planned a 3-minute demo (corrected) |

**Classification of existing work:**

| Artifact | Nature | Eligibility exposure |
|---|---|---|
| Reading NASA PSI pages and literature; general domain knowledge | preparation / learning | Low (judgement call) |
| `scripts/*.py`, `derived/*`, `sources/*` harvest | **challenge-specific implementation** | **High**: work on the challenge before kickoff |
| `docs/*` (product, architecture, findings) | **challenge-specific design** | **High**; product direction also refined with an SI assistant (see the SI-idea rule) |
| Background downloads still running | challenge-specific data acquisition | **High while running before kickoff** |

**Recommendation (no concealment, no back-dating):**
1. **Tonight, disclose in writing** to your Local Lead (or the Global Organizing team via the Contact page).
   Say what was done, when, and with which SI tools, and ask whether any of it may be used.
2. **Follow the written ruling.**
3. **If no ruling arrives by kickoff,** do not submit pre-event artifacts as hackathon work. Rebuild the implementation
   during the event, and state the pre-event research and SI use plainly in the submission's SI and References
   fields. **Do not tick "Confirm All Work is Original" for anything it does not truthfully cover.**
4. **Whether to stop the running downloads** is your decision. They are still challenge-specific work happening
   before kickoff. I have not terminated them.

---

## 4. Consistency and correctness findings
Severity:
- **Critical** — before implementation
- **High** — during initial implementation
- **Medium** — before final integration
- **Low** — optional

| # | Issue | Docs / artifacts affected | Actual source of truth (verified) | Root cause | Sev. | Resolution |
|---|---|---|---|---|---|---|
| C1 | Pre-event work vs. FAQ rule | all artifacts | FAQ text above | Work began before kickoff | **Critical** | Organizer ruling (OPEN_DECISIONS D1) |
| C2 | SI used in shaping the solution idea | docs | Submission Guide SI rule | Planning sessions with an SI assistant | **Critical** | Disclose; organizer ruling (D2) |
| C3 | "35 runs in 30–36% O₂ / 8.2–10.2 psia" | EXECUTIVE_SUMMARY, DATASET_AUDIT, RISKS, curated F18, validation V02, `coverage.py`, plan, memory | `claims_check.json`: **0** runs (ambient O₂); Moon-base definition (≥30%, ≤10.2 psia) **20** runs, all CFI-G at ≈7.35 psia; bracket 27 (CFI-G 10 + FLEX 17) | (a) pressure band 0.5–0.75 atm mislabeled as 8.2–10.2 psia (true span 7.35–11.0 psia); (b) 8 inverse-flame rows counted, whose O₂ is the burner stream, not the atmosphere | **Critical** | Docs, facts and validation corrected (CHANGELOG); `coverage.py` label + ambient filter in D0 |
| C4 | Non-unique `run_id` | `runs.csv`, DATA_ARCHITECTURE PK | 10 IDs / 20 rows: CFI ×8, E-FIELD ×1 (exact duplicate rows in NASA tables), SAME-R #57 (one test number, two materials) | IDs built from test labels, which are not unique in the source | **Critical** | Canonical `row_key` from source location; keep `test_label` non-unique (FINAL_DATA_CONTRACT) |
| C5 | 20 orphan flags | `runs_flags.csv` | BRE flags reference pre-split IDs | Flags emitted before the O₂-level split | **Critical** (FK) | D0: flags keyed by `row_key` after the split |
| C6 | "2,007 test runs across 20 investigations" | EXECUTIVE_SUMMARY, PROJECT_UNDERSTANDING, PRODUCT_DESIGN, DATASET_AUDIT | 2,007 **condition records** from **19** flight investigations: 1,394 individual-test rows (**1,386 unique**), 469 SPICE test points (151 ignitions), 114 test-day rows, 12 test-date, 8 envelopes, 8 material sets, 2 sessions | Mixed table granularity, never modelled; PSI-142 counted as an investigation with runs | **Critical** (headline wording) | Wording corrected; `row_granularity` field in D0 |
| C7 | O₂ field mixes ambient and burner-stream meanings | `runs.csv`, ranking, gap map | 274 inverse-flame rows (Flame Design 120, CFI-G 154) | One `o2` field for two physical quantities | **Critical** for ranking | `o2_context` ∈ {ambient, burner_stream, envelope}; habitat matching uses ambient only |
| C8 | 3-minute demo | PRODUCT_DESIGN, EXECUTIVE_SUMMARY, ROADMAP | Submission Guide: 7 slides or ≤ 30 s video | Written before the guide was read | **Critical** (submission) | Demo re-planned (P0_ACCEPTANCE_CRITERIA §7) |
| H1 | Undetected duplicate rows | `build_runs.py` | CFI 87 rows → 79 unique; E-FIELD 1 | Duplicate check existed only for SPICE | High | D0: generic duplicate flag; docs corrected |
| H2 | Status vocabulary differs (data `specified`/`missing` vs product "Set-point"/"Not documented"; docs mention `inferred`) | DATA_ARCH, PRODUCT_DESIGN | `runs.csv` uses measured / derived / reported / specified / missing | Two naming layers | High | Canonical enum + display map (DATA_CONTRACT §3) |
| H3 | Gravity is free text that mixes regime and platform | `runs.csv` | 4 distinct strings, all microgravity | — | High | `gravity_regime` + `platform` fields |
| H4 | Data class A–E exists only in prose | DATASET_AUDIT | — | Never made machine-readable | High | `investigation_meta.json` (D0) |
| H5 | "Moon base" conflated with 34% / 8.2 psia | EXECUTIVE_SUMMARY, PRODUCT_DESIGN | Challenge: ≥30% O₂ at ≤10.2 psi; FM2 / exploration: 34% / 8.2 psia | — | High | Scenarios defined separately (DATA_CONTRACT §7) |
| H6 | Weighted composite rank with subjective weights; µg evidence could look like a lunar "match" | AI_ARCH §6 | — | Design | High | Lexicographic evidence-count ranking; gravity is a hard, visible "0 matching" dimension (API_CONTRACT `/scenarios`) |
| H7 | API path drift (`/runs` vs `/api/investigations/{id}/runs`, `/flex`); no distributions endpoint | ROADMAP, TECH_ARCH, PRODUCT_DESIGN | — | Docs written in parallel | High | FINAL_API_CONTRACT supersedes |
| H8 | 7 P0 modules vs 6 pages | PRODUCT_DESIGN vs TECH_ARCH | — | Run Table listed separately | High | **6 screens**; Run Table is a tab of the Investigation detail |
| H9 | Copilot "streamed" but validated before display | TECH_ARCH, AI_ARCH | — | Contradiction: claims cannot stream before validation | High | Non-streamed validated JSON for P0 (API_CONTRACT `/ask`) |
| H10 | False example number in AI_ARCHITECTURE ("17 methanol/N₂ tests at 0.7 atm … all extinction") | AI_ARCHITECTURE | 3 tests, mixed outcomes | Illustrative text written as fact | High | Replaced |
| H11 | "Pentane never flown" | EXECUTIVE_SUMMARY, PRODUCT_DESIGN | Pentane absent from 333 PSI test rows; "never flown" relies on a publication | Overstatement | High | Reworded |
| H12 | "CFI continued FLEX's numbering" | SCIENTIFIC_ANALYSIS, facts | CFI "Flex Number" 1206–1387; FLEX 1–274; 275–1205 undocumented | Inference stated as fact | High | Reworded (F11, V08) |
| H13 | "n-butane" vs table "butane" | several | PSI table says "30% butane" | Publication term | Medium | Show table term; publication term as [Lit] |
| M1 | Literature not archived locally | AI_ARCH | `sources/papers/` empty | Planned step skipped | Medium | Copilot cites `[Lit]` by URL and labels it "not verified offline" |
| M2 | FLEX "burning rate; mm" unit; SAME-R `Rt/R0` meaning | SCIENTIFIC_ANALYSIS | Unverified | — | Medium | Display raw header; no unit conversion |
| M3 | Downloads incomplete, `.part` files present | — | 22 in flight | Server slow | Medium | P0 does not depend on them; D2 uses completed reports only |
| M4 | O₂ "documented" counts include burner stream | SCIENTIFIC_ANALYSIS | 1,219 rows have O₂; **956** are ambient | C7 | Medium | Reworded |
| L1 | Docs restate numbers in many places | all | `claims_check.json` | No single generated source | Low | The app reads numbers from the DB; docs point to `claims_check.json` |

---

## 5. Scientific claim-validation matrix

**Validation status key:**
- **V-D** — verified directly against PSI tables or records (reproducible)
- **V-P** — published conclusion (literature; URL)
- **INF** — inference
- **COR** — corrected by this audit

| Claim (as it may appear in FIREWISE) | Investigation(s) | Supporting rows / population | Source evidence | Kind | Status |
|---|---|---|---|---|---|
| No PSI run documents ambient O₂ 30–36% together with 8.2–10.2 psia | all 19 flight | 0 of 1,733 non-inverse condition records | `claims_check.ambient_A…` | derived statistic over direct evidence | **COR** (was 35) |
| Under the challenge Moon-base definition (≥30% O₂, ≤10.2 psia): 20 runs, all CFI-G normal gas flames at ≈7.35 psia | PSI-159 | 20 test rows; O₂ measured, P "approx" (reported) | CFI-G Normal table | derived statistic | **V-D** |
| Nearest evidence brackets the envelope: 17 FLEX droplets at 10.33–10.50 psia (measured) and 10 CFI-G at ≈7.35 psia | PSI-69, PSI-159 | 27 test rows | `ambient_D…` | derived statistic | **V-D** |
| 0 of 264 solid-material tests document chamber pressure; 140 document O₂ (max 22.2%), 124 document none | PSI-25, 26, 98, 99, 100 | 264 test rows | `solid_*` | derived statistic | **V-D** (wording COR: "none exceeds 23%" applies only to the 140 with O₂) |
| BRE (gas burner emulating solids) ran at 21, 25, 26.5, 34, 40% O₂; pressure not identified | PSI-20 | 43 rows (18 test days) | BRE table + note | direct (set-points) | **V-D** |
| 0 partial-gravity runs in PSI | all | 2,007 records | `partial_gravity_rows` | derived statistic | **V-D** |
| LUCI flew on NS-29 (2025-02-04), lunar g > 25 s; FM2 planned at 34% / 8.2 psia | external | — | NTRS 20250010653, 20240015307 | published | **V-P** (URL only, not archived) |
| CFI-G cool flames: 7 tests, all "30% butane", X_O₂ 0.385–0.399, approx p 2.0266 bar; 1 "no"; 171 blank | PSI-159 | 179 normal-flame rows | table column `Cool flame?` | direct | **V-D** |
| Agrees with Kim et al., PCI 39 (2023) | PSI-159 | — | DRUM UMD item | published | **V-P** |
| Pentane is in the CFI-G objective but in none of the 333 test rows | PSI-159 | 333 rows | objective text + tables | direct | **V-D**; "never flown" = **INF** |
| DAFT/DAFT-2 (2005) qualified a modified P-Trak (vs. DustTrak, Arizona Road Dust) to de-risk SAME | PSI-47, PSI-102 | 2 sessions | PSI-47 objective + table | direct | **V-D** |
| CFI test IDs are a "Flex Number" series (1206–1387); FLEX tests 1–274 | PSI-39, PSI-69 | 87 / 274 rows | tables | direct | **V-D**; "continued the series" = **INF** |
| Local `PSI-159…21265C3` = inverse butane flame, burner X_O₂ 0.50, approx 3.31 bar, ~2 s, self-extinguished | PSI-159 | 1 row | inverse table, row "21265 C3"; name and size match | direct | **V-D** |
| Saffire-II F1C1 frames are pre-test flow visualization | PSI-99 | table row `F1C1/F1C2` | PSI-99 table; local file not in any PSI listing | direct + **INF** (file identity) | **INF (medium)** |
| Igniter drawings = PSI-23 Engineering Documents | PSI-23 | — | name and byte-size match | direct | **V-D** |
| Saffire-II silicone burned ~0 length in µg but completely in 1g at 20 cm/s, ≈22% O₂ | PSI-99 | 4 rows | table µg/1g columns; O₂ derived from CO₂; 1g configuration not stated | direct + caveat | **V-D** |
| FLEX: all 22 methanol/N₂ tests at ≤15% O₂ ended in extinction | PSI-69 | 22 rows | FLEX table | derived statistic | **V-D** |
| Inverse-flame O₂ values (up to 85%) are not habitat atmospheres | PSI-10, 159 | 274 rows | table semantics | direct | **V-D** (new) |

**Rules enforced in the product:**
- Absence of a value is shown as **"not documented"**, never zero or ambient.
- A value in a test matrix keeps its status (`specified` ≠ `measured`).
- Interpretations are labeled.
- Every number in the UI resolves to `claims_check.json` keys or database rows.

---

## 6. Architecture approval: **APPROVED WITH CHANGES**
1. **Data:**
   - canonical `row_key`
   - `row_granularity`, `o2_context`, `gravity_regime`/`platform`, `test_label` and duplicate flags
   - machine-readable investigation metadata

   (FINAL_DATA_CONTRACT; task D0.)
2. **Ranking:**
   - lexicographic order: documented in-window tests, then near-window, then material match
   - no weighted composite
   - gravity shown as its own dimension, with "0 partial-g evidence" stated explicitly
   - missing pressure never counts as a match
3. **Copilot:**
   - non-streamed; validated before display
   - aggregates computed only by the server (`agg:*` evidence items)
   - model `claude-opus-5-5` (verified against Anthropic's models page, 2026-11-13); effort `medium`; structured
     output; deterministic fallbacks
4. **API:** one contract (FINAL_API_CONTRACT). Typed with Pydantic, exported to TypeScript via OpenAPI.
5. **Screens:** 6 (the Run Table is a tab of Investigation detail).
6. **SQLite + FTS5 is sufficient.** About 2k rows and about 30 MB of text; no other store is justified.

---

## 7. Change log
All modifications made by this audit are listed in `docs/CHANGELOG.md`.
