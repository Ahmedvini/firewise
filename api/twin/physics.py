"""Physics twin: a common model interface, the implemented models (A–D) and a deterministic engine.

Rules enforced here:
- Every model declares id, version, governing equations, inputs/outputs with units and valid ranges,
  assumptions, boundary conditions, applicability domain, validation status and limitations.
- Inputs outside a model's valid range are REJECTED (status "rejected"), never clamped.
- Missing inputs make a model UNAVAILABLE (status "unavailable") with the missing names; nothing is
  silently assumed (no default material properties, geometry or boundary conditions).
- No combustion model is implemented. Planned models are listed with status "not_implemented".
"""
import hashlib
import json
import math
from dataclasses import dataclass, field

from . import props

ENGINE_VERSION = "firewise-twin-physics 1.0.0"
KPA = 1000.0


@dataclass(frozen=True)
class Var:
    name: str
    unit: str
    description: str
    min: float | None = None
    max: float | None = None


@dataclass
class PhysicsModel:
    id: str
    name: str
    version: str
    equations: list[str]
    inputs: list[Var]
    outputs: list[Var]
    assumptions: list[str]
    boundary_conditions: list[str]
    applicability: str
    validation_status: str  # verified | validated | not_validated | not_implemented
    validation_summary: str
    limitations: list[str]
    references: list[str]
    output_validation: dict = field(default_factory=dict)  # output name -> status, where it differs from the model status
    implemented: bool = True

    def card(self):
        return {"id": self.id, "name": self.name, "version": self.version, "equations": self.equations,
                "inputs": [v.__dict__ for v in self.inputs], "outputs": [v.__dict__ for v in self.outputs],
                "assumptions": self.assumptions, "boundary_conditions": self.boundary_conditions,
                "applicability": self.applicability, "validation_status": self.validation_status,
                "validation_summary": self.validation_summary, "output_validation": self.output_validation,
                "limitations": self.limitations, "references": self.references, "implemented": self.implemented}


class Unavailable(Exception):
    pass


class Rejected(Exception):
    pass


def _check(model, values):
    """values: name -> float|None for every declared input. Missing -> Unavailable; out of range -> Rejected."""
    missing = [v.name for v in model.inputs if values.get(v.name) is None]
    if missing:
        raise Unavailable(missing)
    bad = []
    for v in model.inputs:
        x = values[v.name]
        if (v.min is not None and x < v.min) or (v.max is not None and x > v.max):
            bad.append(f"{v.name}={x:g} {v.unit} outside the valid range [{v.min:g}, {v.max:g}] {v.unit}")
    if bad:
        raise Rejected(bad)


