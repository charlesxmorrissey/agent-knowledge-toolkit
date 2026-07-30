---
description: Surface relevant past stories before starting work
allowed-tools: Bash, Read
---

# Recall

Given the task you are about to start, surface relevant prior decisions.

1. Run:
   ```bash
   akt recall "<one-line description of the task>"
   ```
   It prints up to 3 story paths (relative to the knowledge base), each with its
   summary line indented beneath it. (For "pick up where we left off" with no real
   query, use `akt latest <repo>` instead.)
2. Use the summaries to drop clearly irrelevant matches for free. Resolve the rest
   against `knowledge_base_path` (from `~/.claude/akt-config.md`) and Read the `story.md`.
3. Judge true relevance yourself — keyword overlap is only a prefilter. Summarize the prior decisions that actually bear on this task before proceeding.
