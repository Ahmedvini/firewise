# FIREWISE Digital Twin — User Guide

Open **Digital Twin** in the navigation (`#/twin/habitat`). The workspace has four parts:
- **At-a-glance strip** (top): the environment, the values you set, what NASA documents for them, and what is calculated.
- **Main area:** the 3D habitat, or the 2D engineering dashboard (toggle; both show the same scenario).
- **Control panel** (right): the essential inputs (preset, O₂, pressure, temperature, gravity, experiment), with zone conditions, sample and wall heat transfer, habitat and ventilation, trace gases and evidence matching under **Advanced**. Every input shows its unit and a status tag.
- **Detail tabs** (below): NASA evidence, Calculations (the physics models), Scenarios and Report.
- **Ask Copilot** (top right): a Copilot that knows the active scenario.

All views show the same scenario. A change in the panel updates the 3D scene, the charts, the evidence, the physics and the report together.

## Reading the status tags
| Tag | Meaning |
|---|---|
| ✎ User-defined | You configured it. It is not a measurement. |
| ● Measured (NASA) / ◐ Reported / □ Set-point / ◆ Derived | Copied from a NASA record ("Use conditions"), keeping NASA's status. Hover to see the source row. |
| ∑ Computed (model) | Output of a FIREWISE physics model (see the Physics view for the model and version). |
| – Not documented | Not set. It is never treated as zero. |

## Typical workflow
1. **Pick a starting point.** Choose a preset: sea-level cabin air, exploration atmosphere (34% O₂, 8.2 psia, lunar gravity), or the Moon-base challenge definition. You can also set values yourself. Out-of-range values are rejected inline, with the allowed range shown.
2. **Select a zone.** Click a zone or sensor in the 3D view, or use the Z1–Z5 buttons. You can then set its temperature, local airflow or an O₂ override. Leave a field blank to use the habitat value.
3. **Place the experiment.** Choose the rack chamber (Z3) or the glovebox (Z2), the material class and, optionally, a material text such as `PMMA`. Add the sample length and the surface temperature if you want convective heat exchange computed.
4. **Habitat view:**
   - Rotate (drag), zoom (scroll) and pan (right-drag).
   - Camera presets: 3/4, Side, Top and Inside.
   - Toggle the overlay (O₂ / temperature / airflow), the airflow arrows and the cutaway.
   - The legend says what each visual encodes. Zone colours are user-defined values. Arrows show an illustrative direction, with speed from Model C's computed bulk velocity; they are not a flow field.
5. **2D engineering view** (main-area toggle):
   - zone charts (orange = user-defined, green = computed)
   - NASA records vs your scenario (blue = NASA)
   - evidence coverage
   - saved-version and session history
   - the outputs table and the assumptions in force
6. **NASA evidence tab:**
   - exact NASA matches and the nearest documented records, with the distance per variable
   - which variables could not be compared
   - source rows (click to see the verbatim NASA row)
   - **Use conditions:** copies a record's documented values into your scenario with NASA status
   - coverage: missing measurements, available observations, materials, outcomes, sources

   A grey row is evidence at a different gravity level.
7. **Calculations tab:**
   - each model's status (completed / unavailable with the missing inputs / rejected with the reason)
   - inputs with their provenance; outputs with unit and Verified/Validated tag
   - equations, assumptions, applicability and limitations
   - the validation-records table (MAE, RMSE, bias, relative error)
   - the models that are not implemented

   Save the scenario, then click **Run & record simulation** to store a reproducible run (input hash, engine version).
8. **Scenarios tab:**
   - Save and save new versions; a version history lets you restore older configurations.
   - Load, Duplicate and Delete (with confirmation).
   - Tick 2–4 scenarios and **Compare selected** to see configuration, evidence and physics side by side. Rows that differ are highlighted.
9. **Report tab:** the scientific report for the current configuration (saved or unsaved), downloadable as Markdown or JSON.
10. **Ask Copilot:** for example "Which NASA experiments are closest to this environment?", "Which variables are missing?" or "How reliable is the selected model?". Every claim is tagged (measured, calculation, model estimate, unknown, interpretation) and cites its evidence.

## Copilot conversations
The **AI Copilot** page and the twin drawer save every conversation to your workspace:
- Use **New chat** to start one.
- Click a conversation to switch to it; its full history reloads.
- Rename or delete conversations from the list.

Asking the same question again with the same context returns the stored answer instantly, marked **Cached answer**.

Your workspace key lives in this browser (`localStorage`). Another browser has a different workspace and does not see your scenarios or conversations.

## What the twin does not do
- It does not predict fire, ignition, flame spread, extinction or fire risk. No combustion model is implemented.
- It does not show partial-gravity combustion evidence: PSI has none. At lunar or Mars gravity, exact matches are 0, and nearest records are labelled as microgravity evidence.
- It is not connected to live telemetry. Monitoring points display configured values.
- It does not compute local airflow fields. Local airflow is user-defined, and Model C gives habitat-averaged bulk quantities only.
