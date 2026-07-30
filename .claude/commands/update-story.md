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
