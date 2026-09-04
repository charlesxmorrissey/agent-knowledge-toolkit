---
description: Start a new story in the knowledge base
allowed-tools: Bash
---

# Start Story

1. Determine the current repo name (the basename of the repo root) and a short title for the task.
2. Run:
   ```bash
   akt start-story <repo> "<short title>"
   ```
   It prints the created story directory (relative to the knowledge base, the same
   form `recall` prints and `finish-story`/`update-story` accept) and seeds `story.md` (an empty `sessions/`
   directory is created too; handoffs are written later via `akt end-session`).
3. Keep brief notes as you work; capture them at session end with `/wrap`.
