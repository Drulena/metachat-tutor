# 0006. The level axis is a parameter of the row registry

- **Status:** accepted
- **Date:** 2026-10-26

## Context

`beginner / intermediate / advanced` lived inside state names (`analysis_task_1_intermediate`), so every file on the level triplet was triplicated: 18 of 44 transition row modules and 18 of 44 scenario modules exist only as triplets of 6 analysis base states. The row triplets are byte-identical except the suffix in `next`/`back`, the fixture's state name and `user_data["level"]`; the scenario triplets differ only in the message text — and the `after_registration` trio not even there. One intent landing on all levels costs lockstep edits: commit `2d1e88f` touched 11 files (+127 insertions) to offer one option on every feedback turn.

Keeping the suffix in the names forced the level axis to be repaired at runtime in four places: the prefix-match back repair in `_go_back` (`tutor_session.py:384-386`), the suffixed-key scenario lookup (`:415`), the `{level}` message substitution (`:459-460`), and the `after_registration_beginner` literal — 17 rows spell it as a `back` placeholder that is a lie for every non-beginner, repaired at runtime by the prefix match.

The same flow carries a live hole: the level can change mid-session (`analysis_intro_* → back → after_registration_* → back → level_assessment`, whose accept map re-sets the level), and a `back` at `pretest`/`level_assessment` lands the learner on `after_registration_beginner` (the repair's beginner fallback fires with the level unset), then `next` → `analysis_intro_beginner` — silently on the beginner path having never picked a level. The per-entry fidelity question (a history entry recorded at intermediate, resolved after the level was re-picked) has no observable effect today because the triplets are identical for nav/accept/item/copy, and only blocks the parameterization design.

## Decision

1. **`row_for(state, level)`.** The row registry is keyed by (**base state**, **level**): 32 row modules — the 6 analysis bases parameterize the axis, the 26 single-form states are untouched — expanded to the 44 (state, level) graph nodes. Graph validation runs over the expanded table: 44 pairs reachable through 32 rows, coverage unchanged. (Clarified at implementation, ticket #25: the expand step is deleted at the cutover — the pair-keyed registry *is* the storage, assembled directly from the row modules, and graph validation runs over its pair keys.)
2. **The level is a session field, set exactly once, and immutable.** Registration is the **point of no return**: `after_registration_*` gets `back: None` (closing the level-change door), `level_assessment` backs to `pretest`, and the pre-registration back chain points at true predecessors (`pretest → data_collection → …`, `start.back = None` already — clarified at implementation, ticket #24: the "data collection" of this chain is the name-and-group screen `start`; the state whose *name* is `data_collection` is the terminal research-data screen, never a back target). The escape from a wrong level pick is **reset**, never back-navigation.
3. **Cutover to base state names, no shim.** State strings at every boundary — `current_state`, chat-history entry states, `Turn.state`, the export transcript — become base names; the level appears in the export **once**, at the session header. No migration script, no compatibility shim, per the owner attestation of this grilling (2026-10-26): the production database holds test sessions only and is backed up; recovery for a stray pre-cutover row is reset (the 0004 pattern).
4. **Scenario modules 18 → 6**: one module per base state carrying the three level texts side by side in a level-keyed map (copy-owner decision — all three level texts of a state in one file, so level copy cannot drift). `SCENARIO["states"]` is generated from the maps, not hand-listed. (Clarified at implementation, ticket #25: what is not hand-listed is the *level* — the assembly names each axis base exactly once and carries the module's level-keyed map under it; the generated per-level flat table of suffixed keys is retired, so no comprehension over levels remains.)
5. **Fixtures are per-base dicts; the seam generates the level axis** (injecting `user_data["level"]` and the state name), so 18 fixture dicts become 6.
6. The four runtime repair points collapse into **one construction point**: building the registration target from the session's level. `_go_back`'s prefix match dies; the 17 placeholder literals become expressible as the base-state target resolved with the session level.

ADR-0002 (one module per state) stands: this removes the level suffix, not the per-base-state module.

## Consequences

- Mid-session level change ceases to exist, and with it the per-entry fidelity question — the session field is unambiguous by construction; nothing parses a suffix at any boundary, ever.
- The export schema shifts: per-turn `state` strings lose their suffix; the session header gains the level. Pre-cutover exports keep the suffixed spelling — one corpus, two spellings, test data only. The cohort-time form of the artifact is stable from here.
- Test surface: assertions pinning suffixed state strings (fixture dicts, `test_views` traversal expectations) get a mechanical rewrite to base names; coverage parity is a spec acceptance (22 transition tests + 38 machine traversals, plus the new test-first anchor: all three level paths traversed through `TutorSession.submit`, asserting the row reached).
- Cohort-time cost, priced at the grilling: a learner who mis-picks a level and resets is a lost participant — mid-session change used to preserve their data. The owner chose the simple rule; the day a cohort dropout traces back to this, it is a known trade, not an oversight.

## Alternatives considered

- **Keep the suffix at the storage boundary, strip it at the seam** — rejected: it buys cohort safety, which the attestation says is not needed, and pays forever: a permanent strip function and two coexisting spellings of every analysis state.
- **Rewrite stored state strings with a data migration** — rejected: script + deploy routine to rescue sessions the attestation calls worthless; strictly dominated by the cutover.
- **Suffix-parse as the canonical level source, with per-entry fidelity for history** — dissolved: the immutability rule makes the session field unambiguous, so parsing survives nowhere.
- **Mid-session level change kept as the escape for a wrong pick** — rejected: it requires the fidelity machinery and inherits the broken pre-registration back edges; the owner chose reset as the escape and flow-edge enforcement.
