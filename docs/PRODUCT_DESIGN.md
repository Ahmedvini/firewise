# FIREWISE — Product Design

> **Readiness audit 2026-11-13:** P0 has **6 screens** (the Run Table is a tab of Investigation detail); "Scenario Ranker" is renamed **Scenario Explorer**; acceptance criteria are in `P0_ACCEPTANCE_CRITERIA.md`. See `FINAL_READINESS_AUDIT.md` and `CHANGELOG.md`.

**Product promise:** *"Ask a fire-safety question about a crewed habitat. FIREWISE shows which NASA experiments
actually tested those conditions, how the tests differed, what was measured, and exactly what nobody has tested
yet, with every number linked to its NASA source."*

**Users:** combustion scientists, spacecraft fire-safety engineers, professors and students.

**Shared need:** they need to find comparable tests fast and to know how much to trust each value.

---

## 1. Modules (P0 = build in the 48 h; P1 = if time allows; P2 = roadmap slide)

| Module | Priority | What it shows | Built on |
|---|---|---|---|
| **Mission Control** (home) | P0 | 24 investigations · 2,007 runs · fuel-class bar chart · O₂ × P scatter of every documented run, coloured by fuel class · partial-g "0 runs" tile · data-class (A–E) counts | `coverage_summary.json`, `runs` |
| **Scenario Ranker** | P0 | Choose ISS / Exploration 34%·8.2 psia / Moon base / Mars / custom sliders. Get a ranked list with **stacked score bars** (c₁…c₆) and a gravity badge ("bracketing only") | `/rank` |
| **Investigation Explorer** | P0 | Search and filter (fuel class, facility, O₂/P range, data class). Card: objective (verbatim), tested ranges with status chips, data products, publications, quality flags, local files | `/investigations` |
| **Run Table ("how tests differed")** | P0 | Per-investigation sortable table: changed variables highlighted, constant ones collapsed, flags inline, "view source row" | `/runs` |
| **Comparison Studio** | P0 | 2–4 investigations side by side: shared / different / missing, per-feature similarity bars, incompatibility warnings, overlaid O₂–P ranges | `/compare` |
| **Evidence Gap Map** | P0 | Heatmap of gravity × fuel class × O₂ band × P band. Click a cell to see its runs or "0 documented runs". Literature-only overlays (LUCI, FM2) drawn dashed | `/gaps` |
| **Research Copilot** | P0 | Grounded Q&A. Answers split into Evidence / Literature / Interpretation / Limitations / Gaps; each claim has clickable citations; follow-up questions | `/ask` |
| Relationship Graph | P1 | Cytoscape view: facility → insert → investigation → diagnostic; paths explain links (DAFT→SAME, FLEX→CFI) | `/graph` |
| Raw-data Showcase | P1 | CFI-G test 21265C3: 10 decoded frames + its PSI-table conditions; Saffire-III calibration grid | static assets |
| FLEX outcome explorer | P1 | Extinction / disruption / completion by O₂, P, diluent; optional transparent classifier with applicability domain | `/flex` |
| Scenario explorer with sliders and evidence tiers | P2 | Free O₂/P/flow/g input → nearest documented runs + tier badges | — |

---

## 2. Evidence-tier visual language (used everywhere)
| Tier | Badge | Meaning |
|---|---|---|
| Measured | solid green ● | value measured in a NASA flight test (PSI table) |
| Derived / Reported | half-filled ◐ | computed or reported by PSI (e.g., Saffire-II O₂ from CO₂) |
| Specified | outline ○ | set-point or design envelope (FLEX-2 ranges) |
| Literature | book icon | peer-reviewed or NASA report, outside PSI tables |
| Interpretation | italic grey | FIREWISE or LLM reasoning, never a result |
| Not documented | dashed grey "—" | absent from the PSI table; **not** "not measured" |

