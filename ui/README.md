# FLARE – Fire Intelligence for Space Exploration

A React + Vite frontend for exploring NASA microgravity combustion research.

> **Status:** frontend prototype. The NASA dataset and the RAG (AI) backend are **not connected yet**.
> All experiments, numbers and insights are placeholders stored in `src/data/sampleData.js`.
> The AI Assistant does not generate answers or citations.

## 1. Required software

- **Node.js 18 or newer** (LTS recommended): https://nodejs.org (this also installs `npm`)
- **Visual Studio Code**: https://code.visualstudio.com
- A modern browser (Chrome, Edge or Firefox)

Check your install in a terminal: `node -v` and `npm -v`.

## 2. Install and run (Windows, VS Code)

1. Unzip the project and open the **FLARE** folder in VS Code (File → Open Folder).
2. Open the terminal in VS Code (Terminal → New Terminal).
3. Install dependencies (once):

   ```bash
   npm install
   ```

4. Start the development server:

   ```bash
   npm run dev
   ```

5. Open the address shown in the terminal (usually http://localhost:5173).

Other commands: `npm run build` (production build into `dist/`) and `npm run preview` (serve that build).

## 3. Folder structure

```text
FLARE/
├── public/assets/        Static files (logos, images)
├── src/
│   ├── components/       Reusable pieces (Sidebar, StatCard, ChartCard, ...)
│   ├── pages/            One component per page
│   ├── data/             sampleData.js – ALL placeholder data
│   ├── services/         api.js – the ONLY place that talks to a backend
│   ├── utils/            Small helper functions
│   ├── styles/           CSS files (global, layout, components, pages)
│   ├── App.jsx           Page switching + layout
│   └── main.jsx          Entry point
├── index.html
├── package.json
└── vite.config.js
```

## 4. Main files

| File | What it does |
|------|--------------|
| `src/main.jsx` | Starts React and loads the CSS files |
| `src/App.jsx` | Holds the current page and shows the sidebar plus the selected page |
| `src/components/Sidebar.jsx` | Navigation (becomes a bottom bar on phones) |
| `src/components/EmbersBackground.jsx` | Floating ember particles (off if the user prefers reduced motion) |
| `src/components/ChartCard.jsx` | Card wrapper and shared colors for Recharts charts |
| `src/components/StatCard.jsx` | One statistic box |
| `src/components/ExperimentCard.jsx` | One experiment card |
| `src/components/Header.jsx`, `SampleBanner.jsx` | Page title and the placeholder-data notice |
| `src/pages/Overview.jsx` | Hero, statistics, charts, featured experiments |
| `src/pages/AIAssistant.jsx` | Chat interface with placeholder states |
| `src/pages/Experiments.jsx` | Search, filters, sorting and experiment details |
| `src/pages/Compare.jsx` | Select experiments, chart, comparison table, "not comparable" warnings |
| `src/pages/Insights.jsx` | Fire safety insights with evidence status |
| `src/data/sampleData.js` | Placeholder experiments, insights, questions |
| `src/services/api.js` | `askQuestion()` – future `POST /ask` call |
| `src/utils/countBy.js` | Counts records by a field for charts |

## 5. Where the sample data is

Everything is in **`src/data/sampleData.js`**. Each experiment has: `id, name, program, year, type, fuel, category, oxygenPercent, airflowCmS, burnSeconds, peakTempK, objective, conditions, observations, sources`.
Use `null` for a measurement that does not exist; the Compare page then shows "Not in dataset" and warns that experiments are not directly comparable.

To use real data later, replace the `EXPERIMENTS` array (for example by loading a JSON export of the PSI dataset) and keep the same field names.

## 6. Where to connect the RAG API

Open **`src/services/api.js`**.

1. Create a file named `.env` in the project root:

   ```text
   VITE_API_BASE_URL=http://localhost:8000
   ```

2. Restart `npm run dev`.

The function `askQuestion(question)` then sends `POST /ask` with `{ "question": "..." }` and expects:

```json
{
  "answer": "...",
  "key_findings": ["..."],
  "sources": [{ "title": "...", "experiment": "...", "year": 2016, "url": "https://..." }],
  "related_experiments": ["Saffire-I"]
}
```

`src/pages/AIAssistant.jsx` already renders this shape. Your backend must allow requests from the frontend origin (CORS).

## 7. Scientific notes

- Partial-gravity combustion data is not currently available in the PSI dataset, so lunar and Mars conclusions are shown as "More research needed".
- The Safety page shows evidence status only. It does not show risk scores or predict real-world fire risk.
