---
description: Write a session handoff so the next agent picks up cleanly
allowed-tools: Bash
---

# End Session

Write a concise handoff for the next agent on THIS story, then persist it.

Pipe the handoff (State / Done / Next / Watch out) into the CLI, which numbers the file:

```bash
python3 -m akt end-session <story_path> <<'EOF'
# Session N

State: <where things stand>
Done: <what this session accomplished>
Next: <immediate next steps>
Watch out: <blockers / open questions>
EOF
```
