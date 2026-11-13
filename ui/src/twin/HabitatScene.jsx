// Interactive 3D habitat (Three.js via React Three Fiber). Reads ONLY the shared twin state.
// Labels say what each visual encodes: zone colours = user-defined scenario values; airflow arrows =
// illustrative direction with speed from Model C's bulk estimate (uniform, not a flow field).
import { Component, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { useTwin, val } from "./TwinContext.jsx";

export const RAMP = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"];
export const OVERLAYS = {
  none: { label: "No overlay" },
  o2: { label: "O₂ (mole %)", get: (z) => val(z.o2_pct), unit: "%" },
  temperature: { label: "Temperature (°C)", get: (z) => (val(z.temperature_K) == null ? null : val(z.temperature_K) - 273.15), unit: "°C" },
  airflow: { label: "Local airflow (m/s)", get: (z) => val(z.airflow_m_s), unit: "m/s" },
};
const EQUIP_COLOR = { rack: "#3b4a66", workstation: "#46506a", glovebox: "#4c5b78", eclss: "#3f5a5a", stowage: "#4a4a5e" };

export function rampColor(v, lo, hi) {
  if (v == null) return null;
  const t = hi > lo ? (v - lo) / (hi - lo) : 0.5;
  return RAMP[Math.min(RAMP.length - 1, Math.max(0, Math.floor(t * RAMP.length)))];
}

function useGeometry() {
  const { scenario } = useTwin();
  const D = val(scenario.habitat.diameter_m) || 4.2;
  const L = val(scenario.habitat.length_m) || 8;
  return { r: D / 2, L, x: (f) => f * L - L / 2 };
}

function Hull({ cutaway }) {
  const { r, L } = useGeometry();
  return (
    <group rotation={[0, 0, Math.PI / 2]}>
      {/* cutaway opens the +z side facing the default camera */}
      <mesh>
        <cylinderGeometry args={[r, r, L, 64, 1, true, cutaway ? Math.PI * 0.15 : 0, cutaway ? Math.PI * 1.25 : Math.PI * 2]} />
        <meshStandardMaterial color="#8090ad" transparent opacity={cutaway ? 0.18 : 0.28} side={THREE.DoubleSide} metalness={0.3} roughness={0.6} depthWrite={false} />
      </mesh>
      {[-L / 2, L / 2].map((y) => (
        <mesh key={y} position={[0, y, 0]}>
          <torusGeometry args={[r, 0.04, 8, 64]} />
          <meshStandardMaterial color="#9aa7c2" />
        </mesh>
      ))}
    </group>
  );
}

function EndCaps({ direction }) {
  const { r, L } = useGeometry();
  const supplyX = direction === "-x" ? L / 2 : -L / 2;
  return (
    <>
      {[-L / 2, L / 2].map((x) => (
        <mesh key={x} position={[x, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
          <ringGeometry args={[r * 0.35, r, 48]} />
          <meshStandardMaterial color="#2a3346" side={THREE.DoubleSide} transparent opacity={0.55} />
        </mesh>
      ))}
      <Html position={[supplyX, r * 0.95, 0]} center className="scene-label">Ventilation supply</Html>
      <Html position={[-supplyX, r * 0.95, 0]} center className="scene-label">Return</Html>
    </>
  );
}

function Deck() {
  const { r, L } = useGeometry();
  const y = -r * 0.62;
  const w = 2 * Math.sqrt(r * r - y * y) * 0.98;
  return (
    <mesh position={[0, y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[L * 0.995, w]} />
      <meshStandardMaterial color="#1b2333" />
    </mesh>
  );
}

function Zones({ conditions, overlay, selected, onSelect }) {
  const { env } = useTwin();
  const { r, L, x } = useGeometry();
  const [hover, setHover] = useState(null);
  const ov = OVERLAYS[overlay];
  const vals = ov.get ? conditions.map((c) => ov.get(c)).filter((v) => v != null) : [];
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return env.zones.map((z) => {
    const c = conditions.find((k) => k.zone_id === z.id);
    const v = ov.get && c ? ov.get(c) : null;
    const color = rampColor(v, lo, hi) ?? "#3a4560";
    const len = (z.x_end - z.x_start) * L;
    const sel = selected === z.id;
    return (
      <group key={z.id} position={[x((z.x_start + z.x_end) / 2), 0, 0]}>
        <mesh rotation={[0, 0, Math.PI / 2]} onClick={(e) => { e.stopPropagation(); onSelect(z.id); }}
          onPointerOver={(e) => { e.stopPropagation(); setHover(z.id); document.body.style.cursor = "pointer"; }}
          onPointerOut={() => { setHover(null); document.body.style.cursor = ""; }} name={`zone-${z.id}`}>
          <cylinderGeometry args={[r * 0.97, r * 0.97, len * 0.985, 48, 1, true]} />
          <meshStandardMaterial color={color} transparent opacity={sel ? 0.42 : hover === z.id ? 0.3 : overlay === "none" ? 0.06 : 0.2}
            side={THREE.DoubleSide} depthWrite={false} emissive={sel ? "#FF7138" : "#000000"} emissiveIntensity={sel ? 0.35 : 0} />
        </mesh>
        {sel && (
          <group rotation={[0, 0, Math.PI / 2]}>
            {[-len / 2, len / 2].map((y) => (
              <mesh key={y} position={[0, y * 0.985, 0]}>
                <torusGeometry args={[r * 0.975, 0.03, 8, 64]} />
                <meshBasicMaterial color="#FF7138" />
              </mesh>
            ))}
          </group>
        )}
        <Html position={[0, -r * 0.62 + 0.02, r * 0.55]} center className={`scene-label zone-label ${sel ? "on" : ""}`}>{z.id}</Html>
      </group>
    );
  });
}

function Equipment() {
  const { env, scenario } = useTwin();
  const { r, L, x } = useGeometry();
  const exp = scenario.experiment;
  const slot = env.experiment_slots.find((s) => s.id === exp.slot_id) || env.experiment_slots.find((s) => s.zone_id === exp.zone_id);
  return (
    <>
      {env.equipment.map((e) => {
        const z = (e.side === "port" ? -1 : 1) * r * 0.6;
        return (
          <mesh key={e.id} position={[x(e.x_frac), -r * 0.08, z]}>
            <boxGeometry args={[e.width_frac * L, r * 1.0, r * 0.42]} />
            <meshStandardMaterial color={EQUIP_COLOR[e.kind] || "#444c60"} metalness={0.2} roughness={0.7} />
          </mesh>
        );
      })}
      {slot && (
        <group position={[x(slot.x_frac), -r * 0.05, (slot.side === "port" ? -1 : 1) * r * 0.36]}>
          <mesh>
            <boxGeometry args={[0.32, 0.32, 0.32]} />
            <meshStandardMaterial color="#FF7138" emissive="#FF7138" emissiveIntensity={0.5} transparent opacity={0.85} />
          </mesh>
          <Html position={[0, 0.42, 0]} center className="scene-label exp-label">
            Experiment · {exp.fuel_class?.replace(/_/g, " ") || "class not set"}{exp.material ? ` · ${exp.material}` : ""}
          </Html>
        </group>
      )}
    </>
  );
}

function MonitoringPoints({ conditions, selected, onSelect }) {
  const { env } = useTwin();
  const { r, x } = useGeometry();
  return env.monitoring_points.map((m) => {
    const c = conditions.find((k) => k.zone_id === m.zone_id);
    const sel = selected === m.zone_id;
    return (
      <group key={m.id} position={[x(m.x_frac), r * 0.72, 0]}>
        <mesh onClick={(e) => { e.stopPropagation(); onSelect(m.zone_id); }}>
          <sphereGeometry args={[0.09, 16, 16]} />
          <meshStandardMaterial color={sel ? "#FFB454" : "#cfd8ea"} emissive={sel ? "#FFB454" : "#000"} emissiveIntensity={sel ? 0.6 : 0} />
        </mesh>
        {sel && c && (
          <Html position={[0, 0.35, 0]} center className="scene-label sensor-card">
            <b>{m.id} · virtual monitoring point</b>
            <div>O₂ {val(c.o2_pct) ?? "—"}% · {val(c.pressure_kPa)?.toFixed(1)} kPa</div>
            <div>{val(c.temperature_K) != null ? `${(val(c.temperature_K) - 273.15).toFixed(1)} °C` : "T not set"} · {val(c.airflow_m_s) != null ? `${val(c.airflow_m_s)} m/s` : "airflow not set"}</div>
            <div className="muted">user-defined scenario values</div>
          </Html>
        )}
      </group>
    );
  });
}

function Airflow({ bulkCmS, direction }) {
  const { r, L } = useGeometry();
  const ref = useRef();
  const n = 54;
  const seeds = useMemo(() => Array.from({ length: n }, (_, i) => {
    const a = (i * 2.399963) % (Math.PI * 2);           // golden-angle spread over the cross-section
    const rad = r * 0.25 + (r * 0.5 * ((i * 7) % n)) / n;
    return { y: Math.sin(a) * rad * 0.8, z: Math.cos(a) * rad, x0: ((i * 13) % n) / n };
  }), [r]);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const sign = direction === "-x" ? -1 : 1;
  // visual speed: proportional to the computed bulk velocity, compressed so slow flows stay visible
  const speed = bulkCmS ? Math.min(2.5, 0.25 + Math.log10(1 + bulkCmS) * 0.9) : 0;
  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    seeds.forEach((s, i) => {
      const f = (s.x0 + (t * speed) / L) % 1;
      dummy.position.set(sign * (f * L - L / 2), s.y, s.z);
      dummy.rotation.set(0, 0, -sign * Math.PI / 2);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      ref.current.setMatrixAt(i, dummy.matrix);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={ref} args={[null, null, n]} frustumCulled={false}>
      <coneGeometry args={[0.06, 0.22, 8]} />
      <meshBasicMaterial color="#7fd6e8" transparent opacity={0.75} />
    </instancedMesh>
  );
}

function CameraRig({ preset }) {
  const { camera, controls } = useThree();
  const { r, L } = useGeometry();
  const invalidate = useThree((st) => st.invalidate);
  useEffect(() => {
    const span = Math.max(L, 2 * r);
    const P = { iso: [span * 0.78, r * 2.4 + span * 0.3, span * 1.05], side: [0, 0.4, span * 1.35], top: [0, span * 1.45, 0.01], inside: [-L * 0.42, 0, 0.01] };
    const T = { iso: [0, 0, 0], side: [0, 0, 0], top: [0, 0, 0], inside: [L * 0.5, 0, 0] };
    camera.position.set(...(P[preset] || P.iso));
    if (controls) {
      controls.target.set(...(T[preset] || T.iso));
      controls.update();
    } else {
      camera.lookAt(...(T[preset] || T.iso));
    }
    invalidate();
  }, [preset, r, L, camera, controls, invalidate]);
  return null;
}

class WebGLBoundary extends Component {
  constructor(p) { super(p); this.state = { failed: false }; }
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed
      ? <div className="panel empty">The 3D view needs WebGL, which is unavailable in this browser. The Engineering view shows the same scenario state.</div>
      : this.props.children;
  }
}

export default function HabitatScene() {
  const t = useTwin();
  const { evaluation, overlay, showAirflow, cutaway, camera, selectedZone, scenario } = t;
  const conditions = evaluation.data?.zone_conditions ?? [];
  const bulk = evaluation.data?.physics.results.find((r) => r.model_id === "bulk_airflow" && r.status === "completed")
    ?.outputs.find((o) => o.name === "bulk_velocity")?.value;
  if (!t.env || !scenario) return null;
  return (
    <WebGLBoundary>
      <Canvas className="habitat-canvas" dpr={[1, 1.75]} camera={{ fov: 42, near: 0.05, far: 200, position: [5, 4, 7] }}
        frameloop={showAirflow && bulk ? "always" : "demand"} gl={{ antialias: true, powerPreference: "high-performance" }}
        onPointerMissed={() => {}} aria-label="Interactive 3D habitat. Use the zone buttons below for keyboard access.">
        <color attach="background" args={["#0b1120"]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[6, 8, 5]} intensity={1.1} />
        <directionalLight position={[-6, -3, -4]} intensity={0.35} />
        <Hull cutaway={cutaway} />
        <EndCaps direction={scenario.ventilation.direction} />
        <Deck />
        <Zones conditions={conditions} overlay={overlay} selected={selectedZone} onSelect={(z) => t.ui({ selectedZone: z })} />
        <Equipment />
        <MonitoringPoints conditions={conditions} selected={selectedZone} onSelect={(z) => t.ui({ selectedZone: z })} />
        {showAirflow && bulk ? <Airflow bulkCmS={bulk} direction={scenario.ventilation.direction} /> : null}
        <OrbitControls makeDefault enableDamping dampingFactor={0.12} minDistance={1.2} maxDistance={60} />
        <CameraRig preset={camera} />
      </Canvas>
    </WebGLBoundary>
  );
}
