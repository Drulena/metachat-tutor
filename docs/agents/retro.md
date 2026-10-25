# Retro

Append-only, one session per section, newest first. Sessions run `/retro` at
close; the findings feed the standards docs and the next session's start.

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
