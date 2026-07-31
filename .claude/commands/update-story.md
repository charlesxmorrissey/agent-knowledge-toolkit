---
description: Append a dated update to an open story and commit it
allowed-tools: Bash, Read
---

# Update Story

For mid-engagement captures on an already-finished story — the next back-and-forth in
the same thread, not a new decision (a new decision gets `/start-story`; see the
continue-vs-new convention in the AKT rule).

1. Write the update body: what changed since the last section, any new
   **decision — because — rejected alternative**, and gotchas.
2. Pipe it in. The CLI appends a `## Update — <date>` section to `story.md` **and
   commits the knowledge base** (pushing if a remote exists) in the same invocation:

   ```bash
   akt update-story <story_path> --stdin <<'EOF'
   <the update body>
   EOF
   ```

   The commit status is printed to stderr and never fails the flow when offline.

3. **Learnings pass** — after the story commit:
   - Run `akt learn list --status candidate`.
   - For each transferable lesson in the story you just captured (a gotcha or
     decision that would help on a future task): if it matches an existing
     candidate — same lesson in different words counts — run
     `akt learn reinforce <id> --story <repo>/<date>-<slug>`; if it's new, run
     `akt learn add <kebab-id> "<rule as one instruction sentence, no '|'>" --story <repo>/<date>-<slug>`.
   - If any command printed a `PROPOSE:` line, relay it to the user verbatim
     and act on their answer: `akt learn graduate <id>` (for a REPO-LOCAL
     proposal, also append the printed rule block to _this_ repo's
     `AGENTS.md`/`CLAUDE.md` and commit it with the work) or `akt learn wont <id>`.
   - Project-specific quirks with no transfer value get no entry. Skip the
     pass entirely if `akt` reports no ledger and no KB.
