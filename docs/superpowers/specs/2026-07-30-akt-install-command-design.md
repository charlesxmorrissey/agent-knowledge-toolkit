# `akt install` — one-command setup (design)

**Date:** 2026-07-30
**Status:** implemented (`akt install`, akt/install.py)

## Problem

Installing AKT is five manual steps (symlink the launcher, copy five command
files, copy the rule file, add the `@AKT.md` import, `akt init`). Worse, the
copy-based steps go stale: every change to the command files or rule requires
re-copying to `~/.claude/` by hand — a sync step that was forgotten-prone and
had to be done manually after PR #13 merged.

Audience: primarily the author setting up their own machines. Not building for
public distribution (a Claude Code plugin stays on the roadmap for that).

## Decision

Add an `install` subcommand to the existing CLI, and switch from copies to
**symlinks** so the global install tracks the repo live (`git pull` = updated
everywhere, no sync step ever again).

- `akt install` (or `python3 -m akt install` from a fresh clone, before the
  launcher is on PATH) performs, idempotently:
  1. Symlink `bin/akt` → `~/.local/bin/akt`.
  2. Symlink each `.claude/commands/*.md` (recall, start-story, end-session,
     update-story, finish-story) → `~/.claude/commands/<name>.md`.
  3. Symlink `claude/akt-rule.md` → `~/.claude/AKT.md`.
  4. Append `@AKT.md` to `~/.claude/CLAUDE.md` if that line isn't already
     present (create the file if missing).
  5. Warn (stderr) if `~/.local/bin` is not on `PATH`.
- Repo root is derived from `__file__`, so any clone location works.
- `akt init <path>` remains a separate step (it creates the knowledge base;
  install configures the toolkit). README quick-setup becomes:
  clone → `python3 -m akt install` → `akt init ~/knowledge`.

### Because / rejected

- **Python subcommand, not `install.sh`** — because the repo is one-language
  stdlib Python with a unittest culture, and idempotency/no-clobber paths
  deserve real tests — rejected a shell script (second language, untested by
  convention).
- **Symlinks, not copies** — because copies drift and demand a manual re-sync
  after every rule/command change — rejected copy + re-run-installer (the sync
  step still exists). Accepted trade-off: a half-finished repo edit is live
  globally; acceptable for a single-user install where the repo is usually on
  `main`.
- **Not a Claude Code plugin** — because plugin caches version+copy files
  (fighting the live-symlink model), it ties AKT to one agent, and it's
  machinery for an audience of one — rejected for now, remains the roadmap
  answer for serious public distribution.

## Safety / idempotency rules

For each symlink target:

- Already the correct symlink → skip silently.
- A symlink pointing elsewhere → replace (it's stale, we own the name).
- A **real file or directory** → leave untouched, warn on stderr. Never
  destroy something the installer didn't create. (First run on a machine with
  the old copy-based install will warn on each copied file; the warning tells
  the user to remove the file and re-run.)

Each action performed prints one status line. Always exit 0 — warnings on
stderr carry the signal (consistent with AKT's graceful-no-op ethos).

## Testing

Unit tests with `HOME` pointed at a temp dir (matching the existing
`AKT_CONFIG` test pattern): fresh install creates all links + import line;
second run is a no-op; real-file collision warns and leaves the file; import
line is not duplicated.

## Out of scope (deliberately)

- `akt uninstall` — it's `rm` on a handful of symlinks; document in README
  instead.
- `--dry-run`, Windows support, version pinning, plugin packaging.

## Docs to update on implementation

- README "Use it from any repo" section → the three-line setup.
- README roadmap: move installer from "Next" to "Shipped"; note the plugin
  remains the future public-distribution path.
