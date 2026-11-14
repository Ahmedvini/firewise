import { CONTEXT_LABEL } from "../data/constants.js";

export function num(v, digits = 3) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a !== 0 && (a < 0.01 || a >= 1e5)) return v.toExponential(2);
  return Number(v.toPrecision(digits)).toLocaleString("en-US");
}

export const int = (v) => (v === null || v === undefined ? "—" : Number(v).toLocaleString("en-US"));

const UNIT = { pct: "%", atm: " atm", cm_s: " cm/s" };

/** Text for a Quantity {min,max,unit,status,psia}; "Not documented" when absent (never zero). */
export function rangeText(q, asPsia = false) {
  if (!q || q.min === null || q.min === undefined) return "Not documented";
  if (asPsia && q.psia) return q.psia.min === q.psia.max ? `${num(q.psia.min)} psia` : `${num(q.psia.min)}–${num(q.psia.max)} psia`;
  return q.min === q.max ? `${num(q.min)}${UNIT[q.unit]}` : `${num(q.min)}–${num(q.max)}${UNIT[q.unit]}`;
}

export const contextLabel = (c) => (c ? CONTEXT_LABEL[c] ?? c : "");

export function evidenceKind(kind = "") {
  if (kind.startsWith("curated_fact")) return "Curated fact";
  return (
    {
      psi_record_field: "PSI investigation record",
      psi_table_row: "PSI experimental-table row",
      observation: "Observation",
      aggregate: "Computed aggregate (SQL)",
      "aggregate (computed by SQL for this question)": "Computed aggregate (SQL)",
      nasa_report_page: "NASA report page",
      report_page: "NASA report page",
      run_group_summary: "Record group",
      run_group: "Record group",
      web_search_source: "Web-search source",
      record_text: "PSI investigation record",
      curated_fact: "Curated fact",
      "comparison (computed)": "Computed comparison",
    }[kind] ?? kind
  );
}
