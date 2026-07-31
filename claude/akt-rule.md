# Agent Knowledge Toolkit (AKT) — automatic recall & capture

These rules apply in every repo. They are no-ops when AKT isn't set up, so they never block work.

## Before starting a non-trivial coding task

Recall relevant past work first, and use it:

1. Run `akt recall "<one-line description of the task>"` — it prints up to 3 relevant past story paths (relative to the knowledge base), each with its summary line indented beneath it. Use the summaries to skip clearly irrelevant matches without reading them.
2. Read each relevant `story.md` (resolve paths against `knowledge_base_path` in `~/.claude/akt-config.md`) and factor the prior decisions, gotchas, and rejected alternatives into your plan **before** writing code.

When the task is "pick up where we left off" rather than a describable problem, run `akt latest <repo>` instead — it prints the most recent story for that repo.

Skip recall for trivial work (typo fixes, one-liners, pure questions).

## When a meaningful chunk of work wraps up (feature / fix / PR-sized)

Capture it so the decision is recorded for next time:

1. If a story isn't already open, run `akt start-story <repo> "<short title>"` (`<repo>` = basename of the repo root).
2. Distill the work into `story.md` and index it via `akt finish-story <story_path> --stdin`, including the **key decision → because → rejected alternative**. The finish-story flow commits (and pushes, if a remote is set) the knowledge base.
3. Learnings pass: run `akt learn list --status candidate` and compare this story's transferable lessons — matches get `akt learn reinforce <id> --story <repo>/<date>-<slug>`, new ones get `akt learn add`. Relay any `PROPOSE:` line to the user verbatim and act on their answer (`akt learn graduate <id>` / `akt learn wont <id>`); a REPO-LOCAL graduation also means appending the printed rule block to this repo's `AGENTS.md`/`CLAUDE.md` and committing it with the work.

Skip capture for trivial/throwaway edits.

### Continue a story vs start a new one

- **Continue** (append via `akt update-story <story_path> --stdin`) when the work advances the same problem: follow-ups, iterations, new versions of the same deliverable, the next back-and-forth in an ongoing engagement thread. It appends a dated `## Update` section and commits/pushes in one call.
- **Start new** (`akt start-story`) when the problem statement changes — a decision that stands on its own and would be recalled independently, even if it arose in the same thread or repo. Link the stories under `## Links`.
- Unsure? Ask "would someone search for this on its own?" — yes → new story; no → update.

## Graceful no-op

If `akt` is not on `PATH`, `~/.claude/akt-config.md` has no `knowledge_base_path`, or recall returns nothing, proceed silently. Never error, block, or nag about AKT.
