# FIREWISE — Dataset Audit

> **Readiness audit 2026-11-13:** Envelope headline corrected; CFI and E-FIELD duplicate rows noted. See `FINAL_READINESS_AUDIT.md` and `CHANGELOG.md`.

*Status: 2026-11-13. Everything here was checked against files on disk or the live NASA PSI API.
Nothing comes from memory. Every number can be regenerated with the scripts in §8.*

---

## 1. Headline findings

1. **The originally downloaded workspace (`Data/`, 7 files, 460 MB) contains no quantitative measurements.**
   It holds:
   - raw ACME camera frames
   - two camera index files
   - Saffire camera test and calibration images
   - one SAME-R downlink video
   - EXIF text for four BASS crew photos
   - ACME igniter engineering drawings

   It is showcase material, not an evidence base.
2. **The real evidence base is the public NASA PSI repository.** It has an open JSON API that needs no login
   for metadata, and files download via pre-signed S3 links. **24 investigations** are classed as Combustion
   Science:
   - 19 flight investigations
   - 5 ground/modeling studies

   All 24 records are harvested. PSI-23 needed `curl --compressed`, because the server truncated plain downloads.
3. **PSI "Experimental tables" give run-level conditions for 20 investigations (22 CSV files).** They
   normalize to **2,019 run rows** with provenance, plus **475 data-quality flags**. Of these, 2,007 are
   combustion or aerosol runs; the remaining 12 are flow-visualization records and ground-study summaries. This is the backbone of the
   "how did tests differ" comparison that the challenge asks for.
4. **Coverage is uneven.**
   - Seven investigations list **no downloadable raw data** even though their records report 17 GB–2.0 TB
     in `totalFileSize`: FLEX, FLEX-2, BRE, CLD, E-FIELD, Saffire-II and SLICE.
   - FLEX's experimental table is nevertheless the richest *measured* outcome table in PSI: 274 droplet tests
     with extinction diameter, burning rate and burn time.
5. **Exploration-atmosphere gap (key scientific finding; `derived/coverage_summary.json`).**
   - **No run** documents *ambient* O₂ of 30–36% together with 8.2–10.2 psia (corrected; an earlier "35" used a
     mislabeled 0.5–0.75 atm band and counted inverse-flame burner-stream O₂). The nearest evidence brackets the
     envelope: 10 CFI-G gas flames at ≈7.35 psia (reported) and 17 FLEX droplets at 10.33–10.50 psia (measured).
     Source: `derived/claims_check.json`.
   - **Not one of the 264 real solid-material tests** (BASS, BASS-II, Saffire I–III) documents chamber pressure.
     The 140 that document O₂ reach at most 22.2%; 124 document no O₂.
   - The only elevated-O₂ evidence for *solid-like* burning is BRE's gas-fed solid emulator: 21–40% O₂, with
     pressure "varied but not identified".
   - Partial-gravity runs: **0**, consistent with the challenge statement.

---

## 2. Local workspace inventory (`Data/`, read-only)

Integrity: SHA-256 baseline in `derived/data_sha256.txt`, re-verified after every script run (`OK: 7 files
unchanged`). All six ZIP archives pass CRC checks (`zipfile.testzip`).
Per-member inventory: `derived/inventory_local.csv` (996 archive members).

