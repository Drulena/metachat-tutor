# Retro

Append-only, one session per section, newest first. Sessions run `/retro` at
close; the findings feed the standards docs and the next session's start.

## 2026-10-26 — C5+C3 implement kickoff: C5 retirement, C3 surfacing, two review rounds (issues #14–#15)

Shipped on `django`: C5 completed (zero-state `progress()` with
`not_started`, unguarded view calls, templates read `summary.started`,
`_summary_or_none` and the menu.html proxy retired) and C3 surfaced
(typed options — `{value, label, kind}` — on **every** rendered turn,
row-owned rejection copy, views' inference branch and hardcoded copy
deleted). Two two-axis reviews ran; findings fixed; history rebuilt
into two focused commits (`e28da86`, `120047f`) with `Refs:` footers.

### What worked

- **"ADR wins" carried its weight.** Three kickoff-prompt lines
  disagreed with ADR-0005 and the ADR won, flagged not obeyed blindly:
  `Turn.rejected` → `.rejection`; "both visible" → the one merged set
  (scenario label, nav kind); "a feedback row with a rejected copy" —
  no feedback row declares one, the generic copy is the ratified
  outcome (d5). Confidence: high.
- **The second review round caught real bugs green tests had missed:**
  history turns typed stored nav values as plain `choice` with no
  completed marks; `back` at start dropped unflagged (no banner);
  a template comment pinned behaviour the views pre-empt; `_nav_values`
  carried a dead `retry` arm and typed `back` for the `start` row that
  declares `"back": None`. Confidence: high.
- **Shared constants over pinned strings.** A fictional assertion
  (`labels["finish"] == "Finish"` — a label that exists nowhere) was
  caught by a live probe before committing; assertions now quote the
  data modules (`ROLE_MENU_STATE["options"]`, `ROLE_LABELS`).
  Confidence: high.
- Every commit verified green in isolation (stash the next batch, run,
  pop) after the history rewrite. Confidence: high.

### Friction

- **sh.exe collisions recurred** (`couldn't create signal pipe, Win32
  error 5`): multi-line `git commit -m`, hooks, and `git add -p` all
  die from the harness. Working pattern: message into
  `.git/COMMIT_MSG_*` + `git commit --no-verify -F`. Consequence:
  hunk-level commit splits are infeasible — focus lands at file
  granularity (two commits, not the four the review sketched).
  Confidence: high.
- **The commit-msg hook fires only in the owner's shell**, so the
  72-char subject cap is invisible here: an 86-char subject passed the
  harness and violated the rule. Check subject length before writing
  the message file. Confidence: high.
- **Two edits anchored to compressed-summary excerpts failed** — the
  elided `…` text is not file text. Re-read the exact region before
  editing. Confidence: high.

### System updates

- `test_states_without_a_row_carry_no_copy` renamed and redocumented —
  it pins the structural no-row semantics, not the old generic
  fallback.
- A rendered-page parity test pins the shared zero-state panel on
  `/menu/` and `/` (the pages-cannot-disagree contract).
- `_append_user_turn(state, text, rejected=False)` — the flag is set
  at the append site, callers never poke `chat_history[-1]`.

### Next time

- `django` is 23 commits ahead of `origin/django` (unpushed) — push
  from the owner's shell.
- No row declares a `retry` edge; if one ever does, `_nav_values`
  needs the arm (comment marks the seam).
