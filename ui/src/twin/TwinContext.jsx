// ============================================================
// FIREWISE Digital Twin — the ONE authoritative scenario state.
// Every view (3D habitat, engineering dashboard, evidence, physics, scenarios, report, Copilot) reads
// the same `scenario` and the same server `evaluation` (POST /api/twin/evaluate), so they never disagree.
// Values the user edits become status "user_defined"; values imported from a NASA row keep NASA's status
// and source. Nothing is computed here: evidence and physics come from the backend.
// ============================================================
import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from "react";
import { twin } from "../services/api.js";

const Ctx = createContext(null);
export const useTwin = () => useContext(Ctx);

const DRAFT_KEY = "firewise.twin.draft";
export const tv = (value, source = null, status = "user_defined") => ({ value, status, source });
export const val = (t) => (t == null ? null : t.value);

// Client-side ranges mirror api/twin/schemas.py RANGES (the server re-validates and is authoritative).
export const RANGES = {
  diameter_m: [1, 10], length_m: [2, 30], pressure_kPa: [10, 200], temperature_K: [250, 350], o2_pct: [1, 100], ar_pct: [0, 5],
  co2_pct: [0, 5], ventilation: [0, 5000], airflow_m_s: [0, 5], characteristic_length_m: [0.001, 2], surface_temperature_K: [250, 900],
  thickness_m: [0.0005, 0.5], conductivity_W_mK: [0.01, 500], inner_temperature_K: [150, 400], outer_temperature_K: [3, 400],
};

function readDraft() {
  try { return JSON.parse(window.localStorage.getItem(DRAFT_KEY) || "null"); } catch { return null; }
}
function writeDraft(d) {
  try { window.localStorage.setItem(DRAFT_KEY, JSON.stringify(d)); } catch { /* storage blocked: state stays in memory */ }
}

const clone = (x) => JSON.parse(JSON.stringify(x));
const setIn = (obj, path, value) => {
  const out = clone(obj);
  let o = out;
  for (let i = 0; i < path.length - 1; i++) o = o[path[i]] ??= {};
  o[path[path.length - 1]] = value;
  return out;
};
const stripMeta = (s) => {
  const { id, version, created_at, updated_at, ...body } = s; // eslint-disable-line no-unused-vars
  return body;
};

const initial = (draft) => ({
  env: null, presets: [], scenario: draft?.scenario ?? null, savedId: draft?.savedId ?? null, savedVersion: draft?.savedVersion ?? null,
  dirty: draft?.dirty ?? false, selectedZone: draft?.selectedZone ?? "Z3", overlay: "o2", showAirflow: true, cutaway: true, camera: "iso",
  evaluation: { data: null, loading: false, error: null }, timeline: [], saving: false, notice: null,
});

function reducer(s, a) {
  switch (a.type) {
    case "env": return { ...s, env: a.env, presets: a.presets, scenario: s.scenario ?? clone(a.presets.find((p) => p.id === "exploration_atmosphere")?.scenario ?? a.presets[0].scenario) };
    case "set": return { ...s, scenario: setIn(s.scenario, a.path, a.value), dirty: true };
    case "zone": {
      const zones = clone(s.scenario.zones || []);
      let z = zones.find((x) => x.zone_id === a.zone);
      if (!z) { z = { zone_id: a.zone, temperature_K: null, airflow_m_s: null, o2_pct: null }; zones.push(z); }
      z[a.field] = a.value;
      return { ...s, scenario: { ...s.scenario, zones }, dirty: true };
    }
    case "replace": return { ...s, scenario: clone(a.scenario), savedId: a.savedId ?? null, savedVersion: a.savedVersion ?? null, dirty: !!a.dirty, notice: a.notice ?? null };
    case "saved": return { ...s, savedId: a.saved.id, savedVersion: a.saved.version, scenario: stripMeta(a.saved), dirty: false, saving: false, notice: a.notice };
    case "ui": return { ...s, ...a.patch };
    case "eval": return { ...s, evaluation: { ...s.evaluation, ...a.patch } };
    case "timeline": return { ...s, timeline: [...s.timeline, a.point].slice(-40) };
    default: return s;
  }
}

