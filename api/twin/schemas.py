"""Pydantic schemas for the Digital Twin (request/response contracts, validation rules).

Canonical units: O₂/Ar/CO₂ in mole %, pressure in kPa, temperature in K, airflow in m/s,
ventilation in m³/h, lengths in m. Every configurable value is a TwinValue carrying its status
and provenance; a value of null means "not documented / not set" and is never treated as zero.
"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

ValueStatus = Literal["user_defined", "measured", "derived", "reported", "specified", "simulated", "not_documented"]
Gravity = Literal["microgravity", "lunar", "mars", "earth"]
FuelClass = Literal["solid", "gaseous", "liquid_droplet", "smoke_source_nonflaming", "solid_emulating_gas_burner"]

# field path -> (min, max, unit). Applied to TwinValue.value when not null.
RANGES = {
    "habitat.diameter_m": (1.0, 10.0, "m"), "habitat.length_m": (2.0, 30.0, "m"),
    "pressure_kPa": (10.0, 200.0, "kPa"), "temperature_K": (250.0, 350.0, "K"),
    "composition.o2_pct": (1.0, 100.0, "%"), "composition.ar_pct": (0.0, 5.0, "%"), "composition.co2_pct": (0.0, 5.0, "%"),
    "ventilation.volumetric_flow_m3_h": (0.0, 5000.0, "m³/h"),
    "zones.temperature_K": (250.0, 350.0, "K"), "zones.airflow_m_s": (0.0, 5.0, "m/s"), "zones.o2_pct": (1.0, 100.0, "%"),
    "experiment.characteristic_length_m": (0.001, 2.0, "m"), "experiment.surface_temperature_K": (250.0, 900.0, "K"),
    "wall.thickness_m": (0.0005, 0.5, "m"), "wall.conductivity_W_mK": (0.01, 500.0, "W/(m·K)"),
    "wall.inner_temperature_K": (150.0, 400.0, "K"), "wall.outer_temperature_K": (3.0, 400.0, "K"),
}


class TwinValue(BaseModel):
    value: Optional[float] = None
    status: ValueStatus = "user_defined"
    source: Optional[str] = Field(default=None, max_length=200, description="evidence id (e.g. row:...) or a short note")


class Habitat(BaseModel):
    environment_id: str = Field(min_length=1, max_length=40)
    diameter_m: TwinValue
    length_m: TwinValue


class Composition(BaseModel):
    o2_pct: TwinValue
    ar_pct: Optional[TwinValue] = None
    co2_pct: Optional[TwinValue] = None
    balance: Literal["N2"] = "N2"


class ZoneConditions(BaseModel):
    zone_id: str = Field(min_length=1, max_length=20)
    temperature_K: Optional[TwinValue] = None
    airflow_m_s: Optional[TwinValue] = None
    o2_pct: Optional[TwinValue] = None


class Experiment(BaseModel):
    zone_id: str = Field(min_length=1, max_length=20)
    slot_id: Optional[str] = Field(default=None, max_length=40)
    fuel_class: Optional[FuelClass] = None
    material: Optional[str] = Field(default=None, max_length=60)
    characteristic_length_m: Optional[TwinValue] = None
    surface_temperature_K: Optional[TwinValue] = None


class Ventilation(BaseModel):
    volumetric_flow_m3_h: TwinValue
    direction: Literal["+x", "-x"] = "+x"


class Wall(BaseModel):
    thickness_m: Optional[TwinValue] = None
    conductivity_W_mK: Optional[TwinValue] = None
    inner_temperature_K: Optional[TwinValue] = None
    outer_temperature_K: Optional[TwinValue] = None
    material_label: Optional[str] = Field(default=None, max_length=60)


class Matching(BaseModel):
    o2_tolerance_pts: float = Field(default=2.0, ge=0.1, le=20.0)
    pressure_tolerance_kPa: float = Field(default=6.89, ge=0.5, le=50.0)
    airflow_tolerance_m_s: float = Field(default=0.05, ge=0.005, le=1.0)
    use_pressure: bool = True
    use_airflow: bool = False
    use_material: bool = False
    use_temperature: bool = False


class ScenarioIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    habitat: Habitat
    pressure_kPa: TwinValue
    temperature_K: TwinValue
    composition: Composition
    gravity: Gravity = "microgravity"
    ventilation: Ventilation
    zones: list[ZoneConditions] = Field(default_factory=list, max_length=20)
    experiment: Experiment
    wall: Optional[Wall] = None
    matching: Matching = Field(default_factory=Matching)

    @model_validator(mode="after")
    def _ranges(self):
        errs = []

        def chk(path, tv, required=False):
            if tv is None or tv.value is None:
                if required:
                    errs.append(f"{path}: a value is required")
                return
            lo, hi, unit = RANGES[path if not path.startswith("zones[") else "zones." + path.split(".", 1)[1]]
            if not lo <= tv.value <= hi:
                errs.append(f"{path} = {tv.value:g} {unit} is outside the allowed range [{lo:g}, {hi:g}] {unit}")

        chk("habitat.diameter_m", self.habitat.diameter_m, True)
        chk("habitat.length_m", self.habitat.length_m, True)
        chk("pressure_kPa", self.pressure_kPa, True)
        chk("temperature_K", self.temperature_K, True)
        chk("composition.o2_pct", self.composition.o2_pct, True)
        chk("composition.ar_pct", self.composition.ar_pct)
        chk("composition.co2_pct", self.composition.co2_pct)
        chk("ventilation.volumetric_flow_m3_h", self.ventilation.volumetric_flow_m3_h, True)
        for i, z in enumerate(self.zones):
            for f in ("temperature_K", "airflow_m_s", "o2_pct"):
                chk(f"zones[{i}].{f}", getattr(z, f))
        chk("experiment.characteristic_length_m", self.experiment.characteristic_length_m)
        chk("experiment.surface_temperature_K", self.experiment.surface_temperature_K)
        if self.wall:
            for f in ("thickness_m", "conductivity_W_mK", "inner_temperature_K", "outer_temperature_K"):
                chk(f"wall.{f}", getattr(self.wall, f))
        tot = sum(tv.value for tv in (self.composition.o2_pct, self.composition.ar_pct, self.composition.co2_pct) if tv and tv.value is not None)
        if tot > 100.0 + 1e-9:
            errs.append(f"O₂ + Ar + CO₂ = {tot:g}% exceeds 100%")
        ids = [z.zone_id for z in self.zones]
        if len(ids) != len(set(ids)):
            errs.append("zones: each zone_id may appear only once")
        if errs:
            raise ValueError("; ".join(errs))
        return self


class Scenario(ScenarioIn):
    id: str
    version: int
    created_at: str
    updated_at: str


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    version: int
    updated_at: str
    environment_id: str
    o2_pct: Optional[float]
    pressure_kPa: Optional[float]
    gravity: str


class ScenarioVersion(BaseModel):
    version: int
    created_at: str
    note: Optional[str]
    o2_pct: Optional[float]
    pressure_kPa: Optional[float]
    temperature_K: Optional[float]
    ventilation_m3_h: Optional[float]
    scenario: dict[str, Any]


class CompareRequest(BaseModel):
    ids: list[str] = Field(min_length=2, max_length=4)


class EvaluateRequest(BaseModel):
    scenario: ScenarioIn
    nearest_limit: int = Field(default=20, ge=1, le=100)


class TwinAskContext(BaseModel):
    scenario: ScenarioIn
    selected_zone: Optional[str] = Field(default=None, max_length=20)
    scenario_id: Optional[str] = Field(default=None, max_length=40)


class SimulationRun(BaseModel):
    run_id: str
    scenario_id: str
    scenario_version: int
    status: Literal["queued", "running", "completed", "failed"]
    engine_version: str
    input_hash: str
    created_at: str
    completed_at: Optional[str]
    summary: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
