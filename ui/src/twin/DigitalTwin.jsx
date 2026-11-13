// FIREWISE Digital Twin workspace: one shared scenario state, six views, plus the twin-aware Copilot.
import { Box, Gauge, FileSearch, Atom, FolderKanban, FileText, Sparkles, X, Save } from "lucide-react";
import Header from "../components/Header.jsx";
import SampleBanner from "../components/SampleBanner.jsx";
import ChatPanel from "../components/ChatPanel.jsx";
import { useTwin } from "./TwinContext.jsx";
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
import { val } from "./TwinContext.jsx";

export const TWIN_TABS = [
  ["habitat", "Habitat", Box], ["engineering", "Engineering", Gauge], ["evidence", "Evidence", FileSearch],
  ["physics", "Physics", Atom], ["scenarios", "Scenarios", FolderKanban], ["report", "Report", FileText],
];

function HabitatView() {
  const t = useTwin();
  const d = t.evaluation.data;
  const zc = d?.zone_conditions ?? [];
  const ov = OVERLAYS[t.overlay];
  const vals = ov.get ? zc.map((z) => ov.get(z)).filter((v) => v != null) : [];
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const sel = zc.find((z) => z.zone_id === t.selectedZone);
  const bulk = d?.physics.results.find((r) => r.model_id === "bulk_airflow" && r.status === "completed")?.outputs.find((o) => o.name === "bulk_velocity")?.value;
  const zoneName = t.env?.zones.find((z) => z.id === t.selectedZone)?.name;
  return (
    <div className="habitat">
      <div className="scene-toolbar">
        <div className="segmented" role="group" aria-label="Camera view">
          {[["iso", "3/4"], ["side", "Side"], ["top", "Top"], ["inside", "Inside"]].map(([k, l]) => <button key={k} className={t.camera === k ? "on" : ""} onClick={() => t.ui({ camera: k })} aria-pressed={t.camera === k}>{l}</button>)}
        </div>
        <label className="small">Overlay <select value={t.overlay} onChange={(e) => t.ui({ overlay: e.target.value })} aria-label="Environmental overlay">
          {Object.entries(OVERLAYS).map(([k, o]) => <option key={k} value={k}>{o.label}</option>)}</select></label>
        <label className="check small"><input type="checkbox" checked={t.showAirflow} onChange={(e) => t.ui({ showAirflow: e.target.checked })} /> Airflow</label>
        <label className="check small"><input type="checkbox" checked={t.cutaway} onChange={(e) => t.ui({ cutaway: e.target.checked })} /> Cutaway</label>
      </div>
      <div className="scene-wrap">
        <HabitatScene />
        <div className="scene-legend">
          {ov.get && (
            <div className="legend-line">
              <b>Zone colour: {ov.label}</b> <span className="tag amber">user-defined values</span>
              {vals.length ? <span className="legend-ramp">{lo.toFixed(1)}{RAMP.map((c) => <span key={c} className="sw" style={{ background: c }} />)}{hi.toFixed(1)} {ov.unit}{lo === hi ? " (all zones equal)" : ""}</span>
                : <span className="muted">no zone values set</span>}
            </div>
          )}
          {t.showAirflow && (
            <div className="legend-line small">
              {bulk ? <><b>Arrows:</b> <span className="tag">illustrative direction</span> speed from Model C bulk velocity {bulk.toFixed(2)} cm/s <span className="tag blue">computed</span> uniform, not a flow field</>
                : "No forced ventilation computed (flow 0 or missing): no arrows."}
            </div>
          )}
          <div className="legend-line small muted">Drag to rotate · scroll to zoom · right-drag to pan · click a zone or sensor to select</div>
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
        <div className="grid cols-4 section-gap">
          <div className="panel stat-tile"><span className="eyebrow">Zone {sel.zone_id} · O₂</span><strong>{val(sel.o2_pct)}%</strong><span className="muted small">{sel.o2_scope}-level value</span><TwinStatusTag status={sel.o2_pct.status} source={sel.o2_pct.source} /></div>
          <div className="panel stat-tile"><span className="eyebrow">Pressure</span><strong>{val(sel.pressure_kPa)?.toFixed(2)} kPa</strong><span className="muted small">habitat-wide</span><TwinStatusTag status={sel.pressure_kPa.status} source={sel.pressure_kPa.source} /></div>
          <div className="panel stat-tile"><span className="eyebrow">Temperature</span><strong>{(val(sel.temperature_K) - 273.15).toFixed(1)} °C</strong><span className="muted small">{sel.temperature_scope}-level value</span><TwinStatusTag status={sel.temperature_K.status} /></div>
          <div className="panel stat-tile"><span className="eyebrow">Local airflow</span><strong>{val(sel.airflow_m_s) == null ? "not set" : `${val(sel.airflow_m_s)} m/s`}</strong><span className="muted small">{zoneName}</span><TwinStatusTag status={val(sel.airflow_m_s) == null ? "not_documented" : sel.airflow_m_s.status} /></div>
        </div>
      )}
    </div>
  );
}