export function TwinProvider({ children }) {
  const [s, dispatch] = useReducer(reducer, undefined, () => initial(readDraft()));
  const evalSeq = useRef(0);

  // environment + presets (once)
  useEffect(() => {
    let live = true;
    twin.environments().then(async (envs) => {
      const env = envs[0];
      const presets = await twin.presets(env.id);
      if (live) dispatch({ type: "env", env, presets });
    }).catch((error) => live && dispatch({ type: "eval", patch: { error } }));
    return () => { live = false; };
  }, []);

  // per-viewer convenience: keep the working draft across reloads (never the source of truth for saved scenarios)
  useEffect(() => {
    if (s.scenario) writeDraft({ scenario: s.scenario, savedId: s.savedId, savedVersion: s.savedVersion, dirty: s.dirty, selectedZone: s.selectedZone });
  }, [s.scenario, s.savedId, s.savedVersion, s.dirty, s.selectedZone]);

  // shared evaluation: debounced, abortable, last-request-wins
  useEffect(() => {
    if (!s.scenario || !s.env) return undefined;
    const controller = new AbortController();
    const seq = ++evalSeq.current;
    const t = setTimeout(() => {
      dispatch({ type: "eval", patch: { loading: true } });
      twin.evaluate(s.scenario, controller.signal).then((data) => {
        if (seq !== evalSeq.current) return;
        dispatch({ type: "eval", patch: { data, loading: false, error: null } });
        const z = data.zone_conditions.find((x) => x.zone_id === s.scenario.experiment.zone_id);
        dispatch({ type: "timeline", point: { t: new Date().toLocaleTimeString(), o2: val(z?.o2_pct), pressure: val(s.scenario.pressure_kPa),
          temperature: val(z?.temperature_K), airflow: val(z?.airflow_m_s), exact: data.evidence.coverage.exact_matches } });
      }).catch((error) => {
        if (error.name === "AbortError" || seq !== evalSeq.current) return;
        dispatch({ type: "eval", patch: { loading: false, error } });
      });
    }, 350);
    return () => { clearTimeout(t); controller.abort(); };
  }, [s.scenario, s.env]);

  const api = useMemo(() => ({
    set: (path, value) => dispatch({ type: "set", path, value }),
    setValue: (path, value, unitSource) => dispatch({ type: "set", path, value: value === null || value === "" || Number.isNaN(value) ? null : tv(Number(value), unitSource ?? null) }),
    setZone: (zone, field, value) => dispatch({ type: "zone", zone, field, value: value === null || value === "" ? null : tv(Number(value)) }),
    ui: (patch) => dispatch({ type: "ui", patch }),
    loadPreset: (id) => {
      const p = s.presets.find((x) => x.id === id);
      if (p) dispatch({ type: "replace", scenario: p.scenario, dirty: true, notice: `Loaded preset “${p.scenario.name}” (unsaved).` });
    },
    importRecord: (rec) => {
      // copy documented NASA values with their NASA status and source row; missing stays missing
      let sc = clone(s.scenario);
      const map = { o2_pct: ["composition", "o2_pct"], pressure_kPa: ["pressure_kPa"] };
      const nasa = (k) => ({ measured: "measured", derived: "derived", reported: "reported", specified: "specified" }[rec.values[k].status] ?? "not_documented");
      for (const [k, path] of Object.entries(map)) {
        const v = rec.values[k];
        if (v.value != null) sc = setIn(sc, path, { value: Number(v.value.toFixed(4)), status: nasa(k), source: rec.evidence_id });
      }
      const f = rec.values.airflow_m_s;
      if (f.value != null) {
        const zones = sc.zones || [];
        const z = zones.find((x) => x.zone_id === sc.experiment.zone_id) || (zones.push({ zone_id: sc.experiment.zone_id }), zones[zones.length - 1]);
        z.airflow_m_s = { value: f.value, status: nasa("airflow_m_s"), source: rec.evidence_id };
        sc.zones = zones;
      }
      sc.experiment.fuel_class = rec.fuel_class === "solid_emulating_gas_burner" || rec.fuel_class === "dust_aerosol" ? sc.experiment.fuel_class : rec.fuel_class;
      dispatch({ type: "replace", scenario: sc, savedId: s.savedId, savedVersion: s.savedVersion, dirty: true,
        notice: `Imported documented conditions from ${rec.acronym || rec.investigation_id} test ${rec.test_label || ""} (${rec.evidence_id}); undocumented values were left unchanged.` });
    },
    save: async (asNew = false, note) => {
      dispatch({ type: "ui", patch: { saving: true } });
      try {
        const saved = !asNew && s.savedId ? await twin.update(s.savedId, s.scenario, note) : await twin.create(s.scenario);
        dispatch({ type: "saved", saved, notice: `Saved “${saved.name}” as version ${saved.version}.` });
        return saved;
      } catch (error) {
        dispatch({ type: "ui", patch: { saving: false, notice: null } });
        dispatch({ type: "eval", patch: { error } });
        throw error;
      }
    },
    load: async (id) => {
      const sc = await twin.get(id);
      dispatch({ type: "replace", scenario: stripMeta(sc), savedId: sc.id, savedVersion: sc.version, dirty: false, notice: `Loaded “${sc.name}” (version ${sc.version}).` });
    },
    newScenario: () => {
      const p = s.presets.find((x) => x.id === "sea_level_air") ?? s.presets[0];
      dispatch({ type: "replace", scenario: { ...p.scenario, name: "New scenario" }, dirty: true, notice: "New unsaved scenario." });
    },
    loadVersion: (scenario, version) => dispatch({ type: "replace", scenario, savedId: s.savedId, savedVersion: s.savedVersion, dirty: true,
      notice: `Restored the configuration of version ${version} (unsaved until you save).` }),
    detach: () => dispatch({ type: "replace", scenario: s.scenario, dirty: true }),
  }), [s.presets, s.scenario, s.savedId, s.savedVersion]);

  return <Ctx.Provider value={{ ...s, ...api }}>{children}</Ctx.Provider>;
}
