# Retro

Append-only, one session per section, newest first. Sessions run `/retro` at
close; the findings feed the standards docs and the next session's start.

## 2026-11-02 — research admin over the ledger (#35)

Shipped on `django`, 4 commits, unpushed: `/admin/` over the session ledger —
changelist with the ADR's columns, group/level/finished-abandoned filters and a
from/to window on each of the three stamps, the row's page (dialogue + gate
answers, escaped), the `Researcher` group (view-only) and the maintainer's
Delete-selected. 296 → 348 tests, 52 of them in `tutor/test_admin.py`.

### What worked

- **Naming the seam before the loop kept the tests honest.** The admin's own
  HTTP surface (+ the group's permission set) was confirmed with the owner
  first; 52 tests, zero unit tests of my own callables, and the two review
  defects were both found at that surface. Confidence: high.
- **`post_migrate` over a data migration for the researcher group.** A
  migration cannot see the `view_*` permissions (Django writes them in its own
  post-migrate phase), and `AppConfigStub` has no `models_module`, so the
  `create_permissions` recipe fails against the historical apps. The signal
  runs where the permissions exist. Pinned by a test that hand-grants
  `change_sessionrecord`, re-runs `migrate`, and asserts the grant is gone —
  that is the test that makes the mechanism observable. Confidence: high.
- **`__date` extracts as the window's query parameters.** `?created_at__date__gte=2026-01-12`
  needs no timezone arithmetic of my own, is inclusive by local day on SQLite,
  and the URL reads as the question it answers. Confidence: high.
- **The two-axis review found three defects behind 46 green tests** (see
  Friction). Green pins the surface, never the interactions. Confidence: high.

### Friction (the expensive lessons)

- **Three defects the tests did not have a shape for.** (1) `auto_now` + admin
  save: repairing a learner's name moved `updated_at` to today, so the row left
  the "abandoned, last activity before X" window — the cleanup list lost the
  rows the cleanup is for. (2) `Group.name` editable while `lookup_key` was not:
  a hand-rename left the key behind and the next intake typing the new spelling
  minted a second group of the same name (decision 5 split). (3) The Assessment
  list offered `delete_selected` while the session page refused to delete the
  same answer. All three are one theme: the desk was written as if it had write
  rights it was never given. Fixed in `af18541`, each with its test. Confidence: high.
- **Django 5.0.9 is not 5.1.** No `BetweenDateFieldListFilter`, no
  `admin/filter/date_range.html` (the sidebar range arrived in 5.1), no
  `readonly_fields = "__all__"`, `ShowFacets` members are `NEVER/ALLOW/ALWAYS`
  (not `OFF`), `post_migrate` sends `using=` (not `database=`), and a popped
  QueryDict parameter arrives as a **list** — a custom filter must take
  `value[-1]` (the stock filters' rule) or the date field gets a list and the
  changelist 500s. Check the installed source, not the current docs. Confidence: high.
- **This sandbox has no tz database** (`/usr/share/zoneinfo` absent on musl), so
  `ZoneInfo("UTC")` raised on the first template that rendered a timestamp.
  Fixed in the repo: `tzdata==2026.6` pinned as a runtime dependency (Django's
  own guidance for that host class), lock + `requirements.txt` regenerated.
  Confidence: high.
- **uv cannot manage the owner's `.venv` from here** (`failed to remove
  .venv/Scripts`, a Windows-layout venv). Working pattern: `uv add --no-sync` +
  `uv lock` to move pyproject/lock, and run tests with a Linux venv at
  `/tmp/opencode/venv311/bin/python manage.py test tutor`. `.venv/` was not
  gitignored (only the pre-uv `venv/`), so `add -A` could sweep an environment
  into a commit — ignored now. Confidence: high.
- **`test_browser` is red, not green-skip, in this container**: the playwright
  driver needs `fcntl64`, musl has none (issue #49). Baseline before this work
  was the same 5 errors, so the suite's signal stayed readable. Confidence: high.
- **Admin page assertions dump 40 kB** into the report on failure
  (`assertNotIn`/`assertContains` print the container). Fixed with the
  `PageChecks.assert_shows/assert_hides` pair, which carries the reason.
  Confidence: high.
- Git identity is unset in this container (commits died on
  `unable to auto-detect email`); set repo-local, not global. The
  `commit-msg`/`pre-commit` hooks fire fine on Linux — no `--no-verify` needed,
  unlike the Windows harness the earlier retros describe. Subject cap 72 is
  `wc -m` on the line, so count the newline. Confidence: high.

### State

- `django` is 4 commits ahead of `origin/django`: `7800794` tzdata + `.venv`
  ignore, `20cc106` the desk, `e0b2090` README/GLOSSARY, `af18541` the review
  fixes. Unpushed: pushing needs the owner's shell.
- New files: `tutor/admin.py`, `tutor/apps.py`,
  `tutor/templates/tutor/admin/date_range_filter.html`, `tutor/test_admin.py`.
  Settings gained `admin`/`auth`, `AuthenticationMiddleware` and the auth
  context processor; `tutor_project/urls.py` mounts `/admin/`.
- GLOSSARY gained **researcher / maintainer**; README gained the admin section
  and the `createsuperuser` step (the desk cannot be opened without one).
- #35 closed. No migration was added, so the append-only rule is untouched.

### Next time

- Give a real researcher account a run in a browser (the desk has no paint test:
  `test_browser` covers learner pages only, and #49 blocks the driver here).
- The maintainer can still edit `user_name`, `group`, `level`,
  `previous_session` — the ADR's "maintainer: full" read as a repair hatch, and
  the reading is written in the docstrings, the README and the ticket. If the
  owner wants the desk strictly read-only, that hatch is the one line to close.
- The range filter renders its own template; Django 5.1's
  `BetweenDateFieldListFilter` would replace it wholesale on an upgrade — the
  parameters (`<field>__date__gte`) are the part tests pin, so the swap is local.
- `tutor/testing.py`'s intake scaffolding is unused by the admin tests; a
  ledger-row-built-from-a-real-chat admin test would close the last gap between
  the desk and the write path.

## 2026-11-01 — browser paints + uv (#44)

Context: the learner reported a blank page with a green suite. The view tests
assert on bytes; nothing asked a browser to paint. Fixed the one real defect
(the intake and terms titles closed with `>` instead of `</title>`), kept two
guards, and moved browser checking into Django's runner.

### What worked
- Two cheap guards before the browser: `tutor/test_pages.py` parses the head
  (raw-text elements swallow the rest of the document) and pins the five page
  titles. It went red on the exact shipped bug, so it is red-capable.
- `tutor/test_browser.py`: `StaticLiveServerTestCase` + playwright driving the
  installed Edge channel headless; one tab per test; the tab label, the painted
  text, `document.styleSheets` and the computed background must be there, and
  console errors, page errors, failed requests and 4xx answers all fail the run.
- uv took the environment over: `pyproject.toml` + `uv.lock`, playwright pinned
  in the dev group, `requirements.txt` regenerated by `uv export` for pip users.

### Friction (the expensive lessons)
- Playwright's sync API runs its event loop in the calling thread for as long as
  it is started. Django's `SynchronousOnlyOperation` then refuses every database
  call, including the runner's per-test flush. Fix: all browser work on a worker
  thread (`drive` hands the scenario a page, joins, main thread asserts). The
  skip path must stop the driver too — a leaked loop poisoned the whole suite.
- The sandbox denies child processes, so uv, Edge and npm all needed one-off
  `danger-full-access` runs; playwright also writes artifacts to the system temp
  dir, so `TMPDIR`/`TMP`/`TEMP` point at `.scratch/tmp` for the run.
- `templates/tutor/main_menu.html` has no `<main>` landmark (chat, intake, terms,
  reset confirm all have one), so the background probe falls back to `body`.
  Filed as #45 instead of reshaping a page mid-tooling.
- Writing Python from a JS program keeps biting: `add('x') + add('y')` is not a
  line, a JSON `\'` is not an escape, RST double-backticks break template literals.
  The safe form is one `add('...')` per Python line, double-quoted Python strings,
  `chr(34)`/`chr(39)` for quotes inside generated selectors and JS fragments.

### State
- The pip `venv/` is deleted from the working tree: `.venv` (built by `uv sync`) is the only
  environment, and the suite is green without the old directory. `requirements.txt` stays as
  the pip compatibility export - the owner asked for uv as the package manager, with the pip
  path kept alive, after their own drop commit was tidied out of the branch history.
- Suite in uv: `uv run manage.py test tutor` → Ran 267 tests, OK (3 of them
  browser paints, ~12 s with Edge). Commits e627a44, 0915fda, a0a8e25, 69e44da
  on `feat/spec-28-intake-ledger`, not pushed.
- Open: #41 (stale chat on browser back), #43 (a pre-upgrade cookie freezes), #45
  (the missing main landmark), #40/#29/#35/#30/#31.
- Next time: the stale `_GENERIC_REJECTION` copy (tutor/tutor_session.py:92-99)
  still offers commands the module does not route; the transition fixture still
  cannot complete all roles; the owner pushes from their own shell.

## 2026-11-01 — Spec #28 build: intake form + write-through ledger (#36–#39)

Shipped on `feat/spec-28-intake-ledger` (9 commits from `1d63c9c`, **unpushed**):
UUID v7 ids (`tutor/ids.py`) and the greenfield `Group` / `SessionRecord` /
`Assessment` schema; the intake form as the entry state (registration out of the
chat, `/` form, `/chat/` chat, `/terms/` consent); write-through mirroring with
`Assessment` rows and reset chaining; `data_collection` as the terminal screen with
`finished_at` stamped once. Suite 207 → 257 tests OK. Spec #28 and #36–#39 closed.

### What worked

- **Red-first tests caught false premises in my own compressed plans.** A folded
  plan asserted “the registry is already green” while `tutor/test_tutor_session.py:143`
  still pinned `start` and 15 steps; a test expectation miscounted the entry list by
  the welcome turn. Verify repo state before trusting a summary. Confidence: high.
- **One writer module kept the ledger off the hot path.** `tutor/ledger.py` is the
  only place that writes rows; `views._mirror_to_ledger` appends the chat’s own
  entry dicts, so “byte-shape identical to storage” is true by construction, and a
  missing row is a `tutor.ledger` warning, never a learner-visible failure.
  Confidence: high.
- **Conditional UPDATE pins the lifecycle.**
  `filter(finished_at__isnull=True).update(finished_at=timezone.now())` gives
  “stamped exactly once, never cleared” and is race-safe without a read-modify-write
  (the row write for the chat append stays `save(update_fields=[...])`). Confidence: high.
- **The terminal screen needed almost no new code.** Routing already answers any input
  when a row declares `next: None`; the work was one validator rule (`TERMINAL_BASE`),
  the row copy, and deleting the `end` state, its scenario and its registry exception.
  Confidence: high.

### Friction

- **Subagents did zero work on this harness.** Both delegated agents (codebase
  exploration, the #37 implementer) finished with raw tool calls as their closing
  message and left the tree untouched. Every ticket was implemented in-session.
  Confidence: high.
- **Only `run_code` is callable directly** here; read/write/edit/deck/todo calls emitted
  as their own tool blocks render as text and execute nothing. Confidence: high.
- **JS template literals break on RST backticks.** A docstring containing
  `` ``state`` `` closed the literal early (“not a function” / stray Python syntax
  errors). Working pattern: build file content from arrays of single-quoted strings
  joined with `"\n"`; write real emoji, not `\uXXXX` pairs, into Python source (lone
  surrogates → `UnicodeEncodeError`). Confidence: high.
- **Two self-inflicted file corruptions:** slicing by an index computed on a *modified*
  string left debris in `tutor/models.py`; a `read(limit=48)` result used as the whole
  file truncated `tutor/test_write_through.py` (recovered with `git checkout --`).
  Confidence: high.
- **`client.session` is a property that mints a new SessionStore on every access.** A
  test helper that stranded the chat silently lost the write; the Django recipe is to
  write and `save()` on ONE object. Now documented in `tutor/testing.py`. Confidence: high.
- **Git ergonomics:** an early commit swept the whole index (fixed with
  `git reset --soft HEAD~1 && git restore --staged`); `git stash` is unusable (same
  `sh.exe` confinement as the hook), so an intermediate commit is verified in a
  detached worktree inside the workspace with the repo-root venv by absolute path.
  Confidence: high.
- **Two intermediate commits are red by design** (`81e67a6` seam+URL move; `103e067`/
  `8e1ad17` tests+stamp before the flow) because a state rename + URL move is one
  atomic change for the view tests. HEAD is green; the fact is recorded on #37/#39
  rather than hidden. Confidence: high.

### System updates

- `tutor/testing.py`: shared browser scaffolding (`open_intake`, `strand`, `state_of`,
  `entries`) with the session-save recipe in its docstring.
- `tutor/ledger.py` (open / append / record_assessment / fill_reflection / mark_finished)
  and `tutor/ids.py` (`uuid7`).
- Docs: GLOSSARY step count fifteen → fourteen (the #37 residue); ADR-0002 got a dated
  amendment (42 rows, every scenario state rowed); the ADR-0006 2026-11-01 amendment is
  cited from `ENTRY_BASE` / `TERMINAL_BASE` docstrings.
- The `--no-verify` + message-file commit workflow reconfirmed for this sandbox.

### Next time

- Push `feat/spec-28-intake-ledger` (9 commits) from the owner’s shell, then open the
  PR; from the harness a push needs a sandbox escalation.
- #35 (admin over the ledger) needs a superuser: the project has no `auth` in
  `INSTALLED_APPS`, so create one from the shell first. #40 (selector rows + Assessment
  score export), #29 (pretest/posttest as selector forms), #41 (bfcache restores a stale
  chat — re-test there now that reset lands on the intake form).
- Stale copy left untouched: `_GENERIC_REJECTION` still tells learners “In data
  collection, type ‘name <your name>’” and lists `restart`/`export`/`help` commands the
  module does not route. Worth one focused pass with the owner.
- The transition fixture cannot complete all nine roles (the invariant ties
  `current_role` to the single touched role), so `data_collection`'s fixture stays
  single-role even though the screen means “done”.

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
