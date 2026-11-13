# FIREWISE — Executive Summary

> **Readiness audit 2026-11-13:** The exploration-atmosphere headline is corrected from "35 runs" to **0**. See `FINAL_READINESS_AUDIT.md` and `CHANGELOG.md`.

**Challenge:** NASA Space Apps 2026, *Flame in Freefall* (Nov 14–15).
**Team:** 2–3 people, 48 hours.

---

## The strongest product direction
**An evidence-graded, habitat-aware ranking and comparison dashboard over NASA's 24 PSI combustion
investigations.**

It answers the challenge's three verbs with provenance on every number:
- **Summarize:** investigation cards and "how tests differed" run tables.
- **Rank:** transparent relevance to ISS, exploration-atmosphere, Moon-base and Mars scenarios.
- **Interpret:** side-by-side comparison, an evidence gap map, and a copilot that must cite NASA rows and pages.

---

## What makes it different (already built, not promised)
1. **Run-level evidence, not documents.**
   - We harvested all 24 PSI records through the open API.
   - We normalized 22 NASA experimental tables into **2,007 condition records (1,386 unique individual tests) from
     19 flight investigations**. Each has O₂, pressure and flow plus its *status* (measured, derived, reported,
     set-point, not documented) and its exact source row.
2. **Visible data honesty.**
   - **475 data-quality issues** are flagged instead of silently fixed: percent-format artifacts (`3400%`),
     auto-incremented fuel names (`CH5…CH14`), encoding loss (`µ-g` → `?-g`), duplicate rows, and records
     claiming terabytes with no files listed.
3. **A real, quantitative gap finding that matters for lunar habitats:**
   - **No PSI test documents the exploration envelope (30–36% ambient O₂ at 8.2–10.2 psia): 0 runs.** The nearest
     evidence brackets it: 10 CFI-G gas flames at ≈7.35 psia and 17 FLEX droplets at 10.3–10.5 psia. Under the
     challenge's Moon-base definition (≥30% O₂, ≤10.2 psi) there are 20 runs, all CFI-G gas flames.
   - **0 of 264 real solid-material tests document chamber pressure.** The 140 that document O₂ reach at most 22.2%.
   - **0 partial-gravity runs.**
   - This is exactly what FM2 (34% / 8.2 psia, CLPS) and LUCI target, and FIREWISE shows it in one click.
4. **It corrects the record.**
   - CFI-G's objective lists pentane, but none of its 333 documented tests uses pentane (the paper confirms the
     tested fuels).
   - Cool flames are marked in exactly **7 tests**, all "30% butane" (n-butane per the paper) at X_O₂ ≈ 0.39 and
     ≈2 bar, matching the published paper.
   - DAFT qualified the P-Trak *for* SAME, the reverse of the common assumption.
   - CFI's tests are numbered in a "Flex Number" series (1206–1387) on the same MDCA hardware as FLEX.
5. **It identifies its own raw data.**
   - Our 415 MB ACME download is CFI-G test 21265C3: a 2-second inverse butane flame at 3.3 bar that
     self-extinguished.
   - The Saffire-II frames are a pre-test flow-visualization record, not a fire.

---

## What we can realistically build in 48 h (P0)
- Mission Control
- Scenario Ranker
- Investigation Explorer with run tables
- Comparison Studio
- Evidence Gap Map
- Research Copilot: Claude, structured output, server-validated citations, cached fallback

**Stack:** SQLite + FastAPI + Next.js/Plotly; every core screen works with the LLM switched off.
**P1 if time allows:** relationship graph, FLEX outcome explorer, decoded ACME frame showcase.
**Explicitly not built:** fire-risk scores, partial-gravity predictions, trained models.

---

## The demo for judges (official format: 7 slides or a video of ≤ 30 s; see P0_ACCEPTANCE_CRITERIA §6)
1. Pick the exploration envelope (30–36% O₂, 8.2–10.2 psia), then the challenge's Moon-base definition.
2. FIREWISE ranks the evidence and shows *why*, component by component.
3. The Gap Map shows **zero runs of any kind** in that envelope, zero solids with documented pressure and zero partial-g data, with LUCI and FM2
   as the first steps.
4. Comparing BASS and Saffire-III shows what is comparable across scales and what isn't.
5. The Copilot answers a cool-flame question with citations to NASA table rows and flags the
   proposal-vs-flight discrepancy.
6. Close: our own raw download, identified and conditioned from NASA's tables.

**Why it is scientifically meaningful:** it turns 24 heterogeneous NASA investigations into a single,
auditable answer to "what do we actually know about fires in the atmospheres we plan to live in, and what must
be tested next?"

---

## Open decisions for the team
- Confirm the Space Apps 2026 rules on pre-event preparation (data pipeline and docs are done; app code starts
  at kickoff).
- 2 or 3 people (the roadmap has both allocations).
- Anthropic API key for the Copilot (`ANTHROPIC_API_KEY` on the API host).
