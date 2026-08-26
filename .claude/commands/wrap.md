---
description: End of session — capture the story, run the learnings pass, push the knowledge base
allowed-tools: Bash
---

# Wrap

End-of-session routine. Do these in order:

1. **Story capture**: distill the session's work — decisions
   (decision → because → rejected alternative), gotchas, what's left open.
   - Same thread continuing → `akt update-story <story_path> --stdin`
     (appends a dated `## Update` and commits + pushes in one call).
   - The problem statement changed (a decision that would be recalled on its
     own) → `akt start-story <repo> "<short title>"` then
     `akt finish-story <story_path> --stdin`. Link related stories under
     `## Links`.
   - Mid-story with nothing distillable yet → leave a handoff instead:
     `akt end-session <story_path>` with State / Done / Next / Watch out
     on stdin.
2. **Learnings pass**: run `akt learn list --status candidate --compact` and
   compare the session's transferable lessons (full text of a likely match via
   `akt learn show <id>`) — matches get
   `akt learn reinforce <id> --story <repo>/<date>-<slug>`, new ones
   `akt learn add <id> "<rule>" --story <repo>/<date>-<slug>`. Relay any
   `PROPOSE:` line to the user verbatim and act on the answer
   (`akt learn graduate <id>` / `akt learn wont <id>`); a REPO-LOCAL
   graduation also appends the printed rule block to this repo's
   AGENTS.md/CLAUDE.md, committed with the work.
3. **Repo extras**: if this repo's CLAUDE.md or AGENTS.md has a
   `## Wrap extras` section, execute those steps now (timesheets, trackers,
   repo commit/push policy — anything project-specific).
4. **Safe-exit check**: verify nothing is left hanging — re-run the checks,
   don't assert from memory:
   - `git status --short` clean and branch pushed in this repo AND any other
     repo touched this session (knowledge base included).
   - The session log's last entry is a closed OUT (if this repo keeps one).
   - No background tasks, agents, or watchers still running.
   - No drafts awaiting approval or unposted external comments.
5. **Report**: what shipped, what's left open (waiting-on, unverified
   deploys), the story path it was captured in, and an explicit "safe to
   exit" verdict (or what's still hanging).

A repo that needs a different shape entirely can ship its own
`.claude/commands/wrap.md`; the project-level command shadows this one.
