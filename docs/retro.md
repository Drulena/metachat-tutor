# Retro

Append-only log of coding-agent and human sessions on this repo. Newest section
first, appended under this header; section shape from
`docs/templates/retro-section.md`. One line per bullet, longer only when the
cause needs explaining; test results in prose, not a log.

## 2026-11-01 — #32 Session ID behind an info button (agent)

### Session

- Implemented issue #32: the Session ID left the menu as plain text and became an
  info button on the Participant row (hover/focus reveal, click to copy). Commits
  `2ae85e3` (fragment + CSS + handlers + 7 tests) and `ea5e6fa` (review fixes) on
  branch `django`; `manage.py test tutor` → Ran 207 tests, OK. Not pushed.

### What worked

- `docs/agents/coding-standards.md:50-51` — "a rendered-page test (assert the
  words absent from the response)" — is what made the privacy claim testable: the
  test asserts on visible text (`_visible_text` strips script/style then every
  tag), because an assertion on the raw body passes while the id is on screen.
  Keep the rule; it also caught the shape of the bug the rule warns about.
- The template/CSS pairing rule is checkable from a diff alone: the review axis
  caught `transition: … box-shadow` on a button that has no box-shadow state.

### Where I got stuck

- One red run: asserting the bare string `.session-id-btn` passed on an
  **unregistered** page, because `chat.html`'s inline JS contains the same
  selector string. Only tag-shaped assertions (`<p class="participant-row">`,
  `<button type="button" class="session-id-btn"`) fail when they should.
- Reveal/copy behaviour has no test: `.revealed` is added by JS, and there is no
  DOM harness, so tests can prove only that the handler ships. Verified by hand
  (`node --check` on the extracted script block).
- `docs/retro.md` and `docs/templates/retro-section.md` did not exist:
  `docs/agents/retro.md` points at both. This is the file's first section, and the
  template was created to match it.

### Tool gaps

- `git`, `gh` and `venv\Scripts\python.exe` all fail under the workspace-write
  sandbox with `failed to run git: pipe: Access is denied.` Every one needs an
  explicit full-access escalation (six in this session), and the working pattern
  is written nowhere, so each session rediscovers it.
- Multi-line `git commit -m` dies under `sh.exe`; the workaround is a message
  file + `git commit -F`. `.git/` still carries `COMMIT_MSG_14`,
  `COMMIT_MSG_22.txt`, `COMMIT_MSG_22_a/b/c.txt`, `COMMIT_MSG_TMP` — at least
  three earlier sessions paid this toll, and no doc records it.
- The documented test command `docs/agents/coding-standards.md:66`
  (`.\venv\Scripts\python.exe manage.py test tutor`) is eaten by bash.
  `MSYS_NO_PATHCONV=1 ./venv/Scripts/python.exe manage.py test tutor` is the form
  that runs.
- No `package.json`, no jsdom/playwright: the chat page's inline JS is limited to
  `node --check` on the extracted `<script>` block plus string assertions. The
  recipe is recorded nowhere, so it is re-derived per session.
- `/code-review` asks for two parallel sub-agents; in this harness a subagent
  returns no report (its tool calls arrive as literal text; active child limit 1),
  so both axes ran inline in the implementation context, under context pressure
  the skill says the reviewer should not carry.
- The deck_ plugin tools did the whole issue lifecycle (claim, read, body, close,
  report) with no escalation; `gh` needs one. `gh issue view --json` has no
  `dependencies` field — dependency reads go through `gh api`, as
  `docs/agents/issue-tracker.md` already says.

### Repo gaps

- The pairing rule has no automated check: no test in `tutor/` mentions
  `style.css`. A test that renders `menu.html`, `chat.html` and
  `main_menu.html` and diffs their class tokens against
  `tutor/static/tutor/style.css` selectors would catch the bug class the rule
  warns about (`docs/agents/coding-standards.md`, issues #21/#26). It fails today
  on `progress-text` (`tutor/templates/tutor/menu.html:21`, unstyled before this
  change), so land it with an allow-list or style that class first.
- The `{# … #}` single-line rule (a multi-line block comment renders as literal
  page text) is prose-only as well. One assertion — the rendered pages' visible
  text contains no `{#`, `{{` or `{%` — covers both traps for the price of one
  test.
- `tutor/templates/tutor/menu.html:4` says "Reusable menu fragment" without naming
  its two includers (`chat.html:15`, `chat.html:84`) or that `/menu/` renders
  `main_menu.html` instead. Finding the right template for a menu change cost a
  grep sweep.
- `progress-text` is still unstyled: worth its own ticket.

### Standards gaps

- View tests on pages that carry inline JS must assert **tag-shaped** markup, not
  bare class or selector strings: the script block contains the same names.
- Record the inline-JS verification recipe (extract the `<script>` block,
  `node --check`, string-assert the handlers ship) and say plainly that no DOM
  harness exists, so reveal/copy behaviour is manual QA.
- Put the escalation and path facts (git, gh, `venv` python; bash-safe
  `./venv/…` with `MSYS_NO_PATHCONV=1`) in `docs/agents/coding-standards.md`, not
  in `AGENTS.md`.
- When a ticket asks to hide a value, the review must say **where** the value is
  rendered — element text vs attribute — not just that it is hidden. Issue #32's
  id is off the page text but is served as `data-session-id` on the button.
