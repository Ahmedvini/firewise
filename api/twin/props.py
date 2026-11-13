"""Pure-component gas data and mixture property functions used by the physics twin.

Every constant below is literature data, transcribed with its source. No parameter is fitted to
FIREWISE or NASA PSI data (there is no calibration set). Validation of these functions against
independent reference data is computed by api/twin/validation.py (docs/DIGITAL_TWIN_VALIDATION.md).

Units: SI throughout (K, Pa, kg/mol, Pa·s, W/(m·K), J/(mol·K)).
"""
import math

R_UNIVERSAL = 8.314462618  # J/(mol·K), CODATA 2018 (exact since the 2019 SI redefinition)
P_SEA_LEVEL = 101325.0     # Pa, standard atmosphere

# Molar masses, kg/mol (IUPAC standard atomic weights; N2 = 2 × 14.0067, O2 = 2 × 15.9994).
# Sutherland viscosity law mu = mu0 (T/T0)^1.5 (T0+S)/(T+S), T0 = 273 K: White, Viscous Fluid Flow, 3rd ed. (2006), Table 1-2.
# Sutherland-type conductivity law k = k0 (T/T0)^1.5 (T0+S)/(T+S), T0 = 273 K: White (2006), Table 1-3.
# NASA 7-coefficient cp/R polynomials, low-temperature range: GRI-Mech 3.0 thermodynamic data (thermo30.dat).
COMPONENTS = {
    "N2": {"M": 28.0134e-3, "mu0": 1.663e-5, "S_mu": 107.0, "k0": 0.0242, "S_k": 150.0,
           "nasa7": (3.298677, 1.4082404e-3, -3.963222e-6, 5.641515e-9, -2.444854e-12), "nasa7_range_K": (300.0, 1000.0)},
    "O2": {"M": 31.9988e-3, "mu0": 1.919e-5, "S_mu": 139.0, "k0": 0.0244, "S_k": 240.0,
           "nasa7": (3.78245636, -2.99673416e-3, 9.84730201e-6, -9.68129509e-9, 3.24372837e-12), "nasa7_range_K": (200.0, 1000.0)},
    "Ar": {"M": 39.948e-3, "mu0": 2.125e-5, "S_mu": 144.0, "k0": 0.0163, "S_k": 170.0,
           "nasa7": (2.5, 0.0, 0.0, 0.0, 0.0), "nasa7_range_K": (300.0, 1000.0)},
    "CO2": {"M": 44.0095e-3, "mu0": 1.370e-5, "S_mu": 222.0, "k0": 0.0146, "S_k": 1800.0,
            "nasa7": (2.35677352, 8.98459677e-3, -7.12356269e-6, 2.45919022e-9, -1.43699548e-13), "nasa7_range_K": (200.0, 1000.0)},
}
T0_SUTHERLAND = 273.0

SOURCES = {
    "R": "CODATA 2018 molar gas constant 8.314462618 J/(mol·K)",
    "M": "IUPAC standard atomic weights",
    "mu": "White, F. M., Viscous Fluid Flow, 3rd ed., McGraw-Hill, 2006, Table 1-2 (Sutherland viscosity law, ±2% over stated ranges)",
    "k": "White, F. M., Viscous Fluid Flow, 3rd ed., McGraw-Hill, 2006, Table 1-3 (Sutherland-type conductivity law, ±2% over stated ranges)",
    "cp": "GRI-Mech 3.0 thermodynamic data (NASA 7-coefficient polynomials), low-temperature range",
    "wilke": "Wilke, C. R., J. Chem. Phys. 18, 517 (1950): semi-empirical mixing rule for gas-mixture viscosity",
    "mason_saxena": "Mason, E. A. & Saxena, S. C., Phys. Fluids 1, 361 (1958): mixture conductivity with Wilke-form coefficients",
}


def sutherland(x0, S, T):
    return x0 * (T / T0_SUTHERLAND) ** 1.5 * (T0_SUTHERLAND + S) / (T + S)


def cp_molar(species, T):
    a = COMPONENTS[species]["nasa7"]
    return R_UNIVERSAL * (a[0] + a[1] * T + a[2] * T ** 2 + a[3] * T ** 3 + a[4] * T ** 4)


def normalize(fractions):
    """Mole fractions dict -> normalized dict (drops zero entries). Raises on unknown species or non-positive total."""
    bad = [s for s in fractions if s not in COMPONENTS]
    if bad:
        raise ValueError(f"no property data for species {bad}; supported: {sorted(COMPONENTS)}")
    tot = sum(v for v in fractions.values() if v > 0)
    if tot <= 0:
        raise ValueError("composition has no positive mole fractions")
    return {s: v / tot for s, v in fractions.items() if v > 0}


def molar_mass(x):
    return sum(xi * COMPONENTS[s]["M"] for s, xi in x.items())


def _phi(mu_i, mu_j, M_i, M_j):
    return (1 + (mu_i / mu_j) ** 0.5 * (M_j / M_i) ** 0.25) ** 2 / (8 * (1 + M_i / M_j)) ** 0.5


def mixture_viscosity(x, T):
    """Wilke (1950) mixing rule over Sutherland pure-component viscosities. Pa·s."""
    mu = {s: sutherland(COMPONENTS[s]["mu0"], COMPONENTS[s]["S_mu"], T) for s in x}
    M = {s: COMPONENTS[s]["M"] for s in x}
    return sum(x[i] * mu[i] / sum(x[j] * _phi(mu[i], mu[j], M[i], M[j]) for j in x) for i in x)


def mixture_conductivity(x, T):
    """Mason–Saxena (1958) form: Wassiljewa mixing with Wilke coefficients (built from viscosities). W/(m·K)."""
    mu = {s: sutherland(COMPONENTS[s]["mu0"], COMPONENTS[s]["S_mu"], T) for s in x}
    k = {s: sutherland(COMPONENTS[s]["k0"], COMPONENTS[s]["S_k"], T) for s in x}
    M = {s: COMPONENTS[s]["M"] for s in x}
    return sum(x[i] * k[i] / sum(x[j] * _phi(mu[i], mu[j], M[i], M[j]) for j in x) for i in x)


def mixture_cp_molar(x, T):
    return sum(xi * cp_molar(s, T) for s, xi in x.items())


def ideal_gas_density(p_Pa, T_K, M_kg_mol):
    return p_Pa * M_kg_mol / (R_UNIVERSAL * T_K)


def laminar_flat_plate_nu(Re, Pr):
    """Average Nusselt number, laminar flat plate, uniform surface temperature: Nu = 0.664 Re^1/2 Pr^1/3."""
    return 0.664 * math.sqrt(Re) * Pr ** (1.0 / 3.0)
