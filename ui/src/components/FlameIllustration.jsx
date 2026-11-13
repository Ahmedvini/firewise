// "Why gravity matters": a conceptual, animated illustration of a candle flame at different gravity levels.
// Earth and microgravity are drawn from well-established combustion physics (qualitative, not FIREWISE data).
// Mars and Moon are NOT drawn: PSI has no partial-gravity combustion data, and FIREWISE never predicts it —
// only the two known endpoints are outlined.
import { useState } from "react";
import { EvidenceLink } from "./Evidence.jsx";

const CASES = [
  { id: "earth", label: "Earth", g: "1 g" },
  { id: "mars", label: "Mars", g: "0.38 g" },
  { id: "moon", label: "Moon", g: "0.16 g" },
  { id: "micro", label: "Microgravity", g: "≈0 g" },
];

const CAPTION = {
  earth: { title: "Buoyancy shapes the flame",
    text: "Hot gas rises and pulls fresh air in from below, stretching the flame into a tall, flickering teardrop. Fast air supply and long residence of soot make it bright yellow.",
    evidence: [["fact:F06", "1 g vs µg (Saffire-II)"]], note: "PSI flight tests are microgravity; 1 g appears only as Saffire-II paired observations." },
  micro: { title: "Without buoyancy, oxygen arrives only by diffusion",
    text: "Nothing carries hot gas away, so the flame wraps the wick as a near-sphere. Oxygen diffuses in slowly: the flame is dimmer, bluer and produces less soot.",
    evidence: [["agg:partial_gravity_records", "all PSI records are µg"]], note: "Every NASA PSI combustion record in FIREWISE was taken in microgravity." },
  partial: { title: "Not measured — not predicted",
    text: "Only the two endpoints are known: Earth gravity and microgravity. NASA PSI has no combustion records at lunar or Martian gravity, so FIREWISE does not draw or predict this flame. LUCI (2025) and FM2 (planned) are the first tests.",
    evidence: [["agg:partial_gravity_records", "0 partial-gravity records"], ["fact:X01", "LUCI"], ["fact:X02", "FM2"]], note: null },
};

// Teardrop (1 g) silhouette and the microgravity sphere, shared by the drawings and the partial-gravity outlines.
const TEAR = "M160 58 C 187 104, 199 152, 193 186 C 188 212, 175 224, 160 224 C 145 224, 132 212, 127 186 C 121 152, 133 104, 160 58 Z";
const SPHERE = { cx: 160, cy: 180, r: 46 }; // sits on the wick; quenched just above the wax

function Candle() {
  return (
    <g aria-hidden>
      <rect x="146" y="234" width="28" height="56" rx="3" fill="url(#candleBody)" />
      <ellipse cx="160" cy="234" rx="14" ry="3" fill="#e9e3d6" />
      <path d="M160 234 C 159 226, 161 220, 160 214" stroke="#2a1d14" strokeWidth="2.2" fill="none" strokeLinecap="round" />
    </g>
  );
}

function Arrow({ d, color, label, lx, ly, anchor = "middle" }) {
  return (
    <g className="flow-arrow">
      <path d={d} stroke={color} strokeWidth="1.6" fill="none" markerEnd={`url(#head-${color.slice(1)})`} />
      {label && <text x={lx} y={ly} fill={color} fontSize="10" textAnchor={anchor}>{label}</text>}
    </g>
  );
}

function EarthFlame({ on }) {
  return (
    <g className={`flame-layer ${on ? "on" : ""}`} aria-hidden>
      <g className="flicker">
        <path d={TEAR} fill="url(#earthGlow)" filter="url(#blur12)" transform="translate(160 224) scale(1.35) translate(-160 -224)" opacity="0.55" />
        <path d={TEAR} fill="url(#earthBody)" filter="url(#soft)" />
        <path d="M137 206 C 141 224, 179 224, 183 206 C 176 218, 144 218, 137 206 Z" fill="#4ea4ff" opacity="0.85" filter="url(#soft)" />
        <ellipse cx="160" cy="200" rx="7" ry="17" fill="#2b1406" opacity="0.4" filter="url(#soft)" />
      </g>
      {Array.from({ length: 9 }).map((_, i) => (
        <circle key={i} className="soot" cx={154 + ((i * 7) % 13)} cy="70" r={1.2 + (i % 3) * 0.5} style={{ animationDelay: `${i * 0.33}s` }} />
      ))}
      <Arrow d="M84 246 C 108 240, 122 226, 132 212" color="#7fb2f0" label="fresh air drawn in" lx="62" ly="226" anchor="start" />
      <Arrow d="M236 246 C 212 240, 198 226, 188 212" color="#7fb2f0" />
      <Arrow d="M160 44 L 160 20" color="#f2b45c" label="hot gas rises" lx="172" ly="32" anchor="start" />
    </g>
  );
}

