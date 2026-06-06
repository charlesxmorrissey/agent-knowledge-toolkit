---
description: Surface relevant past stories before starting work
allowed-tools: Bash, Read
---

# Recall

Given the task you are about to start, surface relevant prior decisions.

1. Run:
   ```bash
   python3 -m akt recall "<one-line description of the task>"
   ```
   It prints up to 3 story paths (relative to the knowledge base).
2. Resolve each against `knowledge_base_path` (from `~/.claude/akt-config.md`) and Read the `story.md`.
3. Judge true relevance yourself — keyword overlap is only a prefilter. Summarize the prior decisions that actually bear on this task before proceeding.
