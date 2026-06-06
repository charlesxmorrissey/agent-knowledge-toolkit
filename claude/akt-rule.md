# Agent Knowledge Toolkit (AKT) — automatic recall & capture

These rules apply in every repo. They are no-ops when AKT isn't set up, so they never block work.

## Before starting a non-trivial coding task

Recall relevant past work first, and use it:

1. Run `akt recall "<one-line description of the task>"` — it prints up to 3 relevant past story paths (relative to the knowledge base).
2. Read each returned `story.md` (resolve paths against `knowledge_base_path` in `~/.claude/akt-config.md`) and factor the prior decisions, gotchas, and rejected alternatives into your plan **before** writing code.

Skip recall for trivial work (typo fixes, one-liners, pure questions).

## When a meaningful chunk of work wraps up (feature / fix / PR-sized)

Capture it so the decision is recorded for next time:

1. If a story isn't already open, run `akt start-story <repo> "<short title>"` (`<repo>` = basename of the repo root).
2. Distill the work into `story.md` and index it via `akt finish-story <story_path> --stdin`, including the **key decision → because → rejected alternative**. The finish-story flow commits (and pushes, if a remote is set) the knowledge base.

Skip capture for trivial/throwaway edits.

## Graceful no-op

If `akt` is not on `PATH`, `~/.claude/akt-config.md` has no `knowledge_base_path`, or recall returns nothing, proceed silently. Never error, block, or nag about AKT.