# ------------------------------------------------------------------------------------------- model B
MIXTURE = PhysicsModel(
    id="gas_mixture", name="Model B — Gas-mixture properties", version="1.0.0",
    equations=[
        "x_i = n_i / Σ n_j  (mole fractions; N₂ is the balance gas)",
        "M_mix = Σ x_i M_i",
        "c_p,mix = Σ x_i c_p,i(T),  c_p,i/R = a1 + a2 T + a3 T² + a4 T³ + a5 T⁴  (NASA 7-coefficient polynomial)",
        "μ_i = μ0,i (T/T0)^1.5 (T0+S_i)/(T+S_i);  k_i analogous  (Sutherland laws, T0 = 273 K)",
        "μ_mix = Σ x_i μ_i / Σ_j x_j φ_ij;  φ_ij = [1 + (μ_i/μ_j)^½ (M_j/M_i)^¼]² / [8 (1 + M_i/M_j)]^½  (Wilke)",
        "k_mix = Σ x_i k_i / Σ_j x_j φ_ij  (Mason–Saxena)",
        "p_O₂ = x_O₂ p  (Dalton)",
        "Pr = c_p μ / k,  γ = c_p / (c_p − R)",
    ],
    inputs=[Var("o2_mole_fraction", "-", "O₂ mole fraction (user-defined or documented)", 0.01, 1.0),
            Var("ar_mole_fraction", "-", "Ar mole fraction (0 if not specified by the user)", 0.0, 0.05),
            Var("co2_mole_fraction", "-", "CO₂ mole fraction (0 if not specified by the user)", 0.0, 0.05),
            Var("pressure_kPa", "kPa", "Total gas pressure", 1.0, 300.0),
            Var("temperature_K", "K", "Gas temperature", 200.0, 600.0)],
    outputs=[Var("molar_mass", "g/mol", "Mixture molar mass"),
             Var("o2_partial_pressure", "kPa", "O₂ partial pressure (Dalton)"),
             Var("o2_partial_pressure_vs_sea_level_air", "-", "p_O₂ ÷ 21.22 kPa (sea-level dry air)"),
             Var("cp_molar", "J/(mol·K)", "Isobaric molar heat capacity"),
             Var("cp_mass", "J/(kg·K)", "Isobaric specific heat"),
             Var("gamma", "-", "Heat-capacity ratio"),
             Var("viscosity", "µPa·s", "Dynamic viscosity (Wilke)"),
             Var("thermal_conductivity", "mW/(m·K)", "Thermal conductivity (Mason–Saxena)"),
             Var("prandtl", "-", "Prandtl number")],
    assumptions=["Dry gas: water vapour is not included.",
                 "Only O₂, N₂ (balance), Ar and CO₂ are represented; other trace gases are neglected.",
                 "Transport properties are pressure-independent (dilute-gas limit).",
                 "Ideal-gas heat capacities (no real-gas correction)."],
    boundary_conditions=["Not applicable (local thermodynamic state)."],
    applicability="O₂/N₂/Ar/CO₂ mixtures, 200–600 K, 1–300 kPa. Transport properties validated only for air-like composition at 250–400 K.",
    validation_status="validated",
    validation_summary="Viscosity and conductivity validated against the independent Sutherland air correlations (White 2006) at 250–400 K; "
                       "molar mass and c_p verified against U.S. Standard Atmosphere 1976 and NIST-JANAF reference values. See /api/twin/validation.",
    output_validation={"molar_mass": "verified", "cp_molar": "verified", "cp_mass": "verified", "gamma": "verified",
                       "o2_partial_pressure": "verified", "o2_partial_pressure_vs_sea_level_air": "verified",
                       "viscosity": "validated", "thermal_conductivity": "validated", "prandtl": "validated"},
    limitations=["O₂-enriched mixtures (x_O₂ > 0.21) are inside the implemented range but the transport validation used air composition only.",
                 "N₂ c_p polynomial is defined from 300 K; 200–300 K is a mild extrapolation (−0.18% vs JANAF at 298 K).",
                 "Helium diluent is not supported in v1 (no property data included)."],
    references=[props.SOURCES[k] for k in ("M", "cp", "mu", "k", "wilke", "mason_saxena")],
)


def run_mixture(v):
    _check(MIXTURE, v)
    x_o2, x_ar, x_co2 = v["o2_mole_fraction"], v["ar_mole_fraction"], v["co2_mole_fraction"]
    if x_o2 + x_ar + x_co2 > 1.0 + 1e-9:
        raise Rejected(["mole fractions of O₂ + Ar + CO₂ exceed 1"])
    x = props.normalize({"O2": x_o2, "Ar": x_ar, "CO2": x_co2, "N2": max(0.0, 1.0 - x_o2 - x_ar - x_co2)})
    T, p = v["temperature_K"], v["pressure_kPa"]
    M = props.molar_mass(x)
    cpm = props.mixture_cp_molar(x, T)
    mu = props.mixture_viscosity(x, T)
    k = props.mixture_conductivity(x, T)
    cp_mass = cpm / M
    po2 = x.get("O2", 0.0) * p
    return {"molar_mass": M * 1000, "o2_partial_pressure": po2, "o2_partial_pressure_vs_sea_level_air": po2 / (0.209476 * props.P_SEA_LEVEL / KPA),
            "cp_molar": cpm, "cp_mass": cp_mass, "gamma": cpm / (cpm - props.R_UNIVERSAL), "viscosity": mu * 1e6,
            "thermal_conductivity": k * 1e3, "prandtl": cp_mass * mu / k, "_x": x, "_M": M, "_mu": mu, "_k": k, "_cp_mass": cp_mass}