| File | Size | Format (verified) | Contents | PSI provenance | Measurements? | Parseable |
|---|---|---|---|---|---|---|
| `PSI-159_Raw Data_21265C3_ACME.zip` | 415 MB | ZIP → 373 `.hobj` + `.mdipsug` (CSV) + `.next` | Raw colour-camera frames, 1360×1024 BayerRG12, 2021-09-22 15:34:58–15:36:04 UTC. 1 fps / 1 s exposure, then 10 fps / 0.1 s | **PSI-159 CFI-G**, name and size match | Imagery only, but **its conditions are known from the PSI table**: inverse flame, O₂ stream X_O₂ = 0.50 into n-butane/N₂ ambient (X_fuel 0.058), ≈3.3 bar; ignited, burned ~2 s, self-extinguished; T_ad 2320 K | Partial: `.hobj` is MVTec HALCON `write_object` format (HOBJ magic at both ends). Needs a validated reader |
| `PSI-159_Raw Data_ACME_21265H1.mdipsug` | 60 KB | CSV, 362 rows | Frame index for test 21265H1. **The 362 frames are not present** | **PSI-159**, name and size match | No (camera timing). PSI table: inverse flame, X_O₂ = 0.40, n-butane ambient, ≈3.3 bar, burned ~1 s | Yes |
| `ACME_drawings_igniter.zip` | 2.9 MB | ZIP → 14 PDF | ACME igniter assembly drawings: Kanthal 28 AWG heating wire, tip insulator, connectors | **PSI-23 s-Flame, Engineering Documents** (name and size match). PSI-23 holds the full ACME drawing set (burners, data and analog cameras, diagnostics, avionics) | No (hardware documentation) | 5 of 14 have a text layer; 9 are scans needing OCR |
| `SAFFIRE_II_F1C1-BIT_jpeg.zip` | 21 MB | ZIP → 600 JPEG 1360×1024 | 20 s at ~30 fps, 2016-11-21 23:27:52 UTC. Static frames (mean ≈24/255), **no flame** | **Not in any PSI file listing.** The PSI-99 table defines `F1C1/F1C2` as "pre-test flow visualization data for sample 2-1" (camera 1), which explains the absence of fire. Date = Saffire-II burn day | No (flow visualization) | Yes |
| `SAFFIRE-III_F1C1_1200x920.zip` | 172 KB | ZIP → 2 JPEG | Distortion-grid calibration (30 mm blocks), colour and mono | **PSI-100**, exact byte-size match | Calibration only (pixel → mm) | Yes |
| `4 lampwick vlc-record-2010-09-08…ts.zip` | 42 MB | ZIP → MPEG-TS, H.264 | Ground capture of an ISS downlink, cotton lamp-wick smoke run | **PSI-101 SAME-R**, name and size match | Video only | Needs ffmpeg |
| `2013_04_16_txt.zip` | 3 KB | ZIP → 4 TXT | EXIF dumps for crew photos iss035e020036–39 (Nikon D2Xs). **The photos are absent** | **PSI-26 BASS**, session 2013_04_16, name and size match | No | Yes |

---

## 3. PSI combustion investigations: availability and data class

**Data-class legend** (highest class the investigation reaches):
- **A** — raw or telemetry measurement files listed and downloadable
- **B** — processed or analyzed data files
- **C** — numerical summary table plus publications only
- **D** — descriptive metadata and documents only
- **E** — not retrievable

"Runs" counts the normalized rows in `derived/runs.csv`.

| PSI | Investigation | Platform / facility | Files listed (GB) | Record `totalFileSize` | Runs | Class | Notes |
|---|---|---|---|---|---|---|---|
| 10 | ACME Flame Design | ISS CIR / ACME | 3,807 (2,180) | 2,180 GB ✓ | 327 | **A** | Per-test `_data.csv`, `_TP.txt`, MFC setpoints, comments. Normal and inverse flames, X_O₂ 0.20–0.85, 0.43–3.0 atm |
| 20 | ACME BRE | ISS CIR / ACME | 2 (0.0) | 2,036 GB ✗ | 43 (18 days × O₂ levels) | **C** | Test-day table: O₂ 21–40%, burner 25/50 mm. Pressure "varied but not identified" |
| 21 | ACME CLD Flame | ISS CIR / ACME | 2 (0.0) | 2,006 GB ✗ | 32 | **C** | Fuel concentration ranges only. O₂ and P not in table |
| 22 | ACME E-FIELD Flames | ISS CIR / ACME | 2 (0.0) | 950 GB ✗ | 21 rows (20 unique test days; 1 duplicate) | **C** | Mesh polarity, fuel concentration |
| 23 | ACME s-Flame | ISS CIR / ACME | 4,165 (782) | 782 GB ✓ | 18 days | **A** | H₂, CH₄, H₂/CH₄, C₂H₄ with N₂ or He; ≈21% and ≈30% O₂ at ≈1 atm (approximate). Record fetched with curl (truncation with urllib) |
| 159 | ACME CFI-G | ISS CIR / ACME | 3,756 (2,086) | 2,086 GB ✓ | 333 | **A** | 179 normal + 154 inverse tests: fuel, X_O₂, ≈p, T_ad, Z_st, hot ignition, burn time, self-extinction vs. flow termination, **cool flame yes (7 tests, PCI-A…G)** |
| 39 | CFI | ISS CIR / MDCA | 2,832 (719) | 719 GB ✓ | 87 rows (79 unique; 8 exact duplicates) | **A** | n-dodecane droplets. P, O₂/N₂/He, support fiber. **Test numbers continue the FLEX series** |
| 69 | FLEX | ISS CIR / MDCA | 1 (0.0) | 924 GB ✗ | 274 | **C** | **Measured outcomes:** extinction diameter, burning rate, burn time, end mode |
| 68 | FLEX-2 | ISS CIR / MDCA | 1 (0.0) | 1,225 GB ✗ | 8 | **C** | Envelope per fuel: O₂ 0.17–0.30, 0.5–3 atm, 0.1–5 cm/s (ranges, not tests) |
| 26 | BASS | ISS MSG | 212 (164) | 164 GB ✓ | 122 | **A** | Material and size per test. No O₂, P or flow in table |
| 25 | BASS-II | ISS MSG | 695 (275) | 275 GB ✓ | 129 | **A** | Measured initial and final O₂, CO₂, CO. Flow only as fan-display settings |
| 107 | SPICE | ISS MSG | 188 (6.9) | 6.9 GB ✓ | 469 | **A** | Fuel, nozzle, fuel rate, coflow air rate. 34 exact duplicate rows |
| 106 | SLICE | ISS MSG | 2 (0.0) | 73 GB ✗ | 12 | **C** | Date and fuel only. The record claims ">4,000 images" |
| 98 | Saffire-I | Cygnus (uncrewed) | 76 (12.3) | 12.3 GB ✓ | 4 | **A** | Large SIBAL sheet 94×40.6 cm, 20 cm/s, O₂ ≈21.5% |
| 99 | Saffire-II | Cygnus | 2 (0.0) | 16.9 GB ✗ | 15 | **C** | 9 samples with **µg *and* 1g** burn and spread results in one table |
| 100 | Saffire-III | Cygnus | 87 (35.2) | 35.2 GB ✓ | 2 | **A** | SIBAL, 30 cm/s, concurrent vs. opposed flow |
| 102 | SAME | ISS MSG | 105 (0.66) | 0.66 GB ✓ | 8 | **B** | 63 analyzed-data files (per-run `.xls`) |
| 101 | SAME-R | ISS MSG | 343 (6.3) | 6.3 GB ✓ | 109 | **A** | Instrument logs (HKPData CSV), analyzed `.xls`, TEM images |
| 47 | DAFT / DAFT-2 | ISS cabin | 33 (0.04) | 0.04 GB ✓ | 2 | **A** | Raw P-Trak/DustTrak text, analyzed `.xls`. Arizona Road Dust, not smoke |
| 60 | SPICE analysis (ground) | — | 1 | 0 | — | **D** | Metadata only |
| 62 | BASS flame-spread FGM modeling (ground) | — | 1 | 0 | — | **D** | Metadata only |
| 115 | SAME smoke modeling (ground) | — | 47 (0.26) | ✓ | — | **B** | 44 analyzed-data files |
| 117 | FLEX cool-flame CFD (ground) | — | 16 (0.07) | ✓ | — | **B** | 10 analyzed-data files |
| 142 | Counterflow cool flames (ground) | — | 3 | ✓ | 8 | **D** | "Data summary" table points to figures in publications |

