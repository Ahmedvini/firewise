# FIREWISE — Open Decisions

| # | Decision | Why it matters | Recommendation | Approver | Deadline |
|---|---|---|---|---|---|
| **D1** | **May pre-event work be used?** | Official FAQ (Nov 13, 2026): *"Teams are not allowed to begin working on the challenges prior to the hackathon."* The pipeline, normalized data, findings and design docs are challenge-specific and pre-date kickoff. The submission requires ticking "Confirm All Work is Original" | **Disclose in writing tonight and follow the ruling. Do not conceal or back-date.** If there is no answer by kickoff, use Plan B (KICKOFF_CHECKLIST §6) and describe the pre-event research honestly in the submission | Team owner → Local Lead / GO team (written) | before Sat 09:00 |
| **D2** | **SI use in shaping the solution idea** | Submission Guide: *"SI should not be used to (come up with your idea of how to solve the challenge)."* FIREWISE's direction was refined in sessions with an SI assistant | Disclose in the same message as D1. In the submission's SI field, state exactly how SI was used (research, data pipeline, documentation, product planning) | Team owner → organizers | with D1 |
| **D3** | **Continue the 3 background downloads?** | They are challenge-specific acquisition still running before kickoff. Telemetry (~5,000 files left) will not finish before Saturday, and it competes for bandwidth | Your choice; I have not stopped them. If D1 is unresolved, stopping them tonight is the conservative option (`kill 197030 197088 241974`). They are resumable later. P0 does not depend on them | You | tonight |
| D4 | Team size: 2 or 3 | Allocation and scope | Use the 3-person plan if possible. With 2, drop the Playwright suite to 5 tests and keep 6 screens | Team | kickoff |
| D5 | Copilot model and budget | Cost and latency | `claude-opus-5-5` (verified ID; current default), effort `medium`, cap the key's spend (e.g. a small monthly limit in the Console). The validation run uses the Batch API | Team owner | kickoff |
| D6 | Demo format | Official limit: 7 slides or ≤ 30 s video | **7-slide deck** plus the live URL (a 30-second video cannot show provenance) | Team | Sat |
| D7 | Ranking method | A weighted composite hides subjective weights and invites "risk score" readings | **Lexicographic evidence counts** (FINAL_API_CONTRACT §3) | Science lead | kickoff |
| D8 | Scenario windows | They define every headline number | Approve the 5 scenarios in FINAL_DATA_CONTRACT §7 (envelope 30–36% / 8.2–10.2 psia; challenge Moon base ≥30% / ≤10.2 psia; FM2 point ±2 pts / ±1 psia) | Science lead | kickoff |
| D9 | Hosting | Judges need a public link with no login; corporate web filters may block new domains | Vercel (web) + Render (API); Docker single-image fallback; request a FortiGuard classification for the domain (Submission Guide tip) | Backend lead | Sat |
| D10 | License for original content | Terms: OSI license, otherwise NASA applies Apache-2.0 | Apache-2.0 | Team | Sat |
| D11 | Literature archive | `sources/papers/` is empty, so `[Lit]` claims rely on URLs | Keep literature claims URL-cited and labeled "not verified offline"; do not add PDF harvesting to P0 | Science lead | — |

**Disclosure message template (D1 + D2):**
> "Our team (FIREWISE, challenge *Flame in Freefall*) did preparatory work before Nov 14: downloaded public NASA
> PSI combustion metadata and tables, wrote data-normalization scripts, and drafted design documents, partly
> with an SI assistant. Before the event starts, we want to confirm what, if anything, of this we may use, and
> how we should disclose it. We will follow your guidance."
