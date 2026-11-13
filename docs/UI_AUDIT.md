# FIREWISE — UI Audit and Simplification (2026-11-13)

Principle: simple on the surface, powerful underneath. Reduce complexity, not capability.

## Audit (before)
| # | Finding | Where |
|---|---|---|
| 1 | Navigation had 8 destinations. Compare is an Investigations task; Findings duplicated the gap-map headlines and the Overview key findings. On phones the 8-item bottom bar overflowed and the last item was cut off. | global |
| 2 | The same provenance notice (2–4 lines, amber) opened every page and repeated the page description. | every page |
| 3 | Decoration competed with content: ember particle canvas, background glow, hero orb with a "conceptual illustration" toggle, glowing borders and backdrop blur. On mobile the orb overlapped text. The particle canvas also halved 3D frame rate. | global, Overview |
| 4 | The Digital Twin page was 156 px wider than a 390 px phone, which widened the fixed bottom bar with it. | Twin (mobile) |
| 5 | The Overview was a wall of statistics: 6 large stat cards, 6 finding cards, 3 charts, 4 featured investigations and limitations. | Overview |
| 6 | Too much was visible at once: | |
|   | 5 filter controls always visible | Investigations |
|   | a 7-column table, 4 stat cards and the custom form always open | Scenario Explorer |
|   | 6 heatmaps at once, plus a separate 10-card Findings page | Research gaps |
|   | an 8-section control panel that pushed the 3D view down on phones, 6 tabs and 4 tiles | Twin |
|   | suggestion chips that stayed visible under every answer | Copilot |
| 7 | Components were inconsistent: 3 metric styles (StatCard, stat-tile, panel); 2 header styles; pill buttons beside square ones; 2 table densities; tags in 4 sizes; ad-hoc `<details>`. | global |
| 8 | Type scale was too wide, from a 120 px hero down to 11 px labels, with display type on minor headings. | global |

## What changed
**Navigation: 6 task-based destinations.** Overview · Investigations (Browse | Compare) · Scenario Explorer · Digital Twin · Research Gaps · Copilot.
- Old links keep working: `#/compare` opens Investigations → Compare, and `#/insights` opens Research Gaps.
- On desktop, a compact sidebar marks the active item with a subtle bar. On phones, a bottom bar holds all 6 items.

**Design system.** All of it lives in `ui/src/styles/*.css` and `ui/src/components/ui.jsx`.
- **Tokens:** surfaces (bg, surface, surface-2, surface-3), text (text, muted, faint), one accent (ember) for primary actions and the active state only, status colours (amber, green, red, blue), and data-series colours.
- **Scales:** type 12/13/15/17/20/26/32; spacing 4–48; radii 6/10/14; control heights 36 and 30; icon size 16.
- **Components:**
  - `PageHeader` (title, one-sentence description, provenance note, actions)
  - `Notice` (warn, danger, info)
  - `Metrics` (one bordered row of key numbers, with source links and an optional tooltip)
  - `Disclosure` (expandable section with a hint line)
  - `Tabs`, `InfoTip` (accessible tooltip), `CoverageBar` (n of total; zero drawn hatched)
  - restyled buttons (primary, secondary, ghost, danger, small), inputs, segmented controls, chips, tags (`.wrap` for sentence-length labels), tables, the modal drawer, and loading, empty and error states with recovery hints
- `Header`, `SampleBanner` and `StatCard` remain as thin aliases, so no page broke during the change.

**Removed or consolidated:**
- the per-page provenance banner (now one note in the sidebar footer, plus page-specific notes only where needed)
- the ember particle canvas, background glow, hero orb and its toggle, glows and backdrop blur
- the separate Findings page (merged into Research Gaps)
- Compare as a top-level destination (now a mode of Investigations)
- the Overview fuel-class bar and documentation-completeness charts (completeness is now a table on Research Gaps)
- the featured-investigation cards (replaced by task shortcuts and real recent activity)
- the four summary tiles in the Twin's engineering view (now in the at-a-glance strip)

**Pages:**
| Page | Now |
|---|---|
| Overview | Heading and one-line description; 4 key numbers with sources; 4 task shortcuts; 4 key findings with evidence; **recent activity** (this workspace's saved scenarios and conversations); the evidence map and limitations in expandable sections. |
| Investigations | Search plus fuel class; facility, data class and sort under **More filters**; compact list rows (identity, fuel class, records, O₂, P, with missing shown as missing); detail shows the verbatim objective, with hypothesis, approach and record details expandable; **Compare** tab. |
| Scenario Explorer | Preset chips; a one-sentence answer and 4 numbers; only investigations with evidence near the window. The other investigations, the custom window, "how the ranking works" and the O₂–pressure map are all expandable. |
| Digital Twin | At-a-glance strip: environment · you set · NASA documents · calculated. Main area: 3D habitat or 2D engineering, sharing the same state. Compact controls with **Advanced** sections. Detail tabs: NASA evidence · Calculations · Scenarios · Report. |
| Research Gaps | Gap list: status, description, coverage bar, missing variables, what would close it, NASA evidence. Then the completeness table by fuel class and "what NASA data do establish". The coverage heatmaps and the methodology, definitions and limitations are expandable. |
| Copilot | Saved conversations on the left. Suggested questions only in an empty chat. Each answer shows its summary, then claims grouped as documented evidence, calculations and model estimates, unknowns, and interpretation, with exact tier tags and citations. Limitations and gaps stay visible; sources and method are expandable. |

**Scientific context kept everywhere:** NASA source links, units, status tags (measured, derived, reported, set-point, user-defined, computed, not documented), missing-data styling, model assumptions and validation, coverage, and the no-risk / no-partial-gravity statements. Nothing scientific was removed; it moved behind one click at most.

## Verification
- `npm run build` OK.
- Playwright: 10/10 tests, including one for the 6 destinations, legacy links, collapsed sections, shortcuts and no horizontal overflow on any page at 390 px.
- pytest: 73/73.
- No console errors on any page.
- No horizontal overflow at 390 px or 768 px on any destination (measured with Playwright device viewports).
- 3D frame rate under software WebGL rose from about 11 to about 22 fps once blur and decorative layers were removed.

## Remaining UX issues
- The Investigations list and detail are side by side on desktop but stacked on phones. On a phone, a selected investigation opens below the list rather than as its own screen.
- The 3D view on phones is usable for orbit and zoom. Precise zone picking is easier with the zone buttons below the scene.
- Long verbatim NASA texts (objectives) are shown in a scrollable box; a "read more" pattern could be gentler.
- The Copilot answer cache and conversations are per browser (a workspace key in `localStorage`). There is no cross-device sync without user accounts.