# ------------------------------------------------------------------------------------------- model A
IDEAL_GAS = PhysicsModel(
    id="ideal_gas", name="Model A — Ideal gas", version="1.0.0",
    equations=["p V = n R T", "ρ = p M_mix / (R T)", "c = n/V = p / (R T)", "c_O₂ = x_O₂ c,  ρ_O₂ = c_O₂ M_O₂",
               "n_zone = c V_zone,  m_zone = ρ V_zone"],
    inputs=[Var("pressure_kPa", "kPa", "Total gas pressure", 1.0, 300.0),
            Var("temperature_K", "K", "Gas temperature", 150.0, 1000.0),
            Var("molar_mass_g_mol", "g/mol", "Mixture molar mass (from Model B)", 2.0, 100.0),
            Var("o2_mole_fraction", "-", "O₂ mole fraction", 0.0, 1.0),
            Var("zone_volume_m3", "m³", "Gas volume of the zone (from habitat geometry)", 0.01, 5000.0)],
    outputs=[Var("density", "kg/m³", "Gas density"), Var("molar_concentration", "mol/m³", "Total molar concentration"),
             Var("o2_molar_concentration", "mol/m³", "O₂ molar concentration"), Var("o2_mass_concentration", "g/m³", "O₂ mass concentration"),
             Var("zone_gas_moles", "mol", "Gas amount in the zone volume"), Var("zone_gas_mass", "kg", "Gas mass in the zone volume")],
    assumptions=["Ideal-gas behaviour (compressibility factor Z = 1).",
                 "Uniform pressure, temperature and composition within the zone.",
                 "Zone volume is the geometric cylinder segment; equipment volume is not subtracted."],
    boundary_conditions=["Closed control volume at the stated state (no transient)."],
    applicability="Non-reacting gas at 150–1000 K and 1–300 kPa, far from condensation.",
    validation_status="verified",
    validation_summary="Verified against the U.S. Standard Atmosphere 1976 sea-level density (same governing equation; a consistency check, not an independent experimental validation).",
    limitations=["Real-gas (compressibility) deviations are not quantified in v1.",
                 "Equipment displacement makes the true gas volume smaller than the geometric volume."],
    references=[props.SOURCES["R"], "U.S. Standard Atmosphere, 1976 (NOAA/NASA/USAF), sea-level values"],
)


def run_ideal_gas(v):
    _check(IDEAL_GAS, v)
    p, T, M = v["pressure_kPa"] * KPA, v["temperature_K"], v["molar_mass_g_mol"] / 1000
    rho = props.ideal_gas_density(p, T, M)
    c = p / (props.R_UNIVERSAL * T)
    co2 = v["o2_mole_fraction"] * c
    return {"density": rho, "molar_concentration": c, "o2_molar_concentration": co2,
            "o2_mass_concentration": co2 * props.COMPONENTS["O2"]["M"] * 1000,
            "zone_gas_moles": c * v["zone_volume_m3"], "zone_gas_mass": rho * v["zone_volume_m3"]}


