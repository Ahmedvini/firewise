// FIREWISE Digital Twin workspace.
// Layout: at-a-glance strip (environment · you set · NASA documents · calculated), then the main area
// (3D habitat or 2D engineering — same shared state) beside compact controls, then detail tabs.
import { Box, Gauge, FileSearch, Atom, FolderKanban, FileText, Sparkles, X, Save } from "lucide-react";
import { PageHeader, Tabs } from "../components/ui.jsx";
import ChatPanel from "../components/ChatPanel.jsx";
import ApiKeySettings, { CopilotModeLine } from "../components/ApiKeySettings.jsx";
import { useTwin, val } from "./TwinContext.jsx";
import ConfigPanel from "./ConfigPanel.jsx";
import HabitatScene, { OVERLAYS, RAMP, rampColor } from "./HabitatScene.jsx";
import EngineeringView from "./EngineeringView.jsx";
import EvidenceView from "./EvidenceView.jsx";
import PhysicsView from "./PhysicsView.jsx";
import ScenariosView from "./ScenariosView.jsx";
import ReportView from "./ReportView.jsx";
import { errorLines } from "../services/api.js";
import { TWIN_QUESTIONS } from "../data/constants.js";
import { TwinStatusTag } from "../components/Tags.jsx";

const MAIN = [["habitat", "3D habitat", Box], ["engineering", "2D engineering", Gauge]];
const DETAIL = [["evidence", "NASA evidence", FileSearch], ["physics", "Calculations", Atom], ["scenarios", "Scenarios", FolderKanban], ["report", "Report", FileText]];
export const TWIN_TABS = [...MAIN, ...DETAIL];

const out = (ph, mid, scope, name) => ph?.results.find((r) => r.model_id === mid && r.scope === scope && r.status === "completed")?.outputs.find((o) => o.name === name)?.value;

function Glance() {
  const t = useTwin();
  const d = t.evaluation.data;
  const sc = t.scenario;
  const z = sc.experiment.zone_id;
  const cov = d?.evidence.coverage;
  const po2 = out(d?.physics, "gas_mixture", `zone:${z}`, "o2_partial_pressure");
  const rho = out(d?.physics, "ideal_gas", `zone:${z}`, "density");
  const near = d?.evidence.nearest[0];
  const gravityLabel = { microgravity: "Microgravity", lunar: "Lunar gravity (0.16 g)", mars: "Mars gravity (0.38 g)", earth: "Earth gravity" }[sc.gravity];
  return (
    <div className="glance" aria-label="Scenario at a glance">
      <div className="g-cell">
        <span className="eyebrow">Environment</span>
        <b>{t.env?.name ?? "Habitat"}</b>
        <span className="small muted">{gravityLabel} · {val(sc.habitat.diameter_m)} m × {val(sc.habitat.length_m)} m</span>
      </div>
      <div className="g-cell">
        <span className="eyebrow">You set</span>
        <b className="tnum">{val(sc.composition.o2_pct)}% O₂ · {val(sc.pressure_kPa)?.toFixed(1)} kPa · {(val(sc.temperature_K) - 273.15).toFixed(1)} °C</b>
        <span><TwinStatusTag status={sc.pressure_kPa.status} source={sc.pressure_kPa.source} /></span>
      </div>
      <div className="g-cell">
        <span className="eyebrow">NASA documents</span>
        <b className="tnum">{cov ? `${cov.exact_matches} matching test${cov.exact_matches === 1 ? "" : "s"}` : "…"}</b>
        <span className="small muted">{near ? `closest: ${near.acronym || near.investigation_id} ${near.test_label || ""} (distance ${near.distance.toFixed(2)})` : "no comparable record"}{cov && cov.gravity.records_at_requested === 0 ? " · none at this gravity" : ""}</span>
      </div>
      <div className="g-cell">
        <span className="eyebrow">Calculated</span>
        <b className="tnum">{po2 != null ? `p(O₂) ${po2.toFixed(2)} kPa · ρ ${rho.toFixed(3)} kg/m³` : "…"}</b>
        <span><TwinStatusTag status="simulated" /> <span className="small faint">zone {z}, Models A/B</span></span>
      </div>
    </div>
  );
}

