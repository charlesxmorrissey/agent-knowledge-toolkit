---
description: Distill the finished story and add it to the index
allowed-tools: Bash, Read
---

# Finish Story

1. Read all `sessions/NN.md` under `<story_path>/sessions` and the work's diff.
2. Write the distilled `story.md` body. It MUST include frontmatter and the required sections:
   ```
   ---
   repo: <repo>
   slug: <slug>
   date: <YYYY-MM-DD>
   summary: <the key decision + because, one line — this is what recall matches on>
   keys: <comma, separated, keywords>
   ---
   ## Problem
   ## Decisions
   - <decision> — because <why> — rejected <alternative>
   ## Outcome
   ## Links
   ```
3. Pipe it in; the CLI validates required sections + non-empty summary, then appends the INDEX.md line:
   ```bash
   akt finish-story <story_path> --stdin <<'EOF'
   <the full story.md content above>
   EOF
   ```
4. Commit the knowledge repo (the `knowledge_base_path`), e.g. `git -C <kb> add -A && git -C <kb> commit -m "story: <repo>/<slug>"`.