# ------------------------------------------------------------------------------------------- model C
AIRFLOW = PhysicsModel(
    id="bulk_airflow", name="Model C — Simplified bulk airflow", version="1.0.0",
    equations=["A = π D² / 4,  V = A L", "U_bulk = Q / A", "ACH = Q / V  (air changes per hour)", "τ = V / Q  (nominal residence time)",
               "Re_D = ρ U_bulk D / μ"],
    inputs=[Var("diameter_m", "m", "Habitat interior diameter (user-defined geometry)", 1.0, 10.0),
            Var("length_m", "m", "Habitat interior length (user-defined geometry)", 2.0, 30.0),
            Var("ventilation_m3_h", "m³/h", "Volumetric ventilation flow (user-defined)", 0.001, 5000.0),
            Var("density_kg_m3", "kg/m³", "Gas density (Model A)", 0.01, 10.0),
            Var("viscosity_Pa_s", "Pa·s", "Gas viscosity (Model B)", 1e-6, 1e-4)],
    outputs=[Var("cross_section_area", "m²", "Cross-sectional area"), Var("habitat_volume", "m³", "Geometric habitat volume"),
             Var("bulk_velocity", "cm/s", "Cross-section-averaged axial velocity"), Var("air_changes_per_hour", "1/h", "Air changes per hour"),
             Var("residence_time", "min", "Nominal residence time"), Var("reynolds_number_D", "-", "Reynolds number on diameter")],
    assumptions=["Steady, incompressible, plug-like axial throughflow from the forward supply to the aft return.",
                 "Fully mixed volume for ACH and residence time.",
                 "Empty cylinder: racks and equipment do not block the cross-section."],
    boundary_conditions=["Uniform supply at one end cap, uniform return at the other (user-chosen direction)."],
    applicability="Habitat-scale bulk quantities only. It does not resolve local velocities, jets, recirculation or dead zones.",
    validation_status="verified",
    validation_summary="Algebraic definitions verified by unit tests; no velocity-field validation (this is not a CFD model).",
    limitations=["Local airflow at an experiment is NOT computed by this model; it is a separate user-defined input.",
                 "Re_D flow-regime labels use internal-pipe thresholds and are indicative only for a cabin with equipment.",
                 "Buoyancy, fans, diffusers and thermal plumes are not represented."],
    references=["Mass conservation and the definition of the Reynolds number (any fluid-mechanics text, e.g. White, Fluid Mechanics)"],
)


def run_airflow(v):
    _check(AIRFLOW, v)
    D, L, Q = v["diameter_m"], v["length_m"], v["ventilation_m3_h"] / 3600.0
    A = math.pi * D * D / 4
    V = A * L
    U = Q / A
    Re = v["density_kg_m3"] * U * D / v["viscosity_Pa_s"]
    return {"cross_section_area": A, "habitat_volume": V, "bulk_velocity": U * 100, "air_changes_per_hour": Q * 3600 / V,
            "residence_time": V / Q / 60, "reynolds_number_D": Re,
            "_regime": "laminar (Re_D < 2300, pipe threshold)" if Re < 2300 else ("transitional (pipe thresholds)" if Re < 4000 else "turbulent (Re_D > 4000, pipe threshold)")}


# ------------------------------------------------------------------------------------------- model D
CONVECTION = PhysicsModel(
    id="forced_convection_flat_plate", name="Model D1 — Forced convection over a flat sample", version="1.0.0",
    equations=["T_f = (T_s + T_∞)/2  (properties at film temperature, Model B)", "Re_L = ρ u L / μ",
               "Nu_L = 0.664 Re_L^½ Pr^⅓  (laminar, average, isothermal plate)", "h = Nu_L k / L", "q″ = h (T_s − T_∞)"],
    inputs=[Var("airflow_m_s", "m/s", "Local airflow speed at the sample (user-defined)", 0.001, 5.0),
            Var("characteristic_length_m", "m", "Sample length in the flow direction (user-defined)", 0.001, 2.0),
            Var("gas_temperature_K", "K", "Free-stream gas temperature", 200.0, 600.0),
            Var("surface_temperature_K", "K", "Sample surface temperature (user-defined)", 200.0, 900.0),
            Var("pressure_kPa", "kPa", "Total gas pressure", 1.0, 300.0),
            Var("o2_mole_fraction", "-", "O₂ mole fraction", 0.01, 1.0),
            Var("ar_mole_fraction", "-", "Ar mole fraction", 0.0, 0.05),
            Var("co2_mole_fraction", "-", "CO₂ mole fraction", 0.0, 0.05)],
    outputs=[Var("film_temperature", "K", "Film temperature"), Var("reynolds_number_L", "-", "Reynolds number on sample length"),
             Var("nusselt_number_L", "-", "Average Nusselt number"), Var("heat_transfer_coefficient", "W/(m²·K)", "Average convective coefficient"),
             Var("heat_flux", "W/m²", "Convective heat flux, positive from surface to gas")],
    assumptions=["Steady, laminar boundary layer on a smooth isothermal flat plate aligned with the flow.",
                 "Forced convection only: buoyancy-driven flow is not included.",
                 "Radiation is not included.", "Non-reacting surface (no flame, no pyrolysis, no blowing)."],
    boundary_conditions=["Uniform free stream u, T_∞ parallel to the plate; uniform surface temperature T_s."],
    applicability="Re_L < 5×10⁵ and 0.6 ≤ Pr ≤ 50, non-burning surfaces. In microgravity buoyancy is negligible; at lunar, Mars or Earth gravity buoyancy is present but not modelled.",
    validation_status="verified",
    validation_summary="Classical laminar boundary-layer correlation; implementation verified by unit tests. Not validated against NASA PSI data in this project.",
    limitations=["Not a flame or ignition model: it gives the convective heat exchange of an inert surface only.",
                 "Leading-edge, finite-width and sample-holder effects are ignored.",
                 "Mixed (forced + buoyant) convection at partial or Earth gravity is not modelled."],
    references=["Incropera, DeWitt, Bergman & Lavine, Fundamentals of Heat and Mass Transfer, laminar flat-plate correlation (Pohlhausen solution)"],
)


