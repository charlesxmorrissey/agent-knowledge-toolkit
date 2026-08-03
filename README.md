```
 █████╗ ██╗  ██╗████████╗
██╔══██╗██║ ██╔╝╚══██╔══╝
███████║█████╔╝    ██║
██╔══██║██╔═██╗    ██║
██║  ██║██║  ██╗   ██║
╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
```

# Agent Knowledge Toolkit

A personal, git-backed knowledge base for coding agents. AKT captures the _why_
behind your work — decisions, rationale, and per-session handoffs — and surfaces
the relevant pieces back to a future agent when it starts a related task, across
all your repos.

![AKT demo — capture a decision, then recall it across repos](demo/akt-demo.gif)

The premise: a coding agent's biggest gap isn't the code, it's the **context** —
why something was built the way it was, what was tried and rejected, what to watch
out for. AKT makes capturing that nearly free, and — more importantly — makes it
**discoverable** at the moment a new task begins.

> **Status: kernel MVP.** This is the portable core — capture + recall + continuity.
> The planning/workflow toolkit and plugin distribution are designed but not yet
> built (see [Status & roadmap](#status--roadmap)).

## How it works

- **Markdown is the source of truth.** Every unit of work is a `story.md` with a
  little frontmatter, plus lightweight `sessions/NN.md` handoffs. Plain files in a
  git repo — portable, diffable, tool-agnostic.
- **`INDEX.md` is a derived cache.** One line per story (decision + keywords + path),
  regenerated from the stories — never hand-edited. It's what makes recall fast and
  is safe to delete and rebuild.
- **Recall is a seam.** Given a task description, recall returns the most relevant
  story paths. Today that's keyword scoring over `INDEX.md`; it can be swapped for
  embeddings later **without changing any stored artifact**.
- **Capture is a byproduct.** You don't hand-write knowledge. The lifecycle commands
  prompt the agent to record the handoff/decision at the moment it already has the
  context in head.

Three tiers: `sessions/` (transient) → `story.md` (durable, per-task) → `AGENTS.md`
(durable, global rules), with `INDEX.md` as the lens over the middle tier.

## Requirements

- Python 3.9+ (standard library only — no third-party dependencies)
- git

## Install

Zero-install — clone and run as a module from the repo:

```bash
git clone https://github.com/charlesxmorrissey/agent-knowledge-toolkit.git
cd agent-knowledge-toolkit
python3 -m akt --help
```

### Use it from any repo (recommended)

One command symlinks everything into place — the `akt` launcher onto your `PATH`
(`~/.local/bin/akt`), the slash commands into `~/.claude/commands/`, and the
auto-recall rule as `~/.claude/AKT.md` (imported from `~/.claude/CLAUDE.md`):

```bash
python3 -m akt install
```

Because they're symlinks, `git pull` in this repo updates the global install —
no re-copy step, ever. The installer is idempotent and never clobbers a real
file (it warns and leaves it; remove the file and re-run to link). After this,
`akt …` and the `/recall`, `/start-story`, `/end-session`, `/update-story`,
`/finish-story` slash commands work in every repo, and the auto-recall rule
tells the agent to recall relevant past stories before a non-trivial task and
capture the story when meaningful work wraps up — a no-op when AKT isn't
configured. (It's agent-instructed, not a hard hook, so it's smart and
low-noise but not 100% deterministic.)

To uninstall, remove the symlinks and the import line:
`rm ~/.local/bin/akt ~/.claude/AKT.md ~/.claude/commands/{recall,start-story,end-session,update-story,finish-story}.md`
and delete the `@AKT.md` line from `~/.claude/CLAUDE.md`.

Finally, initialize a knowledge base (a standalone git repo you keep wherever
you like — git-backing it gives you history and cross-machine sync):

```bash
akt init ~/knowledge
```

This scaffolds the knowledge base and records its path in `~/.claude/akt-config.md`
(override the config location with the `AKT_CONFIG` environment variable).

## Quick start

### If you use Claude Code — you're already done

With `akt install` and `akt init` run (above), the agent drives the whole
lifecycle itself:

1. **You start a task** → the agent recalls relevant past stories and reads
   them before writing code.
2. **You ship a feature/PR** → the agent distills what was decided (and why)
   into a story and commits it to the knowledge base.

Just work normally; the knowledge base accrues as a byproduct. You can also
invoke any step by hand with the slash commands (`/recall`, `/start-story`,
`/finish-story`, …) — see [Slash commands](#slash-commands-claude-code).

### The CLI underneath

The slash commands wrap a plain CLI — use it directly with other agents,
scripts, or by hand. A story's life, start to payoff:

```bash
# 1. Start a story (one per feature/PR). Prints the story directory.
STORY=$(akt start-story webapp "Auth token refresh" --date 2026-06-05)

# 2. Stopping mid-story? Leave a handoff for the next session:
akt end-session "$STORY" <<'EOF'
Done: moved refresh to lazy-on-401
Next: add tests
Watch out: token clock skew
EOF

# 3. Work done — write the distilled record, index it, and commit (+ push)
#    the knowledge base, all in one call:
akt finish-story "$STORY" --stdin <<'EOF'
---
repo: webapp
slug: auth-token-refresh
date: 2026-06-05
summary: Moved refresh from cron to lazy-on-401 to stop thundering-herd reauth
keys: auth, token, rate-limit, webapp
---
## Problem
Cron-based refresh caused thundering-herd reauth.
## Decisions
- Lazy refresh on 401 — because cron drift synchronized clients — rejected fixed-interval cron
## Outcome
Reauth storms gone; watch clock skew.
EOF

# 4. Weeks later, on a related task — the payoff:
akt recall "how do I refresh an auth token"
# -> stories/webapp/2026-06-05-auth-token-refresh/story.md
#        Moved refresh from cron to lazy-on-401 to stop thundering-herd reauth
```

Two more you'll want eventually: `akt update-story "$STORY" --stdin` appends a
dated update when the same thread continues, and `akt latest webapp` resumes
the most recent story for a repo without inventing a query. (`--date` defaults
to today; it's pinned above only so the paths in the example line up.)

## Commands

### CLI (`akt <command>` — or `python3 -m akt` from the repo without the launcher)

| Command                                                 | What it does                                                                                                                                                     |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `install`                                               | Symlink the launcher, slash commands, and auto-recall rule into `~/.local/bin` and `~/.claude` (idempotent; never clobbers real files)                           |
| `init <path>`                                           | Create a knowledge base at `<path>` and record it in config                                                                                                      |
| `start-story <repo> "<title>" [--date YYYY-MM-DD]`      | Scaffold a story dir with `story.md` and an empty `sessions/`; prints the path                                                                                   |
| `end-session <story_path>`                              | Write the next `sessions/NN.md` handoff (body from stdin); the first is `01.md`                                                                                  |
| `finish-story <story_path> --stdin`                     | Validate + write the distilled `story.md` (from stdin), append its `INDEX.md` line, and commit the knowledge base (pushing if a remote exists) — one atomic step |
| `update-story <story_path> --stdin [--date YYYY-MM-DD]` | Append a dated `## Update` section to an existing `story.md` (from stdin) and commit the knowledge base — for the next capture in an ongoing thread              |
| `recall "<query>" [--limit N]`                          | Print the most relevant story paths for a task (default 3), each with its summary indented beneath                                                               |
| `latest <repo>`                                         | Print the most recent story path (+ summary) for a repo — resume without inventing a query                                                                       |
| `reindex`                                               | Rebuild `INDEX.md` from all `story.md` files                                                                                                                     |

#### `akt learn` — evidence ledger

| Subcommand                                       | What it does                                     |
| ------------------------------------------------ | ------------------------------------------------ |
| `add <id> "<rule>" --story <repo>/<date>-<slug>` | New candidate at hits 1                          |
| `reinforce <id> --story <repo>/<date>-<slug>`    | Bump hits; prints `PROPOSE:` at threshold        |
| `graduate <id>`                                  | Promote; global scope also writes KB `AGENTS.md` |
| `wont <id>`                                      | Mark wont-graduate; stops proposals              |
| `list [--status STATUS]`                         | Print the ledger                                 |
| `prune`                                          | Print-only staleness report                      |

### Slash commands (Claude Code)

`.claude/commands/` provides thin wrappers that add the model judgment around the CLI:

- `/start-story` — begin a story for the current repo
- `/end-session` — write a session handoff
- `/update-story` — append a dated update to an open story and commit it
- `/finish-story` — distill the story, index it, and commit + push the knowledge base
- `/recall` — surface and judge relevant past stories before starting work

With the optional auto-recall rule installed (above), the agent runs `/recall` and
`/finish-story` on its own — you don't have to invoke them.

## Knowledge base layout

```
knowledge/
  stories/
    <repo>/<date>-<slug>/
      story.md          # source of truth: problem, decisions + why, outcome
      sessions/        # handoffs, created only by /end-session (empty for single-session stories)
        01.md          #   01.md, 02.md, … appear when you end a session mid-story
  AGENTS.md             # global rules (graduated patterns — future work)
  INDEX.md              # derived search cache (regenerable; do not hand-edit)
```

`story.md` is intentionally tight; the high-value payload is the
**decision → because → rejected-alternative** line, the thing an agent can't
recover by reading code.

## Testing

```bash
python3 -m unittest discover -s tests
```

## Status & roadmap

**Shipped:**

- Kernel — `recall`, capture lifecycle (`start-story` / `end-session` / `finish-story`),
  `INDEX.md`, `reindex`, config, `init`.
- `akt` launcher + global slash commands — use it from any repo.
- `finish-story` commits **and pushes** the knowledge base in the same call — capture is
  atomic, with no separate commit step to forget. `recall` / `start-story` warn (on stderr)
  when the KB has uncommitted changes, so a half-saved story never rots silently.
- Optional auto-recall/capture rule (`claude/akt-rule.md`) — the agent runs recall before
  a task and captures a story when work wraps, without you invoking anything.
- Lessons from first heavy real-world use: `update-story` (mid-engagement appends, atomic
  commit), `latest <repo>` (resume without inventing a query), recall output with summaries,
  and a documented continue-vs-new-story convention.
- `akt install` — one-command, symlink-based setup: launcher, slash commands, rule file,
  and the `@AKT.md` import, idempotently. `git pull` updates the global install; no sync step.
- Learning protocol — recurring lessons accrue evidence in LEARNINGS.md via a capture-time
  pass, and graduate (through a y/n gate, with provenance) into repo-local or global
  AGENTS.md rules that auto-load in every session; /mine-learnings bootstraps the ledger
  from existing stories.

**Next, in build order (see `docs/superpowers/`):**

1. **Planning / workflow toolkit** — swarm planning as a swappable default, plus
   PR and daily-status automations, all layered on the kernel via two touchpoints
   (`recall` before work, `finish-story` after).
2. **Distribution** — a Claude Code plugin for public distribution (`akt install`
   covers single-user setup; the plugin is the answer for versioned, multi-user installs).

## Design docs

- Design spec: [`docs/superpowers/specs/2026-06-05-agent-knowledge-toolkit-design.md`](docs/superpowers/specs/2026-06-05-agent-knowledge-toolkit-design.md)
- Kernel implementation plan: [`docs/superpowers/plans/2026-06-05-akt-kernel-mvp.md`](docs/superpowers/plans/2026-06-05-akt-kernel-mvp.md)
- Learning protocol design: [`docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md`](docs/superpowers/specs/2026-07-30-akt-learning-protocol-design.md)