function HabitatView() {
  const t = useTwin();
  const d = t.evaluation.data;
  const zc = d?.zone_conditions ?? [];
  const ov = OVERLAYS[t.overlay];
  const vals = ov.get ? zc.map((z) => ov.get(z)).filter((v) => v != null) : [];
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const bulk = d?.physics.results.find((r) => r.model_id === "bulk_airflow" && r.status === "completed")?.outputs.find((o) => o.name === "bulk_velocity")?.value;
  const sel = zc.find((z) => z.zone_id === t.selectedZone);
  return (
    <div className="habitat">
      <div className="scene-toolbar">
        <div className="segmented" role="group" aria-label="Camera view">
          {[["iso", "3/4"], ["side", "Side"], ["top", "Top"], ["inside", "Inside"]].map(([k, l]) => <button key={k} className={t.camera === k ? "on" : ""} onClick={() => t.ui({ camera: k })} aria-pressed={t.camera === k}>{l}</button>)}
        </div>
        <label className="small">Colour zones by <select value={t.overlay} onChange={(e) => t.ui({ overlay: e.target.value })} aria-label="Environmental overlay">
          {Object.entries(OVERLAYS).map(([k, o]) => <option key={k} value={k}>{o.label}</option>)}</select></label>
        <label className="check small"><input type="checkbox" checked={t.showAirflow} onChange={(e) => t.ui({ showAirflow: e.target.checked })} /> Airflow</label>
        <label className="check small"><input type="checkbox" checked={t.cutaway} onChange={(e) => t.ui({ cutaway: e.target.checked })} /> Cutaway</label>
      </div>
      <div className="scene-wrap">
        <HabitatScene />
        <div className="scene-legend">
          {ov.get && (
            <div className="legend-line">
              <b>{ov.label}</b> <span className="tag amber">user-defined values</span>
              {vals.length ? <span className="legend-ramp">{lo.toFixed(1)}{RAMP.map((c) => <span key={c} className="sw" style={{ background: c }} />)}{hi.toFixed(1)} {ov.unit}{lo === hi ? " (all equal)" : ""}</span>
                : <span className="faint">no zone values set</span>}
            </div>
          )}
          {t.showAirflow && (
            <div className="legend-line small">
              {bulk ? <><b>Arrows</b> <span className="tag">illustrative direction</span> speed from Model C bulk velocity {bulk.toFixed(2)} cm/s <span className="tag blue">computed</span></>
                : "No forced ventilation computed (flow 0 or missing): no arrows."}
            </div>
          )}
        </div>
      </div>
      <div className="zone-strip" role="group" aria-label="Zones">
        {zc.map((z) => {
          const v = ov.get ? ov.get(z) : null;
          return (
            <button key={z.zone_id} className={`zone-chip ${z.zone_id === t.selectedZone ? "on" : ""}`} onClick={() => t.ui({ selectedZone: z.zone_id })} aria-pressed={z.zone_id === t.selectedZone}>
              <span className="sw" style={{ background: rampColor(v, lo, hi) ?? "transparent" }} /> <b>{z.zone_id}</b> <span className="small">{z.name}</span>
            </button>
          );
        })}
      </div>
      {sel && (
        <p className="small muted zone-line">
          <b>Zone {sel.zone_id}</b> · {sel.name}: O₂ {val(sel.o2_pct)}% ({sel.o2_scope}) · {(val(sel.temperature_K) - 273.15).toFixed(1)} °C ({sel.temperature_scope}) ·
          airflow {val(sel.airflow_m_s) == null ? "not set" : `${val(sel.airflow_m_s)} m/s`} — all user-defined. Drag to rotate, scroll to zoom, right-drag to pan; click a zone or sensor.
        </p>
      )}
    </div>
  );
}

