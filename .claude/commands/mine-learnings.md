---
description: Sweep the knowledge base for recurring lessons and seed/refresh LEARNINGS.md
allowed-tools: Bash, Read
---

# Mine Learnings

Bootstrap or re-sweep the evidence ledger from the story corpus.

1. Resolve the KB path from `knowledge_base_path` in `~/.claude/akt-config.md`.
2. List every story, **oldest first** (dirs sort by date):
   ```bash
   ls -d <kb>/stories/*/*/ | sort -t/ -k+7
   ```
3. For each story, read `story.md` and extract transferable lessons — gotchas,
   decisions, and rules that would help on a future task ("would this help in
   another repo or task?"). Project-specific trivia gets no entry.
4. For each lesson, check the current ledger (`akt learn list`):
   - matches an existing entry (same lesson, any wording) →
     `akt learn reinforce <id> --story <repo>/<date>-<slug> --date <story date>`
   - new → `akt learn add <kebab-id> "<one instruction sentence, no '|'>" --story <repo>/<date>-<slug> --date <story date>`
5. **Batch proposals:** do NOT act on `PROPOSE:` lines mid-sweep. Collect them
   and present all of them to the user at the end; then run
   `akt learn graduate <id>` or `akt learn wont <id>` per their answers.
   For REPO-LOCAL graduations, tell the user the rule block will be added to
   that repo's `AGENTS.md` the next time work happens there (or paste it now
   if the repo is at hand).
