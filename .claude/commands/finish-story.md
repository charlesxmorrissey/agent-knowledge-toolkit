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
3. Pipe it in. The CLI validates required sections + non-empty summary, appends the
   INDEX.md line, **and commits the knowledge base** (pushing if a remote exists) in the
   same invocation — so capture is atomic; there is no separate commit step to forget:
   ```bash
   akt finish-story <story_path> --stdin <<'EOF'
   <the full story.md content above>
   EOF
   ```
   The commit status is printed to stderr. It never fails the flow when there is no
   remote or you're offline (the story is still committed locally).
