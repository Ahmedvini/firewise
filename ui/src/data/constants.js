// UI vocabulary only. Every number shown in FIREWISE comes from the API (build/firewise.sqlite);
// nothing in this file is data.

export const FUEL_LABEL = {
  gaseous: "Gaseous flame",
  liquid_droplet: "Liquid droplet",
  solid: "Solid material",
  solid_emulating_gas_burner: "Solid-emulating gas burner",
  smoke_source_nonflaming: "Smoke source (non-flaming)",
  dust_aerosol: "Dust aerosol",
  none: "Not a test",
};

// Data-series colours: validated categorical slots (dataviz palette check on #0f1522, all pairs:
// CVD ΔE 9.4, normal-vision ΔE 20.9, ≥3:1). The ember brand colour is reserved for UI chrome.
export const SERIES_COLOR = { gaseous: "#3987e5", liquid_droplet: "#d95926", solid: "#199e70" };

export const GRANULARITY_LABEL = {
  test: "Individual test",
  test_point: "Condition point within an ignition",
  test_day: "Test-day summary",
  test_day_o2_level: "Test-day × O₂ level",
  test_date: "Test-date summary",
  condition_envelope: "Design envelope",
  session: "Session",
  material_condition_set: "Material condition set",
  flow_visualization: "Flow visualization (not a burn)",
  figure_reference: "Publication figure reference",
};

export const STATUS_INFO = {
  measured: { label: "Measured", glyph: "●", tone: "green", desc: "Measured in a NASA flight test (PSI table)." },
  derived: { label: "Derived", glyph: "◆", tone: "green", desc: "Computed from measurements (e.g. O₂ from CO₂, adiabatic flame temperature)." },
  reported: { label: "Reported (approx.)", glyph: "◐", tone: "amber", desc: "Stated approximately or qualitatively in the PSI table." },
  specified: { label: "Set-point", glyph: "□", tone: "amber", desc: "Commanded set-point or design envelope — not a measurement." },
  missing: { label: "Not documented", glyph: "–", tone: "", desc: "Not documented in the PSI table. Never treated as zero." },
};

export const TIER_INFO = {
  measured: { label: "Measured evidence", glyph: "●", tone: "green", desc: "PSI tables, records or server-computed aggregates." },
  reported: { label: "Reported", glyph: "◐", tone: "amber", desc: "PSI record text or NASA reports." },
  literature: { label: "Literature", glyph: "▤", tone: "", desc: "Published sources outside PSI (URL-cited)." },
  interpretation: { label: "Interpretation", glyph: "◇", tone: "red", desc: "Reasoning over the evidence — not an experimental result." },
};

export const CONTEXT_LABEL = {
  ambient: "chamber atmosphere",
  burner_stream: "burner oxidizer stream",
  envelope: "design envelope",
  chamber: "chamber",
  forced_duct: "forced duct flow",
  coflow: "coflow",
  inlet: "inlet",
  quiescent: "quiescent",
  fan_setting_uncalibrated: "fan setting (uncalibrated)",
};

export const SUGGESTED_QUESTIONS = [
  "Which experiments document conditions in a 34% oxygen, 8.2 psia habitat atmosphere?",
  "Under what conditions did CFI-G produce cool flames?",
  "What evidence is there for partial-gravity combustion?",
  "What instrumentation was shared between SAME and DAFT?",
  "How do BASS and Saffire-III configurations differ?",
  "What is test 21265C3?",
];

export const COMPARE_PRESETS = [
  { label: "Flame Design vs CFI-G", ids: ["PSI-10", "PSI-159"] },
  { label: "FLEX vs CFI", ids: ["PSI-69", "PSI-39"] },
  { label: "BASS vs Saffire-III", ids: ["PSI-26", "PSI-100"] },
  { label: "DAFT vs SAME", ids: ["PSI-47", "PSI-102"] },
];