def run_convection(v):
    _check(CONVECTION, v)
    Tf = (v["surface_temperature_K"] + v["gas_temperature_K"]) / 2
    mix = run_mixture({"o2_mole_fraction": v["o2_mole_fraction"], "ar_mole_fraction": v["ar_mole_fraction"],
                       "co2_mole_fraction": v["co2_mole_fraction"], "pressure_kPa": v["pressure_kPa"], "temperature_K": Tf})
    rho = props.ideal_gas_density(v["pressure_kPa"] * KPA, Tf, mix["_M"])
    Re = rho * v["airflow_m_s"] * v["characteristic_length_m"] / mix["_mu"]
    Pr = mix["prandtl"]
    if Re >= 5e5 or not 0.6 <= Pr <= 50:
        raise Rejected([f"Re_L = {Re:.3g}, Pr = {Pr:.3g}: outside the laminar correlation range (Re_L < 5e5, 0.6 ≤ Pr ≤ 50)"])
    Nu = props.laminar_flat_plate_nu(Re, Pr)
    h = Nu * mix["_k"] / v["characteristic_length_m"]
    return {"film_temperature": Tf, "reynolds_number_L": Re, "nusselt_number_L": Nu, "heat_transfer_coefficient": h,
            "heat_flux": h * (v["surface_temperature_K"] - v["gas_temperature_K"])}


CONDUCTION = PhysicsModel(
    id="wall_conduction", name="Model D2 — Steady 1-D wall conduction", version="1.0.0",
    equations=["q″ = k (T_in − T_out) / t  (Fourier, steady, 1-D)", "R″ = t / k", "Q = q″ A,  A = π D L_zone"],
    inputs=[Var("thickness_m", "m", "Wall layer thickness (user-defined)", 0.0005, 0.5),
            Var("conductivity_W_mK", "W/(m·K)", "Wall thermal conductivity (user-defined; never defaulted)", 0.01, 500.0),
            Var("inner_temperature_K", "K", "Inner surface temperature (user-defined)", 100.0, 500.0),
            Var("outer_temperature_K", "K", "Outer surface temperature (user-defined)", 3.0, 500.0),
            Var("wall_area_m2", "m²", "Wall area of the zone (from habitat geometry)", 0.01, 1000.0)],
    outputs=[Var("heat_flux", "W/m²", "Conductive heat flux, positive outward"), Var("thermal_resistance", "m²·K/W", "Area-specific thermal resistance"),
             Var("heat_rate", "W", "Heat rate through the zone wall")],
    assumptions=["Steady state, one-dimensional conduction through a single homogeneous layer.",
                 "Surface temperatures are imposed (Dirichlet); no contact resistance; curvature neglected (t ≪ D)."],
    boundary_conditions=["Fixed inner and outer surface temperatures supplied by the user."],
    applicability="Thin homogeneous walls with known conductivity and surface temperatures.",
    validation_status="verified",
    validation_summary="Fourier's law, verified by unit tests against hand calculations. No experimental validation in this project.",
    limitations=["Multilayer insulation, radiation, internal heat sources and transients are not modelled.",
                 "The wall material and its conductivity must be supplied by the user; FIREWISE has no wall-material database."],
    references=["Fourier's law of heat conduction (e.g. Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 3)"],
)


