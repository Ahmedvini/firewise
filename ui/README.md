# FIREWISE UI

The React 18 + Vite 5 front end for FIREWISE. It started as the team's FLARE prototype, copied from `~/Downloads/FLARE`, and is now connected to the FIREWISE API. There is no placeholder data: every number comes from `/api/*`.

```bash
npm ci
npm run dev     # http://localhost:5173, proxies /api to $VITE_API_PROXY (default http://127.0.0.1:8000)
npm run build   # -> dist/, served by the FastAPI app on the same origin
```

| Variable | Default | Use |
|---|---|---|
| `VITE_API_BASE_URL` | `""` (same origin) | API origin when the UI is hosted separately |
| `VITE_API_PROXY` | `http://127.0.0.1:8000` | dev-server proxy target |
| `VITE_BASE` | `/` | public base path |

No secrets belong here. The Copilot key lives only on the backend.

Structure:
- `src/services/api.js`: fetch helpers and the `useApi` hook
- `src/components/Evidence.jsx`: the evidence drawer, which shows the verbatim NASA row and its provenance
- `src/components/Tags.jsx`: measurement-status and evidence-tier tags
- `src/pages/*`: the seven modules
- `src/data/constants.js`: labels, the validated series colours, suggested questions and compare presets

Routes are hash-based, e.g. `#/experiments/PSI-159`, `#/scenarios`, `#/assistant?q=...`.
