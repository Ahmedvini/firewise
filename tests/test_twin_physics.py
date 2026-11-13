"""Digital Twin physics: equations checked independently against hand calculations and reference values."""
import json
import math
import os

import pytest

from api.twin import physics, props, validation

R = 8.314462618


def mix(o2=0.21, ar=0.0, co2=0.0, p=101.325, T=300.0):
    return physics.run_mixture({"o2_mole_fraction": o2, "ar_mole_fraction": ar, "co2_mole_fraction": co2, "pressure_kPa": p, "temperature_K": T})


# ------------------------------------------------------------------------------------------- Model A
def test_ideal_gas_matches_hand_calculation_and_reference():
    out = physics.run_ideal_gas({"pressure_kPa": 101.325, "temperature_K": 288.15, "molar_mass_g_mol": 28.9644, "o2_mole_fraction": 0.209476, "zone_volume_m3": 2.0})
    assert out["density"] == pytest.approx(101325 * 0.0289644 / (R * 288.15), rel=1e-12)
    assert out["density"] == pytest.approx(1.2250, abs=5e-5)                       # U.S. Standard Atmosphere 1976 sea level
    c = 101325 / (R * 288.15)
    assert out["molar_concentration"] == pytest.approx(c, rel=1e-12)              # mol/m³
    assert out["o2_mass_concentration"] == pytest.approx(0.209476 * c * 31.9988, rel=1e-9)  # g/m³ (unit check: mol/m³ × g/mol)
    assert out["zone_gas_mass"] == pytest.approx(2 * out["density"], rel=1e-12)


def test_ideal_gas_scaling_units():
    base = {"pressure_kPa": 50.0, "temperature_K": 300.0, "molar_mass_g_mol": 29.0, "o2_mole_fraction": 0.3, "zone_volume_m3": 1.0}
    a = physics.run_ideal_gas(base)
    b = physics.run_ideal_gas({**base, "pressure_kPa": 100.0})
    c = physics.run_ideal_gas({**base, "temperature_K": 600.0})
    assert b["density"] == pytest.approx(2 * a["density"]) and c["density"] == pytest.approx(a["density"] / 2)


def test_out_of_range_is_rejected_and_missing_is_unavailable():
    with pytest.raises(physics.Rejected):
        physics.run_ideal_gas({"pressure_kPa": 101.3, "temperature_K": 50.0, "molar_mass_g_mol": 29.0, "o2_mole_fraction": 0.21, "zone_volume_m3": 1.0})
    with pytest.raises(physics.Unavailable) as e:
        physics.run_ideal_gas({"pressure_kPa": 101.3, "temperature_K": None, "molar_mass_g_mol": 29.0, "o2_mole_fraction": 0.21, "zone_volume_m3": 1.0})
    assert e.value.args[0] == ["temperature_K"]
    with pytest.raises(physics.Rejected):
        mix(o2=0.99, ar=0.03)  # fractions sum > 1
    with pytest.raises(ValueError):
        props.normalize({"He": 0.5, "O2": 0.5})  # no property data: never silently substituted


# ------------------------------------------------------------------------------------------- Model B
def test_dalton_and_molar_mass():
    out = mix(o2=0.34, p=56.54)
    assert out["o2_partial_pressure"] == pytest.approx(0.34 * 56.54, rel=1e-12)
    assert out["molar_mass"] == pytest.approx(0.34 * 31.9988 + 0.66 * 28.0134, rel=1e-12)
    assert out["o2_partial_pressure_vs_sea_level_air"] == pytest.approx(0.34 * 56.54 / (0.209476 * 101.325), rel=1e-12)


def test_heat_capacity_against_janaf():
    for sp, ref in (("N2", 29.124), ("O2", 29.376), ("Ar", 20.786), ("CO2", 37.135)):
        assert props.cp_molar(sp, 298.15) == pytest.approx(ref, rel=2.5e-3)
    out = mix(o2=0.21, T=300.0)
    assert out["gamma"] == pytest.approx(out["cp_molar"] / (out["cp_molar"] - R))
    assert 1.39 < out["gamma"] < 1.41  # diatomic gas near ambient