def run_conduction(v):
    _check(CONDUCTION, v)
    q = v["conductivity_W_mK"] * (v["inner_temperature_K"] - v["outer_temperature_K"]) / v["thickness_m"]
    return {"heat_flux": q, "thermal_resistance": v["thickness_m"] / v["conductivity_W_mK"], "heat_rate": q * v["wall_area_m2"]}


# ------------------------------------------------------------------------------------------- planned (NOT implemented)
def _planned(id_, name, needs, data):
    return PhysicsModel(id=id_, name=name, version="—", equations=[], inputs=[], outputs=[], assumptions=[], boundary_conditions=[],
                        applicability="Not implemented.", validation_status="not_implemented",
                        validation_summary=f"Not implemented in v1. Would require: {needs}. Candidate validation data: {data}",
                        limitations=["No output is produced. FIREWISE does not predict flame behaviour."], references=[], implemented=False)


PLANNED = [
    _planned("droplet_combustion_d2", "Droplet combustion (quasi-steady d²-law)",
             "fuel and gas transport properties, flame-sheet assumptions, radiative-loss treatment",
             "FLEX (PSI-69) droplet initial diameter, burning-rate and extinction-diameter columns (units of the burning-rate column are unverified)."),
    _planned("flame_extinction", "Flame extinction limits", "detailed or reduced chemical kinetics and radiation models",
             "ACME Flame Design / CFI-G extinction and end-mode observations (PSI-10, PSI-159)."),
    _planned("flame_spread_solid", "Flame spread over solid materials", "pyrolysis and gas-phase kinetics, sample thermal properties",
             "Saffire (PSI-98/99/100) reported spread and burn lengths; BASS/BASS-II observations."),
    _planned("coupled_flow_combustion", "Coupled fluid flow and combustion (CFD)", "a validated CFD solver with combustion and radiation submodels",
             "Not available in PSI at the needed spatial resolution."),
]

REGISTRY = {m.id: m for m in (MIXTURE, IDEAL_GAS, AIRFLOW, CONVECTION, CONDUCTION)}
RUNNERS = {"gas_mixture": run_mixture, "ideal_gas": run_ideal_gas, "bulk_airflow": run_airflow,
           "forced_convection_flat_plate": run_convection, "wall_conduction": run_conduction}


def model_cards(include_planned=True):
    return [m.card() for m in REGISTRY.values()] + ([m.card() for m in PLANNED] if include_planned else [])


def get_card(model_id):
    m = REGISTRY.get(model_id) or next((p for p in PLANNED if p.id == model_id), None)
    return m and m.card()


# ------------------------------------------------------------------------------------------- engine
def _val(tv):
    return None if tv is None else tv.get("value")


def _status(tv):
    return "not_documented" if tv is None or tv.get("value") is None else tv.get("status", "user_defined")


def _execute(model_id, scope, inputs, provenance):
    m = REGISTRY[model_id]
    base = {"model_id": model_id, "model_name": m.name, "model_version": m.version, "scope": scope,
            "validation_status": m.validation_status, "assumptions": m.assumptions, "limitations": m.limitations,
            "inputs": [{"name": v.name, "value": inputs.get(v.name), "unit": v.unit,
                        "status": provenance.get(v.name, ("not_documented", None))[0] if inputs.get(v.name) is not None else "not_documented",
                        "source": provenance.get(v.name, (None, None))[1]} for v in m.inputs],
            "outputs": [], "warnings": [], "reason": None}
    try:
        out = RUNNERS[model_id](inputs)
    except Unavailable as e:
        return {**base, "status": "unavailable", "reason": "Missing inputs: " + ", ".join(e.args[0])}
    except Rejected as e:
        return {**base, "status": "rejected", "reason": "; ".join(e.args[0])}
    units = {v.name: v.unit for v in m.outputs}
    base["outputs"] = [{"name": k, "value": out[k], "unit": units[k], "status": "simulated",
                        "validation_status": m.output_validation.get(k, m.validation_status)} for k in units]
    base["status"] = "completed"
    if model_id == "bulk_airflow":
        base["warnings"].append(f"Flow regime (indicative): {out['_regime']}.")
    return base


