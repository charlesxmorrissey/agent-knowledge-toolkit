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
   It prints the created story directory and seeds `story.md` + `sessions/01.md`.
3. Keep brief notes as you work; you will hand them off with `/end-session`.