✓ = the listed files add up to `totalFileSize`. ✗ = the record reports data that its file listing does not
show. Treat ✗ as "data exists at NASA but is not enumerated or downloadable via PSI today". This is UNVERIFIED
beyond what the API returns.

---

## 4. What we downloaded (and what we deliberately did not)

**User policy (2026-11-13):**
- ≤500 MB per file
- "telemetry only" for raw data: CSV, TXT, MDIPSUG, ASC, LOG, PDF, XLS and similar
- **no video and no camera-image archives** (`.ts`, `.mp4`, `.zip` image bundles, `.hobj`)
- documents, reports and experimental tables always fetched

| Tier | Files | Size | Status |
|---|---|---|---|
| Investigation records (JSON) | 24 + search listing | 19 MB | ✓ (`sources/psi_api/`) |
| Experimental tables | 22 CSV (20 investigations) | <1 MB | ✓ all 22 |
| Documents (reports, science docs, analyzed data, presentations, engineering) | ~478 | ~0.2 GB | in progress |
| Raw telemetry (no media) | ~7,200 | ~7.3 GB | in progress (resumable) |
| Video and image archives | — | >2 TB | **not downloaded** (policy). Showcase sample: the local CFI-G zip |

Every downloaded file is logged in `sources/sources.csv` with its URL, local path, byte count, SHA-256 and
UTC fetch time. Downloads are verified against the byte size PSI reports.

---

## 5. Data-quality findings (surface these, never silently fix them)

### 5a. Repository-level metadata defects
| Investigation | Defect |
|---|---|
| PSI-20, 21, 22, 68, 69, 99, 106 | `totalFileSize` of 17 GB–2 TB, yet only the experimental table and/or metadata are listed |
| PSI-98 Saffire-I | Investigation dates 2001-03-02 → 2008-02-28 (the SAME dates; Saffire-I burned in June 2016) |
| PSI-26 BASS | Metadata zip is named `PSI-26_metadata_PSI-102_BASS.zip`, but 102 is the SAME ID |
| PSI-98, PSI-100 | `flightProgram` = "International Space Station (ISS)", but the hardware field says "enclosure in Cygnus" |
| PSI-100 | Impact text says "The Saffire-I experiment…" (copied from PSI-98) |
| PSI-106, PSI-107 | Investigation start and end dates blank |
| PSI-47 | The file list also contains Constrained Vapor Bubble files (reported by the research agent; to verify) |
| PSI-159 | Objective lists fuels "propane, n-butane, n-pentane". **PSI's own CFI-G tables list ethane, propane and butane (pure, 30% and 50% in N₂), with no pentane.** This is consistent with Kim et al. (PCI 39, 2023). Planned ≠ tested |

