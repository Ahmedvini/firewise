# FIREWISE Digital Twin — Model Validation

Reproducible: `python3 -I scripts/twin_validate.py .` regenerates `derived/twin/validation.json` from `api/twin/validation.py` and the cited reference data in `derived/twin/reference_data.json`. `load_db.py` loads the records into `twin_validation`, and rule R9 fails the build if any record has status `failed`. A pytest test checks that the stored file equals a fresh computation.

## Terminology
- **Verified.** The implementation reproduces reference values that rest on the same governing equation, or on the data its coefficients were fitted to. This checks transcription and arithmetic, not physics.
- **Validated.** The output is compared with **independent** reference data, with error metrics and the reference's stated uncertainty, inside a stated applicability domain.
- **Calibration set.** None. No parameter is fitted to anything; all constants are literature values. The validation references are therefore never used for tuning.
- **NASA PSI.** No implemented model predicts a quantity measured in the PSI tables, so no model is validated against PSI data. No combustion model is implemented.

## Results (engine `firewise-twin-physics 1.0.0`)
| Model / output | Kind | Reference | Domain | n | MAE | RMSE | Bias | Max abs. relative error | Status |
|---|---|---|---|---|---|---|---|---|---|
| A ideal gas — density | verification | U.S. Standard Atmosphere 1976, sea level (1.2250 kg/m³) | 288.15 K, 101.325 kPa | 1 | 2.19×10⁻⁵ kg/m³ | 2.19×10⁻⁵ | −2.19×10⁻⁵ | 0.002% | verified |
| B — molar mass of dry air | verification | USSA 1976 composition, 28.9644 g/mol | dry air | 1 | 0.00037 g/mol | 0.00037 | +0.00037 | 0.001% | verified |
| B — c_p of N₂, O₂, Ar, CO₂ | verification | NIST-JANAF, 298.15 K | 298.15 K | 4 | 0.0139 J/(mol·K) | 0.0265 | −0.0126 | 0.182% (N₂) | verified |
| B — viscosity (Wilke) | **validation** | White (2006) Sutherland law for air, ±2% | air, 250–400 K, 10 K steps | 16 | 0.0806 µPa·s | 0.0837 | +0.0806 | 0.512% | **validated** |
| B — conductivity (Mason–Saxena) | **validation** | White (2006) conductivity law for air, ±2% | air, 250–400 K | 16 | 0.147 mW/(m·K) | 0.179 | −0.099 | 1.027% | **validated** |
| C bulk airflow | verification (unit tests) | — | — | — | — | — | — | — | verified (no metric: no velocity-field data) |
| D1 forced convection | verification (unit tests) | — | — | — | — | — | — | — | verified (no metric: no inert-sample heat-transfer data) |
| D2 wall conduction | verification (unit tests) | — | — | — | — | — | — | — | verified (no metric) |
| Droplet combustion, extinction, flame spread, coupled CFD | — | — | — | — | — | — | — | — | not implemented |

## Interpretation
- **Model A.** The reference standard itself uses the ideal-gas law, so this is a consistency check, not an experimental validation. Real-gas deviations are not quantified.
- **Model B, transport properties.** The Wilke and Mason–Saxena mixing of pure-component data reproduces an independent air correlation within 0.5% (viscosity) and 1.0% (conductivity). That is inside the reference's ±2% accuracy over 250–400 K. The bias is systematic: viscosity is slightly high, and conductivity is slightly low above 300 K.
- **Not validated:**
  - O₂-enriched compositions (for example 34% O₂)
  - temperatures outside 250–400 K
  - any Ar or CO₂ fraction other than air's
- **Model B, c_p.** The N₂ polynomial is defined from 300 K and is −0.18% at 298 K. The other species agree to 0.01% or better.
- **Models C and D.** Correct implementation of the stated equations is shown by unit tests against hand calculations (`tests/test_twin_physics.py`). No error metric is reported, because FIREWISE holds no measurement these models could be meaningfully compared with.

## Uncertainty and applicability as shown to users
- The **Physics view** lists every record above (kind, reference, domain, n, MAE, RMSE, bias, maximum relative error) and tags every output **Verified** or **Validated**.
- The **Copilot** answers "How reliable is the selected model?" from the same records (`twinval:<model>` evidence). It adds an explicit warning when the scenario is O₂-enriched.

## Next validation opportunities
- **Model B at enriched O₂:** compare against tabulated O₂/N₂ mixture transport data, which needs a cited dataset.
- **Model A real-gas check:** compare against NIST reference compressibility data.
- **Model D1:** compare against measured heat-transfer coefficients for flat plates in low-speed flow, which needs a cited experimental dataset.
- **Combustion models (future):** FLEX droplet burning-rate and extinction-diameter columns could serve as validation data. The burning-rate unit must be verified first.