function MicroFlame({ on }) {
  return (
    <g className={`flame-layer ${on ? "on" : ""}`} aria-hidden>
      <g className="breathe">
        <circle cx={SPHERE.cx} cy={SPHERE.cy} r="70" fill="url(#microGlow)" filter="url(#blur12)" />
        <circle cx={SPHERE.cx} cy={SPHERE.cy} r={SPHERE.r} fill="url(#microShell)" />
        <circle cx={SPHERE.cx} cy={SPHERE.cy} r="30" fill="url(#microSoot)" opacity="0.7" />
      </g>
      {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sy], i) => (
        <g key={i}>
          <Arrow d={`M${160 + sx * 104} ${SPHERE.cy + sy * 74} L ${160 + sx * 70} ${SPHERE.cy + sy * 50}`} color="#7fb2f0" />
        </g>
      ))}
      <Arrow d="M118 142 L 98 128" color="#9ba5b6" />
      <Arrow d="M202 142 L 222 128" color="#9ba5b6" />
      <text x="34" y="100" fill="#7fb2f0" fontSize="10">O₂ diffuses in</text>
      <text x="226" y="152" fill="#9ba5b6" fontSize="10">products diffuse out</text>
    </g>
  );
}

function PartialOutlines({ on }) {
  return (
    <g className={`flame-layer ${on ? "on" : ""}`} aria-hidden>
      <path d={TEAR} fill="none" stroke="#f2b45c" strokeWidth="1.4" strokeDasharray="5 5" opacity="0.8" />
      <circle cx={SPHERE.cx} cy={SPHERE.cy} r={SPHERE.r} fill="none" stroke="#7fb2f0" strokeWidth="1.4" strokeDasharray="5 5" opacity="0.8" />
      <text x="160" y="156" fill="#e8edf5" fontSize="42" fontWeight="600" textAnchor="middle" opacity="0.85">?</text>
      <text x="204" y="78" fill="#f2b45c" fontSize="10">Earth (1 g)</text>
      <text x="212" y="222" fill="#7fb2f0" fontSize="10">microgravity</text>
      <text x="160" y="176" fill="#9ba5b6" fontSize="10" textAnchor="middle">no PSI data</text>
    </g>
  );
}

export default function FlameIllustration({ onNavigate }) {
  const [gravity, setGravity] = useState("micro");
  const kind = gravity === "earth" ? "earth" : gravity === "micro" ? "micro" : "partial";
  const c = CAPTION[kind];
  const sel = CASES.find((x) => x.id === gravity);
  const alt = kind === "earth" ? "Illustration: a tall yellow teardrop candle flame with rising soot and inflowing air at Earth gravity."
    : kind === "micro" ? "Illustration: a dim, near-spherical blue candle flame in microgravity with oxygen diffusing in."
      : `Illustration: dashed outlines of the Earth and microgravity flames with a question mark; no data at ${sel.label} gravity.`;
  return (
    <section className="flame-card" aria-label="Why gravity matters">
      <div className="flame-head">
        <h3>Why gravity matters</h3>
        <span className="tag" title="Qualitative drawing based on established combustion physics. Not FIREWISE data, not a simulation.">conceptual illustration</span>
      </div>
      <svg className="flame-svg" viewBox="0 0 320 300" role="img" aria-label={alt}>
        <defs>
          <radialGradient id="earthBody" cx="50%" cy="68%" r="62%">
            <stop offset="0%" stopColor="#fffbe8" />
            <stop offset="28%" stopColor="#ffe08a" />
            <stop offset="58%" stopColor="#ffab45" />
            <stop offset="85%" stopColor="#ff6d1f" />
            <stop offset="100%" stopColor="#ff4d10" stopOpacity="0.2" />
          </radialGradient>
          <radialGradient id="earthGlow" cx="50%" cy="65%" r="60%">
            <stop offset="0%" stopColor="#ff9a3c" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ff5a1a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="microShell" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0b1530" stopOpacity="0" />
            <stop offset="62%" stopColor="#2a5bd8" stopOpacity="0.12" />
            <stop offset="84%" stopColor="#4f8dff" stopOpacity="0.75" />
            <stop offset="93%" stopColor="#a9ccff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#6aa2ff" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="microSoot" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffb36b" stopOpacity="0" />
            <stop offset="78%" stopColor="#ff9a4a" stopOpacity="0.22" />
            <stop offset="92%" stopColor="#ffc27a" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#ffc27a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="microGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#3d7bff" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#3d7bff" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="candleBody" x1="0" x2="1">
            <stop offset="0%" stopColor="#bfb8aa" /><stop offset="45%" stopColor="#efe9dc" /><stop offset="100%" stopColor="#a69f92" />
          </linearGradient>
          <filter id="blur12" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10" /></filter>
          <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.4" /></filter>
          {["7fb2f0", "f2b45c", "9ba5b6"].map((c) => (
            <marker key={c} id={`head-${c}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 z" fill={`#${c}`} />
            </marker>
          ))}
        </defs>
        <EarthFlame on={kind === "earth"} />
        <MicroFlame on={kind === "micro"} />
        <PartialOutlines on={kind === "partial"} />
        <Candle />
      </svg>
      <div className="segmented flame-switch" role="group" aria-label="Gravity level">
        {CASES.map((x) => (
          <button key={x.id} className={gravity === x.id ? "on" : ""} aria-pressed={gravity === x.id} onClick={() => setGravity(x.id)}>
            {x.label} <span className="faint">{x.g}</span>
          </button>
        ))}
      </div>
      <div className="flame-caption" aria-live="polite">
        <b>{c.title}</b>
        <p className="muted small">{c.text}</p>
        {c.note && <p className="faint small">{c.note}</p>}
        <div className="ev-row">
          {c.evidence.map(([id, label]) => <EvidenceLink key={id} id={id} label={label} />)}
          {kind === "partial" && onNavigate && <button className="btn ghost sm" onClick={() => onNavigate("gaps")}>See research gaps →</button>}
        </div>
      </div>
    </section>
  );
}