def test_wilke_reduces_to_pure_component_and_tracks_air():
    pure = props.mixture_viscosity({"N2": 1.0}, 300.0)
    assert pure == pytest.approx(props.sutherland(1.663e-5, 107.0, 300.0), rel=1e-12)
    air = props.normalize({"N2": 0.78084, "O2": 0.209476, "Ar": 0.00934, "CO2": 0.000314})
    for T in (250.0, 300.0, 350.0, 400.0):
        assert props.mixture_viscosity(air, T) == pytest.approx(props.sutherland(1.716e-5, 111.0, T), rel=0.02)
        assert props.mixture_conductivity(air, T) == pytest.approx(props.sutherland(0.0241, 194.0, T), rel=0.02)


def test_prandtl_consistent():
    out = mix()
    assert out["prandtl"] == pytest.approx(out["_cp_mass"] * out["_mu"] / out["_k"], rel=1e-12)
    assert 0.68 < out["prandtl"] < 0.74  # air near 300 K


# ------------------------------------------------------------------------------------------- Model C
def test_bulk_airflow_definitions():
    out = physics.run_airflow({"diameter_m": 4.0, "length_m": 10.0, "ventilation_m3_h": 3600.0, "density_kg_m3": 1.2, "viscosity_Pa_s": 1.8e-5})
    A = math.pi * 4.0
    assert out["cross_section_area"] == pytest.approx(A)
    assert out["bulk_velocity"] == pytest.approx(100 / A)                    # cm/s
    assert out["air_changes_per_hour"] == pytest.approx(3600 / (A * 10))
    assert out["residence_time"] == pytest.approx(A * 10 / 60)               # min
    assert out["reynolds_number_D"] == pytest.approx(1.2 * (1 / A) * 4.0 / 1.8e-5)


# ------------------------------------------------------------------------------------------- Model D
def test_forced_convection_correlation_and_rejection():
    v = {"airflow_m_s": 0.2, "characteristic_length_m": 0.1, "gas_temperature_K": 295.0, "surface_temperature_K": 345.0, "pressure_kPa": 101.325,
         "o2_mole_fraction": 0.21, "ar_mole_fraction": 0.0, "co2_mole_fraction": 0.0}
    out = physics.run_convection(v)
    m = mix(T=320.0)
    rho = props.ideal_gas_density(101325, 320.0, m["_M"])
    Re = rho * 0.2 * 0.1 / m["_mu"]
    Nu = 0.664 * Re ** 0.5 * m["prandtl"] ** (1 / 3)
    assert out["film_temperature"] == 320.0
    assert out["reynolds_number_L"] == pytest.approx(Re) and out["nusselt_number_L"] == pytest.approx(Nu)
    assert out["heat_transfer_coefficient"] == pytest.approx(Nu * m["_k"] / 0.1)
    assert out["heat_flux"] == pytest.approx(out["heat_transfer_coefficient"] * 50.0)
    with pytest.raises(physics.Rejected):  # turbulent range: the laminar correlation must not be used
        physics.run_convection({**v, "airflow_m_s": 5.0, "characteristic_length_m": 2.0, "pressure_kPa": 200.0})


def test_wall_conduction_fourier():
    out = physics.run_conduction({"thickness_m": 0.01, "conductivity_W_mK": 0.5, "inner_temperature_K": 295.0, "outer_temperature_K": 275.0, "wall_area_m2": 3.0})
    assert out["heat_flux"] == pytest.approx(1000.0) and out["thermal_resistance"] == pytest.approx(0.02) and out["heat_rate"] == pytest.approx(3000.0)


# ------------------------------------------------------------------------------------------- engine, metadata, validation
ENV = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "derived", "twin", "environments.json")))[0]


