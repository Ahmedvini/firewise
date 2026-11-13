// ALL VALUES IN THIS FILE ARE PLACEHOLDERS.
// Replace them with the real NASA PSI dataset later (keep the same field names,
// or update the pages that use them). A value of null means "not in dataset".

export const EXPERIMENTS = [
  { id: "bass", name: "BASS", program: "BASS", year: 2003, type: "Droplet / solid-fuel burning", fuel: "Placeholder fuel A", category: "Flame structure",
    oxygenPercent: 21, airflowCmS: 0, burnSeconds: 60, peakTempK: null,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: pressure, atmosphere and ignition details.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "bass2", name: "BASS-II", program: "BASS", year: 2008, type: "Droplet / solid-fuel burning", fuel: "Placeholder fuel A", category: "Flame structure",
    oxygenPercent: 25, airflowCmS: 5, burnSeconds: 90, peakTempK: 1450,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: pressure, atmosphere and ignition details.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "saffire1", name: "Saffire-I", program: "Saffire", year: 2016, type: "Large-scale flame spread", fuel: "Placeholder material B", category: "Spacecraft fire safety",
    oxygenPercent: 21, airflowCmS: 20, burnSeconds: 300, peakTempK: null,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: flow, sample geometry, vehicle.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "saffire3", name: "Saffire-III", program: "Saffire", year: 2017, type: "Large-scale flame spread", fuel: "Placeholder material B", category: "Spacecraft fire safety",
    oxygenPercent: 25, airflowCmS: 25, burnSeconds: 300, peakTempK: 900,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: flow, sample geometry, vehicle.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "flex", name: "FLEX", program: "FLEX", year: 2009, type: "Droplet combustion", fuel: "Placeholder fuel C", category: "Flame structure",
    oxygenPercent: 21, airflowCmS: 0, burnSeconds: 45, peakTempK: null,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: chamber and diluent details.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "flex2", name: "FLEX-2", program: "FLEX", year: 2012, type: "Droplet combustion", fuel: "Placeholder fuel C", category: "Flame structure",
    oxygenPercent: 18, airflowCmS: 0, burnSeconds: 70, peakTempK: 1100,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: chamber and diluent details.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
  { id: "acme", name: "ACME", program: "ACME", year: 2018, type: "Gaseous diffusion flame", fuel: "Placeholder gas D", category: "Combustion behavior",
    oxygenPercent: 21, airflowCmS: 10, burnSeconds: 120, peakTempK: 1300,
    objective: "Placeholder: objective text from the dataset will appear here.",
    conditions: "Placeholder: burner, flow and ambient details.",
    observations: "Placeholder: key observations from the source documents.", sources: [] },
];

// Number of indexed documents. null = "not connected yet".
export const DOCUMENT_COUNT = null;

export const FEATURED_EXPERIMENT_IDS = ["bass2", "saffire1", "flex2", "acme"];

export const SUGGESTED_QUESTIONS = [
  "How does microgravity affect flame shape?",
  "What did the Saffire experiments investigate?",
  "How does oxygen concentration influence combustion?",
  "What are the fire safety implications for spacecraft?",
];

// Parameters shown on the Compare page
export const COMPARE_PARAMETERS = [
  { key: "oxygenPercent", label: "Oxygen concentration (%)" },
  { key: "airflowCmS", label: "Airflow (cm/s)" },
  { key: "burnSeconds", label: "Burning duration (s)" },
  { key: "peakTempK", label: "Peak temperature (K)" },
];

export const STATUS_LABELS = {
  established: "Established finding",
  possible: "Possible implication",
  research: "More research needed",
};

export const INSIGHTS = [
  { id: "i1", section: "Spacecraft", status: "established", title: "Flame shape can differ without buoyancy",
    observation: "Placeholder wording: without buoyant convection, flame shape and spread can differ from flames on Earth.",
    whyItMatters: "Fire safety assumptions based on Earth flames may need review.", related: ["BASS", "FLEX"] },
  { id: "i2", section: "Spacecraft", status: "possible", title: "Detection assumptions may not transfer",
    observation: "Possible implication: smoke and heat patterns may differ in microgravity.",
    whyItMatters: "Detector placement and response could depend on how fires develop.", related: ["Saffire-I"] },
  { id: "i3", section: "International Space Station", status: "possible", title: "Material flammability depends on ventilation",
    observation: "Placeholder wording: airflow conditions can change how a material burns.",
    whyItMatters: "Station ventilation may affect how a fire would spread.", related: ["Saffire-III"] },
  { id: "i4", section: "Lunar habitats", status: "research", title: "Partial-gravity behavior is unconfirmed",
    observation: "Lunar gravity lies between Earth and microgravity, but no experiment in this dataset tests it.",
    whyItMatters: "Lunar fire safety cannot be inferred from microgravity data alone.", related: [] },
  { id: "i5", section: "Mars habitats and rovers", status: "research", title: "Mars-gravity combustion is unconfirmed",
    observation: "Conclusions for Martian habitats and rovers cannot be drawn from microgravity data alone.",
    whyItMatters: "Habitat and rover designs need evidence from partial-gravity tests.", related: [] },
];
