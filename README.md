```
 █████╗ ██╗  ██╗████████╗
██╔══██╗██║ ██╔╝╚══██╔══╝
███████║█████╔╝    ██║
██╔══██║██╔═██╗    ██║
██║  ██║██║  ██╗   ██║
╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
```

# Agent Knowledge Toolkit

A personal, git-backed knowledge base for coding agents. AKT captures the *why*
behind your work — decisions, rationale, and per-session handoffs — and surfaces
the relevant pieces back to a future agent when it starts a related task, across
all your repos.

![AKT demo — capture a decision, then recall it across repos](demo/akt-demo.gif)

The premise: a coding agent's biggest gap isn't the code, it's the **context** —
why something was built the way it was, what was tried and rejected, what to watch
out for. AKT makes capturing that nearly free, and — more importantly — makes it
**discoverable** at the moment a new task begins.

> **Status: kernel MVP.** This is the portable core — capture + recall + continuity.
> The learning protocol, planning/workflow toolkit, and plugin distribution are
> designed but not yet built (see [Roadmap](#roadmap)).

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

Symlink the launcher onto your `PATH` and copy the slash commands into your global
Claude Code commands directory. No packaging, no virtualenv — the launcher resolves
the toolkit location automatically:

```bash
# from the toolkit repo root:
ln -s "$PWD/bin/akt" ~/.local/bin/akt                 # `akt` works from any directory
cp .claude/commands/{recall,start-story,end-session,finish-story}.md ~/.claude/commands/
```

(Ensure `~/.local/bin` is on your `PATH`.) After this, `akt …` and the `/recall`,
`/start-story`, `/end-session`, `/finish-story` slash commands work in every repo.

### Automatic recall & capture (optional)

So you don't have to remember to run `/recall`, install the rule in
[`claude/akt-rule.md`](claude/akt-rule.md) into your global Claude config. It tells the
agent to recall relevant past stories before a non-trivial task and to capture the story
when meaningful work wraps up — and it's a no-op when AKT isn't configured.

```bash
cp claude/akt-rule.md ~/.claude/AKT.md
# then add an import line to ~/.claude/CLAUDE.md:
printf '@AKT.md\n' >> ~/.claude/CLAUDE.md
```

It's agent-instructed (not a hard hook), so it's smart and low-noise but not 100%
deterministic — the agent may skip recall on borderline-trivial work.

Initialize a knowledge base (a standalone git repo you keep wherever you like —
git-backing it gives you history and cross-machine sync):

```bash
akt init ~/knowledge
```

This scaffolds the knowledge base and records its path in `~/.claude/akt-config.md`
(override the config location with the `AKT_CONFIG` environment variable).

## Quick start

```bash
# Start a story (one per feature/PR). Prints the story directory.
# (--date is optional; it defaults to today. Pinned here so the example is reproducible.)
STORY=$(akt start-story webapp "Auth token refresh" --date 2026-06-05)

# At the end of a working session, write a handoff for the next agent (from stdin):
akt end-session "$STORY" <<'EOF'
State: refactor done
Done: moved refresh to lazy-on-401
Next: add tests
Watch out: token clock skew
EOF

# When the work is done, distill the durable record and index it (from stdin):
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
## Links
EOF

# Later, on a new task, surface relevant prior decisions:
akt recall "how do I refresh an auth token"
# -> stories/webapp/2026-06-05-auth-token-refresh/story.md
```

## Commands

### CLI (`akt <command>` — or `python3 -m akt` from the repo without the launcher)

| Command | What it does |
|---------|--------------|
| `init <path>` | Create a knowledge base at `<path>` and record it in config |
| `start-story <repo> "<title>" [--date YYYY-MM-DD]` | Scaffold a story dir with `story.md` and an empty `sessions/`; prints the path |
| `end-session <story_path>` | Write the next `sessions/NN.md` handoff (body from stdin); the first is `01.md` |
| `finish-story <story_path> --stdin` | Validate + write the distilled `story.md` (from stdin) and append its `INDEX.md` line |
| `recall "<query>" [--limit N]` | Print the most relevant story paths for a task (default 3) |
| `reindex` | Rebuild `INDEX.md` from all `story.md` files |

### Slash commands (Claude Code)

`.claude/commands/` provides thin wrappers that add the model judgment around the CLI:

- `/start-story` — begin a story for the current repo
- `/end-session` — write a session handoff
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
- `/finish-story` auto-commits **and pushes** the knowledge base.
- Optional auto-recall/capture rule (`claude/akt-rule.md`) — the agent runs recall before
  a task and captures a story when work wraps, without you invoking anything.

**Next, in build order (see `docs/superpowers/`):**
1. **Learning protocol** — recurring patterns accrue evidence and graduate into
   repo-local or global `AGENTS.md` rules, with provenance. (Pays off once you've
   accumulated stories and patterns start repeating.)
2. **Planning / workflow toolkit** — swarm planning as a swappable default, plus
   PR and daily-status automations, all layered on the kernel via two touchpoints
   (`recall` before work, `finish-story` after).
3. **Distribution** — a true one-command installer / Claude Code plugin (the launcher +
   manual command copy is the current stopgap).

## Design docs

- Design spec: [`docs/superpowers/specs/2026-06-05-agent-knowledge-toolkit-design.md`](docs/superpowers/specs/2026-06-05-agent-knowledge-toolkit-design.md)
- Kernel implementation plan: [`docs/superpowers/plans/2026-06-05-akt-kernel-mvp.md`](docs/superpowers/plans/2026-06-05-akt-kernel-mvp.md)
