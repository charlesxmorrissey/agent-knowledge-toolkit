---
description: Start of session — repo state, latest story, pick up where we left off
allowed-tools: Bash
---

# Resume

Start-of-session routine. Do these in order:

1. **Repo state**: `git log --oneline -5` and `git status --short`.
2. **Open issues**: if the repo has a GitHub remote and `gh` is authenticated, run
   `gh issue list --state open --limit 20` and list anything open (number, title,
   author, age). Skip silently if there is no GitHub remote or `gh` fails — this is
   a surface-it step, not a blocker.
3. **Recall**: run `akt latest <repo>` (`<repo>` = basename of the repo root) —
   it prints the most recently active story path with its summary. Read that
   story (resolve against `knowledge_base_path` in `~/.claude/akt-config.md`).
   Its final section (the last `## Update`, or the newest `sessions/NN.md`
   handoff) is the authoritative "where we left off".
4. **Repo extras**: if this repo's CLAUDE.md or AGENTS.md has a
   `## Resume extras` section, execute those steps now (external trackers,
   time logs — anything project-specific).
5. **Report**: one short summary — current repo state, open threads from the
   story, open issues, anything the extras surfaced — then pick up whatever thread the user
   already named, or ask which one.

A repo that needs a different shape entirely can ship its own
`.claude/commands/resume.md`; the project-level command shadows this one.
