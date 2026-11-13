"""Pydantic contract models (single source of truth; TypeScript types are generated from /openapi.json)."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["measured", "derived", "reported", "specified", "missing"]


class PsiaRange(BaseModel):
    min: float
    max: float


class Quantity(BaseModel):
    min: Optional[float]
    max: Optional[float]
    unit: Literal["pct", "atm", "cm_s"]
    status: Status
    status_label: str
    context: Optional[str]
    psia: Optional[PsiaRange] = None


class Provenance(BaseModel):
    row_key: str
    source_table_id: str
    source_file: str
    source_row: int
    source_sha256: str
    source_url: str
    psi_url: str
    evidence_id: str


class Observation(BaseModel):
    variable: str
    value_num: Optional[float]
    value_text: Optional[str]
    unit: Optional[str]
    status: Status
    status_label: str
    gravity_regime: str
    source_column: str
    evidence_id: str


class Flag(BaseModel):
    severity: Literal["anomaly", "limitation", "note"]
    code: str
    message: str


class Run(BaseModel):
    row_key: str
    investigation_id: str
    test_label: Optional[str]
    row_granularity: str
    duplicate_of: Optional[str]
    date_text: Optional[str]
    fuel_or_material: Optional[str]
    fuel_class: str
    fuel_class_detail: Optional[str]
    geometry: Optional[str]
    diluent: Optional[str]
    gravity_regime: str
    platform: str
    o2: Quantity
    pressure: Quantity
    flow: Quantity
    outcome_text: Optional[str]
    observations: list[Observation]
    flags: list[Flag]
    provenance: Provenance


class RunPage(BaseModel):
    items: list[Run]
    total: int
    limit: int
    offset: int


class BuildInfo(BaseModel):
    schema_version: int
    build_utc: str
    counts: dict[str, int]
    report_pages_indexed: int
    claims_check_sha256: str


class KeyCheck(BaseModel):
    valid: bool
    message: str
    model: str


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    build: Optional[BuildInfo]
    copilot_configured: bool = Field(description="A server-wide ANTHROPIC_API_KEY is configured (the key itself is never exposed)")
    copilot_model: str
    user_keys_accepted: bool = Field(default=True, description="Clients may send their own key per request in X-Anthropic-Key")


class Metric(BaseModel):
    value: Any
    description: str
    evidence_id: str


class KeyFinding(BaseModel):
    id: str
    title: str
    statement: str
    evidence_ids: list[str]
    tier: Literal["measured", "reported", "literature", "interpretation"]


class Summary(BaseModel):
    metrics: dict[str, Metric]
    by_fuel_class: dict[str, int]
    by_granularity: dict[str, int]
    by_data_class: dict[str, int]
    by_platform: dict[str, int]
    flags_by_severity: dict[str, int]
    documentation_by_fuel_class: dict[str, dict[str, int]]
    scenario_counts: dict[str, int]
    key_findings: list[KeyFinding]
    limitations: list[str]
    build: BuildInfo


class InvestigationCard(BaseModel):
    id: str
    acronym: Optional[str]
    title: str
    project_type: str
    platform: Optional[str]
    facility: Optional[str]
    insert_hw: Optional[str]
    data_class: Optional[str]
    fuel_classes: list[str]
    n_records: int
    n_unique_tests: int
    n_duplicates: int
    o2_ambient: Quantity
    pressure: Quantity
    flow: Quantity
    has_burner_stream_o2: bool
    n_publications: int
    n_anomalies: int
    psi_url: str
    doi_url: Optional[str]


class InvestigationPage(BaseModel):
    items: list[InvestigationCard]
    total: int
    limit: int
    offset: int


class TextField(BaseModel):
    value: Optional[str]
    evidence_id: str


class Publication(BaseModel):
    title: str
    authors: Optional[str]
    doi: Optional[str]
    status: Optional[str]


class Relation(BaseModel):
    src: str
    dst: str
    type: str
    status: Literal["verified", "inferred"]
    note: Optional[str]
    evidence_id: str


class Fact(BaseModel):
    id: str
    value: str
    tier: str
    source: str
    confidence: Optional[str]
    caveat: Optional[str]
    evidence_id: str


class DataProducts(BaseModel):
    n_files_listed: int
    listed_gb: float
    total_gb: float
    listing_complete: bool
    folders: dict[str, int]
    downloaded_files: int


class InvestigationDetail(InvestigationCard):
    hardware: Optional[str]
    sub_research_area: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    doi: Optional[str]
    license: Optional[str]
    objective: TextField
    hypothesis: TextField
    approach: TextField
    research_impacts: TextField
    publications: list[Publication]
    data_products: DataProducts
    flags_by_code: dict[str, int]
    granularity: dict[str, int]
    relations: list[Relation]
    curated_facts: list[Fact]
    source_tables: list[dict[str, Any]]


class InvestigationRuns(BaseModel):
    varying_columns: list[str]
    constant_columns: dict[str, Optional[str]]
    page: RunPage


class HistogramBin(BaseModel):
    lo: float
    hi: float
    n: int


class DistributionGroup(BaseModel):
    key: str
    n_documented: int
    n_missing: int
    status_counts: dict[str, int]
    histogram: list[HistogramBin]


class Distribution(BaseModel):
    variable: str
    unit: str
    o2_context: Optional[str]
    groups: list[DistributionGroup]


class Window(BaseModel):
    o2_min_pct: float = Field(ge=0, le=100)
    o2_max_pct: float = Field(ge=0, le=100)
    p_min_psia: float = Field(ge=0, le=100)
    p_max_psia: float = Field(ge=0, le=100)
    gravity: Literal["microgravity", "partial_gravity_lunar", "partial_gravity_mars", "normal_gravity", "any"] = "any"
    fuel_focus: Literal["any", "solid", "gaseous", "liquid_droplet", "smoke_source_nonflaming"] = "any"


class Scenario(BaseModel):
    id: str
    label: str
    description: str
    window: Window
    source: str
    gravity_evidence_records: int


class CountWithStatus(BaseModel):
    n: int
    o2_status: dict[str, int]
    p_status: dict[str, int]
    evidence_id: Optional[str] = None


class ScenarioItem(BaseModel):
    investigation_id: str
    acronym: Optional[str]
    in_window: CountWithStatus
    near_window: CountWithStatus
    undocumented: dict[str, int]
    records_considered: int
    material_class: list[str]
    material_match: bool
    gravity_match: str
    sample_row_keys: list[str]


class ScenarioEvidence(BaseModel):
    scenario: Scenario
    gravity_evidence: dict[str, Any]
    ranking_method: str
    near_window_tolerance: str
    label: str
    totals: dict[str, int]
    items: list[ScenarioItem]


class CompareFeature(BaseModel):
    name: str
    kind: Literal["categorical", "interval", "set", "count", "text"]
    values: dict[str, Any]
    comparable: bool
    similarity: Optional[float]
    note: Optional[str]


class Incompatibility(BaseModel):
    a: str
    b: str
    reason: str


class Comparison(BaseModel):
    investigations: list[InvestigationCard]
    features: list[CompareFeature]
    compared_on: str
    mean_similarity_on_comparable: Optional[float]
    incompatibilities: list[Incompatibility]
    relations: list[Relation]
    label: str


class GapCell(BaseModel):
    gravity_regime: str
    fuel_class: str
    o2_band: str
    p_band: str
    records: int
    investigations: dict[str, int]


class LiteratureOverlay(BaseModel):
    id: str
    label: str
    gravity_regime: str
    fuel_class: str
    o2_band: str
    p_band: str
    status: str
    evidence_id: str


class Gaps(BaseModel):
    dims: dict[str, list[str]]
    cells: list[GapCell]
    literature_overlays: list[LiteratureOverlay]
    definitions: dict[str, str]
    headline: list[KeyFinding]


class Evidence(BaseModel):
    evidence_id: str
    kind: str
    title: str
    text: Optional[str]
    url: Optional[str]
    data: Optional[dict[str, Any]] = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    scenario_id: Optional[str] = None
    twin: Optional["TwinAskContext"] = Field(default=None, description="Active Digital Twin scenario (shared state) for twin-aware answers")


class NumberRef(BaseModel):
    value: float
    unit: Optional[str] = None
    evidence_id: str


ClaimTier = Literal["measured", "reported", "literature", "interpretation", "calculation", "model_prediction", "unknown"]


class Claim(BaseModel):
    text: str
    tier: ClaimTier
    evidence_ids: list[str]


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: str
    title: str
    snippet: str
    url: Optional[str]


class AskResponse(BaseModel):
    status: Literal["answered", "insufficient_evidence", "partial"]
    mode: Literal["llm_validated", "deterministic", "evidence_only"]
    answer_summary: Optional[str]
    claims: list[Claim]
    limitations: list[str]
    gaps: list[str]
    related_investigations: list[str]
    evidence: list[EvidenceItem]
    notice: Optional[str]
    model: Optional[dict[str, str]]
    latency_ms: int
    cached: bool = False


class Points(BaseModel):
    fields: list[str]
    points: list[list[Any]]
    n_points: int
    n_records: int
    note: str


from .twin.schemas import TwinAskContext  # noqa: E402  (forward reference used by AskRequest)

AskRequest.model_rebuild()
