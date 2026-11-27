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
     `akt finish-story <story_path> --stdin --summary "..." --keys a,b,c`
     (the body on stdin, the summary and keys on the flags — one call).
     Link related stories under `## Links` as relative markdown links,
     `[<repo>/<date>-<slug>](../../<repo>/<date>-<slug>/story.md)`.
   - Mid-story with nothing distillable yet → leave a handoff instead:
     `akt end-session <story_path>` with State / Done / Next / Watch out
     on stdin (commits + pushes in the same call, like `update-story`).
   - Work landed in sibling repos but the record is in this story →
     `akt drift <story_path> --repos a,b --pointer` appends a pointer update
     to each sibling story flagged `stale`, so a session started there finds
     this story. A sibling whose newest update already names it prints
     `pointer skipped` and is left alone: that is the expected result, not
     a failure, so do not run it again.
2. **Learnings pass**: run `akt learn match "<lesson>" "<lesson>"` with one
   quoted argument per transferable lesson from the session — it prints the
   closest ledger entries under each lesson. The same lesson in different
   words is a match and gets
   `akt learn reinforce <id> --story <repo>/<date>-<slug>` (also when the
   entry is already graduated); a lesson with no real match gets
   `akt learn add <id> "<rule>" --story <repo>/<date>-<slug> --lesson "<lesson>"`,
   where `<lesson>` is the same text you passed to `match`. Relay any
   `PROPOSE:` line to the user verbatim and act on the answer
   (`akt learn graduate <id>` / `akt learn wont <id>`). For a GLOBAL
   proposal also ask whether the rule should load in every session: yes means
   `akt learn graduate <id> --core`, for a rule that applies in any repo or
   guards an action that is hard to undo; without `--core`, `akt recall`
   prints the rule when a task matches. A REPO-LOCAL
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