The scenario explorer must label each condition as supported by flight evidence, literature-only, hypothetical,
or unsupported extrapolation. **No "risk score" anywhere.**

---

## 3. Core user journeys

**J1. Fire-safety engineer, lunar habitat (the demo journey)**
1. Selects the Scenario "Exploration envelope (30–36% O₂, 8.2–10.2 psia)", then "Moon base (challenge definition)".
2. The ranked list shows CFI-G, FLEX, Flame Design and BRE high on atmosphere match. BASS/BASS-II and Saffire
   rank high on material relevance but low on match. A banner reads "No documented runs of real solids above 23%
   O₂ or with documented pressure."
3. Clicks Gap Map: the solid × 30–36% × 0.5–0.75 atm cell shows **0**. LUCI (2025) and FM2 (planned) appear as
   literature overlays.
4. Asks Copilot: "What do we know about solid flammability at 34% O₂ and 8.2 psia?" The answer separates BRE
   emulator evidence (measured O₂, pressure not documented), the Saffire-II µg/1g contrast at 22%, and the FM2
   plan, with citations, and ends with the open questions.

**J2. Graduate student comparing methodology**
- Comparison Studio: BASS vs Saffire-III. Shared: solid fabric (SIBAL), forced flow, two cameras. Different:
  MSG small duct vs Cygnus 94 × 40.6 cm, flow up to 40 vs 30 cm/s, O₂ not documented vs reported. Warning:
  BASS-II flow in fan units.

**J3. Combustion scientist validating a claim**
- Copilot: "Under what conditions were cool flames seen in CFI-G?" The answer comes from the PSI table: 7 tests,
  30% n-butane, X_O₂ ≈ 0.39, ≈2 bar. It is cross-checked against Kim et al. 2023 and notes that 171 rows are
  unrecorded.

**J4. Professor preparing a lecture**
- Investigation Explorer, filtered to "liquid droplet". Opens FLEX's run table and shows students how
  outcomes shift with O₂ and diluent.

---

## 4. Layout and interaction rules
- Desktop-first, responsive to tablet. Left navigation: Mission Control · Scenarios · Explorer · Compare ·
  Gaps · Copilot.
- Every number is hoverable, showing status, source file and row/page, with a link to the PSI DOI or URL.
- Accessibility: tier badges use shape + colour (colour-blind safe), keyboard-navigable tables, WCAG AA contrast.
- Performance: all P0 views read precomputed JSON or SQLite. Under 300 ms except Copilot (streamed).

---

## 5. Demo script (SUPERSEDED: the official format is 7 slides or a video of ≤ 30 s; see P0_ACCEPTANCE_CRITERIA §6)
| t | Screen | Line |
|---|---|---|
| 0:00 | Mission Control | "NASA's PSI holds 24 combustion investigations. We normalized 2,007 condition records (1,386 unique tests) from NASA's own tables, with 475 data-quality issues surfaced, not hidden." |
| 0:25 | Scenario Explorer: exploration envelope | "For a 30–36% O₂, 8.2–10.2 psia habitat atmosphere, NASA's PSI documents zero tests; here is the nearest evidence, and *why*." |
| 0:55 | Gap Map | "And here's what doesn't exist: not one solid-material run at elevated O₂ or with documented pressure. Zero partial-gravity runs. LUCI and FM2 are the first steps." |
| 1:25 | Comparison Studio: BASS vs Saffire-III | "Same question, different scales. FIREWISE shows what is comparable and what isn't." |
| 1:55 | Copilot: cool-flame question | "Every claim is cited to a NASA table row or document. It even catches that CFI-G's objective listed pentane, yet none of its 333 documented tests used pentane." |
| 2:30 | Local raw data | "Our downloaded raw frames? FIREWISE identified them: test 21265C3, a 2-second inverse butane flame at 3.3 bar." |
| 2:50 | Close | "FIREWISE: evidence, not guesses, for the fire-safety decisions of lunar habitats." |
