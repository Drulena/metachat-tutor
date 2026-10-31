# Retro section template

Copy these bullets into a new `## <date> — <issue/task> (agent|human)` section in
`docs/retro.md`, newest section first. Keep the shape; drop a bullet only when it
is genuinely empty. One line per bullet, longer only when the cause needs
explaining — no session logs, no flattery, no hedging, and specific enough for a
reader who was not in the session.

## <YYYY-MM-DD> — <short task name> (<agent|human>)

### Session

- What was worked on, and the commits/test result that closed it.

### What worked

- Steering that paid for itself (file:line), and the rule worth keeping.

### Where I got stuck

- The moments that cost time, each with its cause, not just the symptom.

### Tool gaps

- Commands, tools or skills that did not work as documented, with the exact error
  text and the working invocation if one was found.

### Repo gaps

- Missing checks, missing files a pointer points at, navigation that misled.

### Standards gaps

- A rule the reviewer should enforce (or drop), phrased as an instruction.
