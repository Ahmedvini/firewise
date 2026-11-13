# FIREWISE — Risks and Validation

> **Readiness audit 2026-11-13:** Validation set extended to 35 items; envelope numbers corrected. See `FINAL_READINESS_AUDIT.md` and `CHANGELOG.md`.

---

## 1. Risk register
| # | Risk | Type | Likelihood / impact | Mitigation | Status |
|---|---|---|---|---|---|
| R1 | Local downloads contain no measurements | data | happened / high | Evidence base rebuilt from the PSI API + experimental tables (2,007 runs) | **mitigated** |
| R2 | PSI tables are *summaries*: absence ≠ not measured (BRE pressure, BASS O₂) | scientific | certain / high | "Not documented in PSI table" wording; `missing` status; never imputed | designed |
| R3 | Spreadsheet artifacts (3400%, CH5…CH14, N3…N6, `?-g`, `�`, duplicates, 0 mmHg) | data | certain / medium | 475 flags, raw row preserved, corrections only where chemically unambiguous | **mitigated** |
| R4 | Proposal conditions mistaken for tested ones (CFI-G pentane, FLEX-2 envelopes) | scientific | likely / high | Record text tagged as objective; tested ranges come only from tables; validation items V12 and V24 | designed |
| R5 | Similarity read as scientific equivalence | scientific | likely / medium | per-feature breakdown, "compared on k/n features", incompatibility flags | designed |
| R6 | Scores read as fire risk | scientific / ethical | likely / high | "Evidence relevance" label, decomposed bars, no risk numbers anywhere | designed |
| R7 | Partial-g over-claim | scientific | likely / high | Gap map shows 0; bracketing only; V01 and V27 enforce it | designed |
| R8 | LLM hallucination or wrong citation | AI | possible / high | evidence-ID validator, number cross-check, cached validated demo answers | P0 build |
| R9 | PSI server slow or truncating | technical | happened / medium | everything pre-harvested; gzip/curl fallback; resumable downloader | **mitigated** |
| R10 | HOBJ decode wrong (misleading imagery) | technical | possible / low | time-boxed P1; show only if validated visually against PSI previews | open |
| R11 | Rule conflict on pre-event work | process | unknown / high | verify the Space Apps 2026 rules at kickoff; code starts at kickoff | **open: user action** |
| R12 | Scope creep within 48 h | delivery | likely / high | P0 freeze list; feature freeze Sun 18:00; LLM-free core screens | designed |
| R13 | Literature facts gathered by agents may be imprecise | scientific | possible / medium | tagged `[Lit]` with URL; anything snippet-only marked unverified; spot-check before the demo | open |
| R14 | Prompt injection through PDF text | security | low / medium | retrieved text treated as data; no side-effect tools; validator | designed |

---

## 2. Evaluation plan
### 2a. Data quality (automated, `tests/test_data.py`)
| Check | Target |
|---|---|
| Completeness: every run has `source_file` + `source_row`; every investigation has a record | 100% |
| Unit consistency: O₂ 0–100 %, P > 0 atm, flows in cm/s or flagged | 100% |
| Provenance: every downloaded file has a `sources.csv` row whose sha256 matches | 100% |
| Originals unchanged: `checksum_data.py --verify` | OK |
| **Manual accuracy audit:** 30 random normalized values compared with the source CSV row | ≥ 29/30 exact; 0 fabricated |

### 2b. Retrieval quality
- Run each of the 35 questions in `derived/validation.jsonl` through retrieval only.
- **Recall@5** = share of questions where at least one `must_cite_any` evidence ID is in the top 5. Target **≥ 0.8**.
  Embeddings are added only if this target is missed.
- **Investigation retrieval accuracy:** the correct investigation(s) appear in the evidence pack. Target ≥ 0.9.

### 2c. Answer quality (LLM, run through the Batch API)
| Metric | How | Target |
|---|---|---|
| Citation correctness | every cited ID resolves and supports the claim (validator plus manual check on 10) | ≥ 0.95 |
| Factual agreement | key numbers in the answer match `expected_answer` (scripted match plus human judgement) | ≥ 0.9 |
| Negative constraints | none of `must_not_contain` appears (e.g., "predicts lunar", "SAME instrument was later adapted for DAFT") | 100% |
| Tier discipline | no claim marked `measured` cites a `specified`, `reported` or `literature` item | 100% |

### 2d. Predictive (only if the P1 FLEX classifier is built)
- Grouped K-fold by test day (no leakage between neighbouring tests); macro-F1 vs a majority baseline;
  calibration plot.
- An applicability-domain check that refuses inputs outside FLEX's O₂/P/d₀ hull.
- Reported only as "FLEX droplet outcome patterns", never as fire prediction.

### 2e. Product usability (with 2–3 testers on Sunday morning)
| Task | Target |
|---|---|
| Find FLEX tests at 0.7 atm with helium | < 30 s |
| Compare BASS vs Saffire-III and name 2 differences | < 60 s |
| Find whether solids were tested at 34% O₂ | < 45 s |
| Keyboard-only navigation of the explorer; colour-blind check on tier badges | pass |
| Non-LLM API P95; time to first Copilot token | < 100 ms; < 3 s |

---

## 3. Validation dataset (built: `derived/validation.jsonl`, 35 items after the readiness audit)
**Categories:**

| Category | Items |
|---|---|
| coverage | 4 |
| lineage | 4 |
| hardware | 2 |
| conditions | 8 |
| outcomes | 4 |
| comparison | 3 |
| data | 3 |
| scope | 2 |
| atmospheres | 1 |
| literature | 1 |

Every expected answer was checked against `derived/runs.csv` or a curated fact on 2026-11-13. The counts were
re-computed programmatically: 274 FLEX tests, 7 cool flames, 22 methanol extinctions, 103/161/9 pressure
groups, 0 runs in the exploration envelope (27 bracketing it), and 0 solids with pressure (corrected 2026-11-13).

Each item carries:
- `must_cite_any`: the evidence IDs that should be retrieved
- `must_not_contain`: hallucination traps that encode the brief's own risky assumptions

---

## 4. Scientific trust statement (for the submission)
> FIREWISE reports only what NASA's PSI records and experimental tables document, plus clearly-marked literature.
> Each value shows whether it was measured, derived, reported, specified (set-point) or not documented. The
> platform maps evidence and gaps; it does not predict fire behaviour, and it makes no claims about partial
> gravity beyond stating that PSI contains no such data yet.