def scenario(**over):
    tv = lambda v: {"value": v, "status": "user_defined", "source": None}
    s = {"name": "t", "habitat": {"environment_id": "fwh-1", "diameter_m": tv(4.2), "length_m": tv(8.0)}, "pressure_kPa": tv(56.54),
         "temperature_K": tv(295.15), "composition": {"o2_pct": tv(34.0), "ar_pct": None, "co2_pct": None, "balance": "N2"}, "gravity": "microgravity",
         "ventilation": {"volumetric_flow_m3_h": tv(400.0), "direction": "+x"},
         "zones": [{"zone_id": "Z3", "temperature_K": None, "airflow_m_s": tv(0.1), "o2_pct": None}],
         "experiment": {"zone_id": "Z3", "slot_id": "rack-chamber", "fuel_class": "solid", "material": None,
                        "characteristic_length_m": tv(0.1), "surface_temperature_K": None}, "wall": None, "matching": {}}
    s.update(over)
    return s


def test_every_result_carries_units_assumptions_version_limitations():
    res = physics.run_scenario(ENV, scenario())
    assert res["engine_version"] and len(res["input_hash"]) == 16
    for r in res["results"]:
        assert r["model_version"] and r["assumptions"] and r["limitations"] and r["validation_status"] in ("verified", "validated")
        for o in r["outputs"]:
            assert o["unit"] and o["status"] == "simulated" and o["validation_status"] in ("verified", "validated")
        for i in r["inputs"]:
            assert i["unit"] and i["status"]
    by = {(r["model_id"], r["scope"]): r for r in res["results"]}
    assert by[("forced_convection_flat_plate", "experiment:Z3")]["status"] == "unavailable"  # no surface temperature -> never assumed
    assert "surface_temperature_K" in by[("forced_convection_flat_plate", "experiment:Z3")]["reason"]
    assert by[("wall_conduction", "zone:Z3")]["status"] == "unavailable"


def test_engine_gravity_and_zero_flow_handling():
    s = scenario(gravity="lunar")
    s["experiment"]["surface_temperature_K"] = {"value": 350.0, "status": "user_defined", "source": None}
    res = physics.run_scenario(ENV, s)
    conv = next(r for r in res["results"] if r["model_id"] == "forced_convection_flat_plate")
    assert conv["status"] == "completed" and any("Buoyancy" in w for w in conv["warnings"])
    s["zones"][0]["airflow_m_s"] = {"value": 0.0, "status": "user_defined", "source": None}
    s["ventilation"]["volumetric_flow_m3_h"] = {"value": 0.0, "status": "user_defined", "source": None}
    res = physics.run_scenario(ENV, s)
    st = {r["model_id"]: r for r in res["results"] if r["scope"] in ("habitat", "experiment:Z3")}
    assert st["forced_convection_flat_plate"]["status"] == "unavailable" and st["bulk_airflow"]["status"] == "unavailable"


def test_engine_is_deterministic():
    a, b = physics.run_scenario(ENV, scenario()), physics.run_scenario(ENV, scenario())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_planned_combustion_models_produce_nothing():
    cards = {c["id"]: c for c in physics.model_cards()}
    for mid in ("droplet_combustion_d2", "flame_extinction", "flame_spread_solid", "coupled_flow_combustion"):
        assert cards[mid]["validation_status"] == "not_implemented" and not cards[mid]["implemented"] and not cards[mid]["outputs"]
    assert mid not in physics.RUNNERS


def test_validation_records_are_reproducible_and_honest():
    stored, fresh = validation.load(), validation.compute()
    assert json.dumps(stored, sort_keys=True) == json.dumps(fresh, sort_keys=True), "run scripts/twin_validate.py"
    for r in fresh["records"]:
        if r["status"] == "validated":
            assert r["kind"] == "validation" and r["metrics"]["max_abs_rel_error_pct"] <= 2.0 and "Independent" in r["independence"]
        if r["kind"] == "verification" and r["metrics"]:
            assert "Not independent" in (r["independence"] or "Not independent") or r["model_id"] == "gas_mixture"
        if r["metrics"] is None:
            assert r["status"] in ("verified", "not_implemented")
        assert r["calibration_set"] in (None, "none (no fitted parameters)")
