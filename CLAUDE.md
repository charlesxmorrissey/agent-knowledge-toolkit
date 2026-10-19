## Graduated learnings (AKT)

Repo-local rules promoted by `akt learn graduate` (all evidence in this repo).
Cross-repo rules live in the knowledge base's `AGENTS.md`.

- When a process needs two steps and agents silently skip the second (e.g. write then commit), make it one atomic operation instead of a documented follow-up step.
  <!-- akt: atomic-operations-not-agent-memory | 3 hits | agent-knowledge-toolkit/2026-07-04-atomic-capture-finish-story-commits-dirty-warning, agent-knowledge-toolkit/2026-07-30-update-story-latest-recall-summaries-from-first-real-world-use, agent-knowledge-toolkit/2026-10-04-end-session-commits-and-pushes-the-handoff-like-its-siblings -->
- Whatever a CLI's read command prints must be accepted verbatim as input by its sibling write commands — normalize path/id shapes at the CLI boundary instead of documenting two forms
  <!-- akt: cli-output-roundtrips-as-input | 3 hits | agent-knowledge-toolkit/2026-08-02-path-prefix-normalization-and-learn-add-flag-aliases, agent-knowledge-toolkit/2026-09-04-finish-story-stdin-keeps-complete-body-start-story-prints-kb-relative-path, agent-knowledge-toolkit/2026-10-11-update-story-and-learn-story-accept-the-knowledge-stories-pointer-form-session-notes-carry -->

## Resume extras

Releases on this repo are made by hand: a `vX.Y.Z` tag plus a GitHub release. A merge made outside a session does not release itself, so check at session start:

1. Run `git describe --tags --abbrev=0` to get the last tag.
2. Run `git log --oneline <tag>..main`.
3. If any commit since the tag is a fix or a feature, report it as "unreleased: N commits since <tag>" and offer to cut the next version.