def zone_geometry(env, scenario):
    """Zone volumes and wall areas from the user-defined cylinder and the environment's zone fractions."""
    D = _val(scenario["habitat"]["diameter_m"])
    L = _val(scenario["habitat"]["length_m"])
    A = math.pi * D * D / 4
    out = {}
    for z in env["zones"]:
        seg = (z["x_end"] - z["x_start"]) * L
        out[z["id"]] = {"length_m": seg, "volume_m3": A * seg, "wall_area_m2": math.pi * D * seg,
                        "x_start_m": z["x_start"] * L, "x_end_m": z["x_end"] * L}
    return out


def zone_state(scenario, zone_id):
    """Effective zone conditions with provenance: zone overrides fall back to habitat-level values."""
    zc = next((z for z in scenario.get("zones", []) if z["zone_id"] == zone_id), {}) or {}
    T = zc.get("temperature_K") or scenario["temperature_K"]
    o2 = zc.get("o2_pct") or scenario["composition"]["o2_pct"]
    flow = zc.get("airflow_m_s")
    return {"temperature_K": T, "o2_pct": o2, "airflow_m_s": flow,
            "temperature_scope": "zone" if zc.get("temperature_K") else "habitat",
            "o2_scope": "zone" if zc.get("o2_pct") else "habitat"}