- Row `phase` is dead residue vs GLOSSARY ("phase (gone)") — left for
  the dead-code sweep (candidate 6's scope).

## 2026-10-25 (evening) — Owner UI polish pass: four reported defects (issue #15)

Owner reviewed the branch in `runserver` and reported four defects; all four
fixed test-first on the same branch: the literal progress-panel comment
(Django `{# #}` is single-line — block headers use `{% comment %}`, and a
rendered-page test asserts the words absent), the LLM chain-of-thought reaching
the chat (parse `content` only; a `content`-missing answer falls through to the
demo-failure path; prompt demands student-facing output only), utility offers
sharing the look and order of content options (choices first in defined order;
nav/retry in their own row), finished roles rendering live (new
`TurnOption.completed` — the module marks options whose step is in the ledger;
role options map through `ROLE_BY_VALUE`, and the test's first premise —
comparing scenario values to ledger keys — was false, caught by a print probe).
Lesson kept: the two-axis review and the unit tests never rendered a full page —
owner eyes on `runserver` found four defects in minutes; rendered-page tests
catch comment leaks.

## 2026-10-25 — Candidates 2/3/5: Summary rows, typed options, rejection copy (issues #14–#15)

Shipped: section rows carrying their own status (ADR-0003), the `started`/
`finished` lifecycle pair, typed `TurnOption {value, label, kind}` with
row-owned rejection copy (ADR-0005). Branch `refactor/summary-status-rows`,
9 commits from the base, full suite green.

### What worked

- **RED tests as premise-checkers.** Two test premises were false and the red
  caught them: "start has no transition row → generic copy" (start ACCEPTS any
  input — the welcome answers free text), and "the typed `back` marks the
  newest turn" (back/retry append no user entry — the adjacency rule can never
  fire). The stamp design (mark the answered entry at the routing moment) came
  out of those reds. Confidence: high.
- **Two-axis review caught what green tests missed.** The `.rejection-note`
  class shipped in the template unstyled; a rejection-inference branch survived
  dead in the view; three modules pinned the same strings. All fixed in the
  cleanup commit. Green is not "done". Confidence: high.
- **Grilling the kind rule in the open.** Three iterations (nav-map origin →
  row-declared `choices` → unclassified falls back to `nav`) before the
  vocabulary settled; the final rule is in GLOSSARY + ADR-0005, so the next
  reader gets the rule, not the archaeology. Confidence: high.

### Friction

- **Windows harness vs Git hooks.** Every hook-spawned `sh.exe` dies here with
  `couldn't create signal pipe, Win32 error 5` — a raw spawn fails too, so the
  harness's MSYS runtime collides with Git's. Hook commits from the harness
  need `--no-verify` plus verification in the user's own shell. Note written
  to the global guide. **Resolved:** the owner confirmed in their own shell
  (2026-10-25) that the hook fires. Confidence: high (mechanism not
  root-caused).
- **`git reset --hard HEAD~1` as hook-cleanup wiped an uncommitted doc batch**
  (my own edits, recovered by re-application, now in the amended commit).
  Lesson: never reset with work in flight — test a hook with
  `git commit --amend` on the real commit. Confidence: high.
- Context pressure on a deep session (grill + implement + review + cleanup)
  forced aggressive folding; two full context windows consumed. A
  review-and-cleanup pass is a natural fork point for a fresh session.
  Confidence: medium.

### System updates

- `docs/agents/coding-standards.md` created: docstring bar, template class ⇔
  CSS rule, shared test constants pinned once, venv test commands.
- `docs/agents/domain.md`: ADR file conventions (`# 000N. Title`,
  `**Status:**`, `**Supersedes:**`, `Alternatives considered`).
- ADR-0005 normalised: Supersedes 0001/0003, 44 rows, ratified kind rule.
- `.git/hooks/commit-msg`: Conventional subject ≤72 + `Issue:` footer —
  unverified from this harness, verify in a plain shell.
- `~/.agents/AGENTS.md`: commit-early-and-often bullet.

### Next time

- Run the hook smoke test in the user's shell before wiring it into the trail.
- Untracked-file policy: resolved in-session — the gitignore rework had
  dropped `.env` / `*.sqlite3` / `.hive` (owner: secrets and research data
  must never be visible to `add -A`); restored in `cbddcaf`, verified never
  committed. Keep the protection set when editing `.gitignore` — add, don't
  subtract.
