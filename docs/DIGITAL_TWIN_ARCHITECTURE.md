# FIREWISE Digital Twin — Architecture

The Digital Twin extends the existing FIREWISE stack. It adds no second backend and no second scientific database.

```
Browser (Vite + React 18, JavaScript — the existing FIREWISE UI)
  TwinProvider (ui/src/twin/TwinContext.jsx) ── ONE authoritative scenario state
     ├─ Habitat view (Three.js / React Three Fiber 8 / Drei 9)   ├─ Engineering view (Recharts)
     ├─ Evidence view   ├─ Physics view   ├─ Scenarios view   ├─ Report view   └─ Twin Copilot drawer
     │  every view reads the same `scenario` + the same server evaluation
     ▼  debounced, abortable POST /api/twin/evaluate   (scenario → zone conditions + evidence + physics)
FastAPI (api/main.py) ── /api/twin/* (api/twin/routes.py), /api/conversations/*, /api/ask
  api/twin/schemas.py    Pydantic scenario contract + range validation
  api/twin/evidence.py   evidence twin  ── reads build/firewise.sqlite (read-only, deterministic)
  api/twin/physics.py    physics twin   ── pure functions, api/twin/props.py property data
  api/twin/service.py    evaluation, presets, comparison, report
  api/twin/copilot_twin.py  twin-aware Copilot evidence pack + deterministic answers
  api/twin/state.py      user-state store (scenarios, versions, runs, conversations, answer cache)
Storage
  build/firewise.sqlite  scientific DB (schema v2): NASA records + twin_environment, twin_zone, twin_validation
  state/twin_state.sqlite (FIREWISE_STATE_DB) user state, versioned migrations 1–3
```

## Decisions (and why)
| Decision | Reason |
|---|---|
| Keep the existing Vite + React (JavaScript) front end; add `three@0.172.0`, `@react-three/fiber@8.18.0`, `@react-three/drei@9.122.0` | The repository's front end is the team's FLARE app, not Next.js/TypeScript. Porting it would add risk with no user value. R3F v8/Drei v9 are the lines compatible with React 18. |
| User scenarios in a separate state store | `build/firewise.sqlite` is rebuilt deterministically by `load_db.py` (atomic replace) and opened read-only. Storing scenarios there would either wipe them on every rebuild or break reproducibility. The state store holds no scientific records. |
| Twin reference data in the scientific DB | The habitat template (`twin_environment`, `twin_zone`) and the model validation records (`twin_validation`) are deterministic inputs. `load_db.py` loads them with rules R8 (zones tile the habitat) and R9 (no failed validation record). |
| Pure-Python physics | The models are closed-form. NumPy/SciPy would add a dependency with no numerical benefit. |
| Evaluation on the server | One deterministic implementation of evidence and physics. The UI never computes a scientific value, and the Copilot uses exactly the same results. |
| Workspace key (`X-Workspace`) | FIREWISE has no user accounts. Scenarios and conversations are scoped to a random key generated in the browser. The server stores only its SHA-256, and other workspaces get 404. This is capability-key isolation, not authentication. |
| Twin page code-split | Three.js loads only when the twin opens (main bundle 636 kB; twin chunk 924 kB). |

## Shared state
`TwinProvider` holds the current scenario (`api/twin/schemas.py::ScenarioIn`), plus the saved id and version, the dirty flag, the selected zone and the view options (overlay, airflow arrows, cutaway, camera).

- **Editing a value.** It becomes `{value, status: "user_defined", source: null}`.
- **Importing a NASA record.** It copies documented O₂, pressure and airflow with NASA's status and the `row:` evidence id as source. Undocumented values stay untouched.
- **Evaluation.** Every change triggers one evaluation, debounced 350 ms. The last request wins, and earlier ones are aborted.
- **Persistence across navigation.** The provider wraps the whole app, so the state survives page changes. A `localStorage` draft restores it after a reload. That draft is a per-viewer convenience; the saved scenario on the server is the record.

## Scenario model (summary)
| Group | Fields (canonical units) |
|---|---|
| Habitat | `environment_id`, `diameter_m`, `length_m` |
| Atmosphere | `pressure_kPa` (habitat-wide), `temperature_K`, `composition.o2_pct` (+ optional `ar_pct`, `co2_pct`; N₂ balance), `gravity` ∈ {microgravity, lunar, mars, earth} |
| Ventilation | `volumetric_flow_m3_h`, `direction` (+x / −x) |
| Zones | per-zone overrides: `temperature_K`, `airflow_m_s` (local, user-defined), `o2_pct` |
| Experiment | `zone_id`, `slot_id`, `fuel_class`, `material`, `characteristic_length_m`, `surface_temperature_K` |
| Wall (optional) | `thickness_m`, `conductivity_W_mK`, `inner_temperature_K`, `outer_temperature_K`, `material_label` |
| Matching | tolerances (O₂ pts, kPa, m/s) and toggles (pressure, airflow, material, temperature) |

Every value is a `TwinValue {value, status, source}`. Statuses are user_defined, measured, derived, reported, specified, simulated and not_documented. `null` means not set, and is never treated as zero.

## State store (migrations)
| Version | Tables |
|---|---|
| 1 | `twin_scenario`, `twin_scenario_version` (full body per version), `twin_simulation_run` |
| 2 | `twin_scenario.owner_hash` (workspace isolation) |
| 3 | `chat_conversation`, `chat_message`, `copilot_answer_cache` |

Migrations are applied idempotently on first use and recorded in `schema_migrations` (`GET /api/twin/state/migrations`).

## Performance
- **Rendering on demand.** The scene uses `frameloop="demand"` unless airflow animation is on. Airflow arrows are a single instanced mesh; geometry is low-poly, with `dpr ≤ 1.75`.
- **Ember background.** The decorative ember canvas is disabled on the twin page. That raised the software-rendering frame rate from 1.2 to about 11 fps.
- **Measured frame rate.**

| Renderer | Habitat view with airflow animation |
|---|---|
| Intel UHD Graphics (TGL GT1, Vulkan ANGLE), headless Chrome 147 | 60 fps (display-limited) |
| SwiftShader software WebGL | ~10–11 fps (lower bound) |

## Security
- The Anthropic key stays on the backend: it is never in the UI bundle, the image or the API responses (tested).
- Scenario and conversation routes require `X-Workspace` and are owner-scoped.
- Copilot cache keys for twin questions cover the whole twin context and the workspace, so a cached twin answer never crosses scenarios or workspaces. General questions carry no user data and share the cache.
- 422 errors return only `loc`/`msg`/`type`, never the request body.
