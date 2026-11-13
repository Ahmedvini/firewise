# FIREWISE Digital Twin — Scientific Models

Engine `firewise-twin-physics 1.0.0` (`api/twin/physics.py`, property data in `api/twin/props.py`).

Every model implements one interface: `PhysicsModel`, with id, version, equations, inputs and outputs (units and valid ranges), assumptions, boundary conditions, applicability, validation status, limitations and references.

The engine follows four rules:
- **Missing inputs** make a model *unavailable*, and the response lists the missing names. Nothing is assumed: no default material, geometry, surface temperature or wall property.
- **Out-of-range inputs** make a model *rejected*. Inputs are never clamped.
- **Every output** carries its unit, `status: simulated` and its own validation status.
- **Deterministic results.** The result includes an input hash.

No combustion model is implemented, and FIREWISE produces no flame, ignition, extinction, spread or fire-risk output.

## Model A — Ideal gas (`ideal_gas` v1.0.0, verified)
- **Equations:** p V = n R T; ρ = p M_mix/(R T); c = p/(R T); c_O₂ = x_O₂ c; ρ_O₂ = c_O₂ M_O₂; zone moles and mass = c V and ρ V.
- **Inputs:**

| Input | Unit | Valid range |
|---|---|---|
| p | kPa | 1–300 |
| T | K | 150–1000 |
| M_mix | g/mol | from Model B |
| x_O₂ | — | — |
| zone volume | m³ | geometric cylinder segment, status `derived` |

- **Outputs:** density (kg/m³), molar concentration (mol/m³), O₂ molar concentration (mol/m³), O₂ mass concentration (g/m³), zone gas moles (mol), zone gas mass (kg).
- **Assumptions:** Z = 1; uniform state in the zone; equipment volume not subtracted.
- **Limitations:** real-gas deviation not quantified; the geometric volume overestimates the gas volume.

## Model B — Gas-mixture properties (`gas_mixture` v1.0.0, validated / verified per output)
- **Composition:** O₂ (user), Ar and CO₂ (optional, 0 if not set and labelled so), N₂ as balance. Helium is not supported in v1 and is never substituted.
- **Equations:**
  - M_mix = Σ x_i M_i
  - c_p,i/R from NASA 7-coefficient polynomials (GRI-Mech 3.0); c_p,mix = Σ x_i c_p,i
  - Sutherland laws for μ_i and k_i (White 2006, Tables 1-2/1-3)
  - Wilke rule for μ_mix; Mason–Saxena for k_mix
  - p_O₂ = x_O₂ p (Dalton); Pr = c_p μ/k; γ = c_p/(c_p − R)
- **Valid range:** 200–600 K, 1–300 kPa.
- **Validated range:** transport properties only, air composition, 250–400 K. O₂-enriched mixtures are inside the implemented range but outside the validated range, and the UI and Copilot say so.
- **Outputs:**

| Output | Unit | Validation status |
|---|---|---|
| Molar mass | g/mol | verified |
| p_O₂ | kPa | verified |
| p_O₂ ÷ 21.22 kPa | — | verified |
| c_p | J/(mol·K) and J/(kg·K) | verified |
| γ | — | verified |
| Viscosity | µPa·s | validated |
| Conductivity | mW/(m·K) | validated |
| Pr | — | validated |

## Model C — Simplified bulk airflow (`bulk_airflow` v1.0.0, verified)
- **Equations:** A = πD²/4; V = A L; U = Q/A; ACH = Q/V; τ = V/Q; Re_D = ρ U D/μ.
- **Inputs:** the user-defined cylinder (D, L) and ventilation flow Q; volume-weighted ρ and μ from Models A and B.
- **Outputs:** cross-section area, habitat volume, bulk axial velocity (cm/s), air changes per hour, residence time (min), Re_D. The regime label uses pipe thresholds and is indicative only.
- **Not a CFD model.** Local airflow at the experiment is a separate user-defined input and is not computed. Zero ventilation makes the model unavailable.
- **The 3D airflow arrows** take their speed from this model (logarithmically compressed for visibility) and are labelled "illustrative direction".

## Model D1 — Forced convection over a flat sample (`forced_convection_flat_plate` v1.0.0, verified)
- **Equations:** T_f = (T_s + T_∞)/2, with properties from Model B at T_f; Re_L = ρ u L/μ; Nu_L = 0.664 Re_L^½ Pr^⅓; h = Nu k/L; q″ = h (T_s − T_∞).
- **Applicability:** laminar regime (Re_L < 5×10⁵, 0.6 ≤ Pr ≤ 50); anything outside is rejected. Inert, non-burning surface.
- **Unavailable cases:**
  - surface temperature not given: never assumed
  - zero local airflow: in microgravity heat transfer is then by diffusion and radiation, which are not modelled
- **Gravity:** at lunar, Mars or Earth gravity the result carries a warning that buoyant convection is not included.

## Model D2 — Steady 1-D wall conduction (`wall_conduction` v1.0.0, verified)
- **Equations:** q″ = k (T_in − T_out)/t; R″ = t/k; Q = q″ π D L_zone.
- **Inputs:** all four wall inputs must be user-supplied: thickness, conductivity, inner and outer surface temperature. FIREWISE has no wall-material database.

## Not implemented (registry entries with status `not_implemented`, no outputs)
| Model | Would need | Candidate validation data |
|---|---|---|
| Droplet combustion (quasi-steady d²-law) | fuel/gas transport properties, flame-sheet and radiative-loss treatment | FLEX (PSI-69) droplet d₀, burning rate (unit unverified), extinction diameter |
| Flame extinction limits | chemical kinetics, radiation | ACME Flame Design / CFI-G end-mode observations |
| Flame spread over solids | pyrolysis and gas-phase kinetics, sample thermal properties | Saffire (PSI-98/99/100) reported spread and burn lengths; BASS |
| Coupled flow and combustion (CFD) | a validated CFD solver with combustion and radiation | not available in PSI at the needed resolution |

## Where each number comes from
| Constant | Source |
|---|---|
| R = 8.314462618 J/(mol·K) | CODATA 2018 |
| Molar masses | IUPAC standard atomic weights |
| NASA-7 c_p coefficients | GRI-Mech 3.0 thermo data (low-T range) |
| Sutherland μ0, k0, S | White, *Viscous Fluid Flow*, 3rd ed. (2006), Tables 1-2 and 1-3 |
| Mixing rules | Wilke (1950); Mason & Saxena (1958) |
| Laminar flat-plate correlation | Pohlhausen solution, e.g. Incropera et al. |