### 5b. Experimental-table defects (all logged per row in `derived/runs_flags.csv`)
| Table | Defect | Our handling |
|---|---|---|
| BRE | O₂ cells `3400%`, `2100%` | Read as 34% and 21% (spreadsheet percent-format artifact); flagged |
| BRE | Pressure "varied but not identified" | Pressure stays **missing**; flagged on every row |
| CLD, s-Flame | Fuel bottle `40% CH5 … CH14`, `C2H5`; atmosphere `with N3 … N6` | Corrected to CH₄ / C₂H₄ / N₂ (auto-increment artifact); original kept in `raw` |
| Saffire-II | Headers `?-g Burn Length` | Interpreted as `µ-g` (encoding loss); flagged |
| SPICE | 34 exact duplicate rows; 8 negative air rates (−0.28, −5.92 cm/s) | Kept as reported and flagged |
| FLEX | Test 114 pressure = 0 mmHg | Treated as missing |
| FLEX | 6 initial-diameter cells contain `�` (encoding loss) | Kept missing; flagged |
| FLEX | Header "CO initial…" is CO₂; "Burning rate; mm" has an implausible unit | Interpretation flagged; unit to verify against NASA/TP-2015-216046 |
| BASS | Date `6/29/\`12` | Flagged |
| E-FIELD | Continuation rows with only a fuel concentration | Merged into the preceding test day |
| Flame Design | "RAMPED" composition/flow tests | Mass flows missing; flagged |
| CFI-G | Pressure given as "approx p (bar)" | Converted to atm, status `reported` (approximate) |
| CFI-G (inverse) | 1,015 CSV rows, of which only 154 hold tests (rest blank) | Blank rows dropped |
| FLEX-2 | Rows are condition *envelopes* per fuel, not tests | Status `specified`; flagged |

---

## 6. Measured vs. specified vs. missing (normalized run table)

| Field | Measured | Specified (set-point/design) | Missing |
|---|---|---|---|
| O₂ | Flame Design (normal), CFI-G (normal), FLEX, BASS-II. *Derived:* Saffire-II (from CO₂). *Reported:* Saffire-I, s-Flame (≈21/≈30%) | BRE, Flame Design (inverse), CFI-G (inverse), CFI, FLEX-2 | CLD, E-FIELD, BASS, Saffire-III, SAME/SAME-R, SPICE, SLICE, DAFT |
| Pressure | Flame Design, FLEX. *Reported (approx.):* CFI-G, s-Flame (≈1 atm note) | CFI, FLEX-2 | everything else, including **all solid-fuel investigations** |
| Flow | — | Saffire (20/30 cm/s), SPICE, SAME/SAME-R, FLEX-2 (0.1–5), quiescent (0) for BRE/FLEX/CFI/Flame Design | CLD, E-FIELD, BASS, BASS-II (fan display only), SLICE |

---

## 7. Gaps, risks and open items
- **PSI-23 s-Flame:** retrieved via `curl --compressed` after Python downloads were truncated by the server (`IncompleteRead`). The manifest row records the method.
- **CFI-G "Cool flame?" column** is blank for 171 of 179 normal-flame tests. Blank means "not recorded",
  not "no cool flame". The UI must not count blanks as negatives.
- **The HOBJ reader isn't validated.** The local frames can't yet be shown faithfully (P1, time-boxed).
- **Saffire-II BIT frames:** in no PSI file listing. Provenance is inferred from the PSI-99 table (F1C1 = pre-test flow
  visualization) and the burn date.
- Experimental tables are **summaries**. Absence of a value in a table ≠ the value was never measured
  (e.g., BRE pressure). The UI must say "not documented in PSI table", not "not measured".

---

## 8. Reproduce
```bash
cd NasaSA
python3 -I scripts/checksum_data.py Data derived/data_sha256.txt --verify      # originals untouched
python3 -I scripts/harvest_psi.py sources/psi_api                              # PSI records (resumable)
python3 -I scripts/inventory_psi.py sources/psi_api derived/psi --cap-mb 500    # PSI file inventory
python3 -I scripts/inventory_local.py Data sources/psi_api derived/inventory_local
python3 -I scripts/fetch_psi_files.py derived/psi_files.csv sources/psi_files \
    --folders "Raw Data" --exclude-exts ".ts,.zip,.mp4,.hobj" --cap-mb 500       # telemetry tier
python3 -I scripts/build_runs.py sources/psi_files derived/runs                 # 2,019 run rows + flags
python3 -I scripts/coverage.py derived/runs.csv derived/coverage                # gap map + headline numbers
```