export default function DigitalTwin({ tab = "habitat", onTab, onOpenExperiment }) {
  const t = useTwin();
  const view = TWIN_TABS.some(([k]) => k === tab) ? tab : "habitat";
  const err = t.evaluation.error;
  return (
    <>
      <SampleBanner>
        Digital Twin of a generic habitat module. Configured values are <b>user-defined</b> (not measurements); NASA evidence keeps its own status; physics outputs are deterministic model calculations with stated assumptions.
        No combustion model is implemented — FIREWISE does not predict fire behaviour or fire risk.
      </SampleBanner>
      <div className="twin-head">
        <Header eyebrow="Digital Twin" title={t.scenario?.name ?? "Digital Twin"} description={t.scenario?.description || "Configure the cabin environment; every view below reflects the same scenario."} />
        <div className="btn-row twin-actions">
          <span className={`tag ${t.dirty ? "amber" : "green"}`}>{t.savedId ? (t.dirty ? `v${t.savedVersion} · unsaved changes` : `saved v${t.savedVersion}`) : "not saved"}</span>
          {t.evaluation.loading && <span className="tag">updating…</span>}
          <button className="btn primary" disabled={t.saving || (t.savedId && !t.dirty)} onClick={() => t.save(false).catch(() => {})}><Save size={15} /> {t.savedId ? "Save" : "Save scenario"}</button>
          <button className="btn" onClick={() => t.ui({ copilotOpen: !t.copilotOpen })} aria-expanded={!!t.copilotOpen}><Sparkles size={15} /> Ask Copilot</button>
        </div>
      </div>
      {t.notice && <p className="note small">{t.notice}</p>}
      {err && (
        <div className="panel warn" role="alert">
          <b>{err.status === 422 ? "Invalid configuration" : "Evaluation failed"}:</b> {errorLines(err).join("; ") || err.message}
        </div>
      )}
      <div className="twin-layout">
        <aside className="twin-config panel" aria-label="Environmental configuration"><ConfigPanel /></aside>
        <section className="twin-main">
          <div className="tabs twin-tabs" role="tablist">
            {TWIN_TABS.map(([k, l, Icon]) => (
              <button key={k} role="tab" aria-selected={view === k} className={view === k ? "on" : ""} onClick={() => onTab(k)}><Icon size={15} /> {l}</button>
            ))}
          </div>
          {!t.scenario || !t.env ? <div className="panel">Loading the habitat…</div> : (
            <>
              {view === "habitat" && <HabitatView />}
              {view === "engineering" && <EngineeringView />}
              {view === "evidence" && <EvidenceView />}
              {view === "physics" && <PhysicsView />}
              {view === "scenarios" && <ScenariosView />}
              {view === "report" && <ReportView />}
            </>
          )}
        </section>
      </div>
      {t.copilotOpen && t.scenario && (
        <div className="twin-drawer" role="dialog" aria-label="Twin Copilot">
          <div className="row-between"><h3>Copilot · {t.scenario.name}</h3><button className="icon-btn" onClick={() => t.ui({ copilotOpen: false })} aria-label="Close Copilot"><X size={18} /></button></div>
          <p className="muted small">Answers use this scenario (zone {t.selectedZone}), its NASA evidence and the physics models — and say which parts are measurements, calculations or unknowns.</p>
          <ChatPanel kind="twin" compact suggestions={TWIN_QUESTIONS} onOpenExperiment={onOpenExperiment}
            getContext={() => ({ scenario: t.scenario, selected_zone: t.selectedZone, scenario_id: t.savedId })}
            intro={<>Ask about this scenario: closest NASA experiments, missing variables, applicable models, what changes with pressure.</>} />
        </div>
      )}
    </>
  );
}
