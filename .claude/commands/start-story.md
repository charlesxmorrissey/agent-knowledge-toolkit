---
description: Start a new story in the knowledge base
allowed-tools: Bash
---

# Start Story

1. Run `akt repo` for the current repo name (in a git worktree it prints the name of the main
   checkout, not of the worktree directory) and choose a short title for the task.
2. Run:
   ```bash
   akt start-story <repo> "<short title>" [--keys a,b,c]
   ```
   It prints the created story directory (relative to the knowledge base, the same
   form `recall` prints and `finish-story`/`update-story` accept) and seeds `story.md` (handoffs are
   written later via `akt end-session`, which creates `sessions/` on first use).
3. Keep brief notes as you work; capture them at session end with `/wrap`.