export default function DigitalTwin({ tab = "habitat", onTab, onOpenExperiment }) {
  const t = useTwin();
  const main = MAIN.some(([k]) => k === tab) ? tab : t.mainView || "habitat";
  const detail = DETAIL.some(([k]) => k === tab) ? tab : t.detailTab || "evidence";
  const setMain = (k) => { t.ui({ mainView: k }); onTab(k); };
  const setDetail = (k) => { t.ui({ detailTab: k }); onTab(k); };
  const err = t.evaluation.error;
  return (
    <>
      <PageHeader eyebrow="Digital Twin" title={t.scenario?.name ?? "Digital Twin"}
        description="Configure a habitat cabin and see, in one place, what NASA has documented for it and what can be calculated."
        note="Values you set are user-defined, not measurements. NASA evidence keeps its own status. Calculations state their model and assumptions. No combustion model is implemented: FIREWISE does not predict fire behaviour or fire risk."
        actions={<>
          <span className={`tag ${t.dirty ? "amber" : "green"}`}>{t.savedId ? (t.dirty ? `v${t.savedVersion} · unsaved changes` : `saved v${t.savedVersion}`) : "not saved"}</span>
          {t.evaluation.loading && <span className="tag">updating…</span>}
          <button className="btn primary" disabled={t.saving || (t.savedId && !t.dirty)} onClick={() => t.save(false).catch(() => {})}><Save /> {t.savedId ? "Save" : "Save scenario"}</button>
          <button className="btn" onClick={() => t.ui({ copilotOpen: !t.copilotOpen })} aria-expanded={!!t.copilotOpen}><Sparkles /> Ask Copilot</button>
        </>} />
      {t.notice && <p className="note small">{t.notice}</p>}
      {err && (
        <div className="panel warn" role="alert">
          <b>{err.status === 422 ? "Invalid configuration" : "Evaluation failed"}:</b> {errorLines(err).join("; ") || err.message}
        </div>
      )}
      {!t.scenario || !t.env ? <div className="panel">Loading the habitat…</div> : (
        <>
          <Glance />
          <div className="twin-layout">
            <section className="twin-main">
              <div className="segmented main-switch" role="tablist" aria-label="Main view">
                {MAIN.map(([k, l, Icon]) => <button key={k} role="tab" aria-selected={main === k} className={main === k ? "on" : ""} onClick={() => setMain(k)}><Icon size={15} aria-hidden /> {l}</button>)}
              </div>
              {main === "habitat" ? <HabitatView /> : <EngineeringView />}
            </section>
            <aside className="twin-config" aria-label="Environmental configuration"><ConfigPanel /></aside>
          </div>
          <Tabs label="Details" value={detail} onChange={setDetail} items={DETAIL} />
          {detail === "evidence" && <EvidenceView />}
          {detail === "physics" && <PhysicsView />}
          {detail === "scenarios" && <ScenariosView />}
          {detail === "report" && <ReportView />}
        </>
      )}
      {t.copilotOpen && t.scenario && (
        <div className="twin-drawer" role="dialog" aria-label="Twin Copilot">
          <div className="row-between"><h3>Copilot · {t.scenario.name}</h3><button className="icon-btn" onClick={() => t.ui({ copilotOpen: false })} aria-label="Close Copilot"><X size={18} /></button></div>
          <p className="muted small">Answers use this scenario (zone {t.selectedZone}), its NASA evidence and the physics models, and say which parts are measurements, calculations or unknowns. <CopilotModeLine /></p>
          <div className="btn-row" style={{ marginBottom: 12 }}><ApiKeySettings /></div>
          <ChatPanel kind="twin" compact suggestions={TWIN_QUESTIONS} onOpenExperiment={onOpenExperiment}
            getContext={() => ({ scenario: t.scenario, selected_zone: t.selectedZone, scenario_id: t.savedId })}
            intro={<>Ask about this scenario: closest NASA experiments, missing variables, applicable models, what changes with pressure.</>} />
        </div>
      )}
    </>
  );
}