def run_scenario(env, scenario):
    """Deterministic evaluation of every implemented model for a scenario. Returns results + metadata."""
    comp = scenario["composition"]
    p = scenario["pressure_kPa"]
    ar, co2 = comp.get("ar_pct"), comp.get("co2_pct")
    geo = zone_geometry(env, scenario)
    results = []
    zone_props = {}
    for z in env["zones"]:
        st = zone_state(scenario, z["id"])
        prov = {"pressure_kPa": (_status(p), p.get("source")), "temperature_K": (_status(st["temperature_K"]), st["temperature_K"].get("source")),
                "o2_mole_fraction": (_status(st["o2_pct"]), st["o2_pct"].get("source")),
                "ar_mole_fraction": (_status(ar) if ar else "user_defined", (ar or {}).get("source") or ("not specified: 0" if not ar else None)),
                "co2_mole_fraction": (_status(co2) if co2 else "user_defined", (co2 or {}).get("source") or ("not specified: 0" if not co2 else None))}
        mix_in = {"o2_mole_fraction": _pct(st["o2_pct"]), "ar_mole_fraction": _pct(ar) or 0.0, "co2_mole_fraction": _pct(co2) or 0.0,
                  "pressure_kPa": _val(p), "temperature_K": _val(st["temperature_K"])}
        rb = _execute("gas_mixture", f"zone:{z['id']}", mix_in, prov)
        results.append(rb)
        if rb["status"] != "completed":
            continue
        ob = {o["name"]: o["value"] for o in rb["outputs"]}
        ga_in = {"pressure_kPa": mix_in["pressure_kPa"], "temperature_K": mix_in["temperature_K"], "molar_mass_g_mol": ob["molar_mass"],
                 "o2_mole_fraction": mix_in["o2_mole_fraction"], "zone_volume_m3": geo[z["id"]]["volume_m3"]}
        ra = _execute("ideal_gas", f"zone:{z['id']}", ga_in, {**prov, "molar_mass_g_mol": ("simulated", "Model B"), "zone_volume_m3": ("derived", "habitat geometry")})
        results.append(ra)
        if ra["status"] == "completed":
            oa = {o["name"]: o["value"] for o in ra["outputs"]}
            zone_props[z["id"]] = {"density": oa["density"], "viscosity": ob["viscosity"] * 1e-6}
    # habitat bulk airflow uses the mean of zone densities/viscosities (volume-weighted)
    hab = scenario["habitat"]
    if zone_props:
        V = {zid: geo[zid]["volume_m3"] for zid in zone_props}
        tot = sum(V.values())
        rho = sum(zone_props[z]["density"] * V[z] for z in V) / tot
        mu = sum(zone_props[z]["viscosity"] * V[z] for z in V) / tot
    else:
        rho = mu = None
    vent = scenario["ventilation"]["volumetric_flow_m3_h"]
    af_in = {"diameter_m": _val(hab["diameter_m"]), "length_m": _val(hab["length_m"]), "ventilation_m3_h": _val(vent) or None,
             "density_kg_m3": rho, "viscosity_Pa_s": mu}
    rc = _execute("bulk_airflow", "habitat", af_in,
                  {"diameter_m": (_status(hab["diameter_m"]), None), "length_m": (_status(hab["length_m"]), None),
                   "ventilation_m3_h": (_status(vent), vent.get("source")), "density_kg_m3": ("simulated", "Model A, volume-weighted"),
                   "viscosity_Pa_s": ("simulated", "Model B, volume-weighted")})
    if _val(vent) == 0:
        rc = {**rc, "status": "unavailable", "reason": "Ventilation flow is 0 m³/h: no forced throughflow to characterise."}
    results.append(rc)
    # experiment convection
    exp = scenario["experiment"]
    st = zone_state(scenario, exp["zone_id"])
    cv_in = {"airflow_m_s": _val(st["airflow_m_s"]), "characteristic_length_m": _val(exp.get("characteristic_length_m")),
             "gas_temperature_K": _val(st["temperature_K"]), "surface_temperature_K": _val(exp.get("surface_temperature_K")),
             "pressure_kPa": _val(p), "o2_mole_fraction": _pct(st["o2_pct"]), "ar_mole_fraction": _pct(ar) or 0.0, "co2_mole_fraction": _pct(co2) or 0.0}
    rd = _execute("forced_convection_flat_plate", f"experiment:{exp['zone_id']}", cv_in,
                  {"airflow_m_s": (_status(st["airflow_m_s"]), (st["airflow_m_s"] or {}).get("source")),
                   "characteristic_length_m": (_status(exp.get("characteristic_length_m")), None),
                   "gas_temperature_K": (_status(st["temperature_K"]), None), "surface_temperature_K": (_status(exp.get("surface_temperature_K")), None),
                   "pressure_kPa": (_status(p), None), "o2_mole_fraction": (_status(st["o2_pct"]), None),
                   "ar_mole_fraction": ("user_defined", None), "co2_mole_fraction": ("user_defined", None)})
    if _val(st["airflow_m_s"]) == 0:
        rd = {**rd, "status": "unavailable", "reason": "Local airflow is 0 m/s: forced convection is absent. In microgravity, heat transfer is then by diffusion and radiation, which are not modelled."}
    if scenario["gravity"] != "microgravity" and rd["status"] == "completed":
        rd["warnings"].append("Buoyancy-driven convection exists at this gravity level and is NOT included; the result is the forced-convection component only.")
    results.append(rd)
    # wall conduction (experiment zone wall)
    w = scenario.get("wall") or {}
    wc_in = {"thickness_m": _val(w.get("thickness_m")), "conductivity_W_mK": _val(w.get("conductivity_W_mK")),
             "inner_temperature_K": _val(w.get("inner_temperature_K")), "outer_temperature_K": _val(w.get("outer_temperature_K")),
             "wall_area_m2": geo[exp["zone_id"]]["wall_area_m2"]}
    results.append(_execute("wall_conduction", f"zone:{exp['zone_id']}", wc_in,
                            {k: (_status(w.get(k)), None) for k in ("thickness_m", "conductivity_W_mK", "inner_temperature_K", "outer_temperature_K")}
                            | {"wall_area_m2": ("derived", "habitat geometry")}))
    payload = json.dumps(scenario_core(scenario), sort_keys=True, default=str)
    return {"engine_version": ENGINE_VERSION, "input_hash": hashlib.sha256(payload.encode()).hexdigest()[:16],
            "geometry": geo, "results": results, "planned_models": [m.card() for m in PLANNED],
            "notice": "Physics outputs are deterministic calculations from the stated inputs and assumptions. No combustion, ignition or flame-spread model is implemented; FIREWISE does not predict fire behaviour."}


def _pct(tv):
    v = _val(tv)
    return None if v is None else v / 100.0


def scenario_core(s):
    """The physically relevant part of a scenario (drops name/description/metadata) for hashing and comparison."""
    return {k: s.get(k) for k in ("habitat", "pressure_kPa", "temperature_K", "composition", "gravity", "ventilation", "zones", "experiment", "wall")}
