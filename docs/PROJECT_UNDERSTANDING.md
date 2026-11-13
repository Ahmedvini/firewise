# FIREWISE — Project Understanding

> **Readiness audit 2026-11-13:** Counts reworded (condition records vs unique tests; 19 flight investigations). See `FINAL_READINESS_AUDIT.md` and `CHANGELOG.md`.

---

## 1. Challenge (verified, 2026-11-13)
**NASA Space Apps 2026, "Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data."**
URL: https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/
Hackathon: **Nov 14–15, 2026**.

> *"Your challenge is to build an SI-powered, web-based dashboard that **summarizes, ranks, and interprets**
> combustion science investigations to deliver critical foundational insights for fire safety."*

The challenge asks teams to summarize:
- objectives
- fuels, with sample or burner shape and size
- O₂ and airflow
- **how tests within one investigation differed**
- sensors and measurements

Relevance targets are spacecraft, stations, lunar and Martian bases, and pressurized rovers.

It also states:
- "there is currently no partial-gravity combustion data available in PSI"
- LUCI and FM2 will add such data in the future
- "µg and 1g results could bound" intermediate gravity
- rockets and propellants are out of scope

---

## 2. The scientific problem
- **Buoyancy is removed in microgravity.** That changes how air reaches a flame, how heat and smoke leave it,
  and therefore flame shape, spread, extinction limits and smoke particle size.
- **Exploration habitats will run oxygen-enriched, reduced-pressure atmospheres** (≥30% O₂ at ≤10.2 psi; 34% at
  8.2 psia) in partial gravity (0.16 g Moon, 0.38 g Mars). These are conditions for which the evidence base is
  thin.
- **NASA's PSI repository holds 24 combustion investigations** spanning gas flames, droplets, solids and smoke.
  The data is scattered across heterogeneous records, spreadsheets and terabytes of raw files.

---

## 3. What we found (shapes the product)
1. Our local downloads (7 files) contain no measurements, only showcase raw data.
2. **PSI's open JSON API and per-investigation "experimental tables"** let us build a normalized,
   provenance-tracked evidence base: **2,007 condition records (1,386 unique individual tests) from 19 flight
   investigations, with 475 quality flags surfaced.**
3. **The evidence is strong for gas flames and droplets at elevated O₂ and reduced pressure. It is
   absent for real solid materials** (0 of 264 solid tests document pressure; documented O₂ ≤ 22.2%) and absent for
   partial gravity (0 runs).
4. Several brief assumptions were wrong or unverifiable:
   - SAME and DAFT: DAFT qualified the P-Trak *for* SAME, not the reverse.
   - CFI-G tested ethane, propane and butane, not pentane.
   - Some investigations list no downloadable data at all.

---

## 4. Target users and their jobs
| User | Job to be done |
|---|---|
| Spacecraft fire-safety engineer | "What tested evidence exists for my habitat atmosphere, and where are the holes?" |
| Combustion scientist | "Which experiments are comparable to mine, and under exactly which conditions?" |
| Professor / student | "How did NASA design these experiments, and what did they vary?" |
| Mission planner (secondary) | "What should the next flight experiment test?" |

---

## 5. Product vision
**FIREWISE is an evidence-graded, habitat-aware intelligence layer over NASA PSI combustion data.**
- **Summarize:** every investigation as a structured card. Verbatim NASA text, *tested* ranges with
  measured/specified/derived status, data products, publications, data-quality flags.
- **Rank:** investigations by transparent, decomposed relevance to a chosen habitat scenario (ISS, exploration
  atmosphere, Moon base, Mars, rover).
- **Interpret:**
  - side-by-side comparison of conditions and hardware
  - an evidence gap map
  - a research copilot whose every claim cites a NASA table row, record field, report page or labelled
    literature
- **Not:** a chatbot, a fire-risk predictor, or a partial-gravity simulator.

---

## 6. Challenge alignment
| Challenge asks | FIREWISE answer |
|---|---|
| Summarize objectives, fuels, geometry, O₂, airflow, sensors | Investigation cards and run tables (P0) |
| How tests in the same investigation differed | Run table with changed-variable highlighting (P0) |
| Rank by relevance to crew habitats | Scenario Ranker with decomposed scores (P0) |
| Interpret for fire safety | Comparison Studio, Gap Map, grounded Copilot (P0) |
| Support predictive modeling | normalized, provenance-tracked run table export; FLEX outcome explorer (P1); honest feasibility statement |
| Inform next-generation controls and equipment | smoke-detection lineage (DAFT→SAME→SAME-R), suppression evidence (FLEX CO₂/He), gap priorities |
| Partial-gravity gap | Gap Map plus bracketing with Saffire-II µg/1g; LUCI and FM2 shown as literature-only |
