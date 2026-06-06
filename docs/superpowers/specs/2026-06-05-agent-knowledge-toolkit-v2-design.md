# Agent Knowledge Toolkit v2 — Design

- **Date:** 2026-06-05
- **Status:** Approved design, pre-implementation
- **Type:** Redesign (v1 exists in a separate private repo; treated as input, not target)
- **Scope:** **Personal / single-user.** No team. The user works across multiple of
  their own repos and machines. "Cross-repo" means across the user's own repos;
  the knowledge repo is git-backed for history + cross-machine sync, not sharing.

## Context

A working v1 exists: a git-backed knowledge base capturing planning artifacts,
decision rationale, and agent changelogs per story across repos, plus a toolkit of
commands/skills (swarm planning, PR/daily workflows, a hit-counted learning protocol
that graduates patterns into a shared `AGENTS.md`). This document redesigns it for
**personal use** — a single developer compounding context across their own repos.

## Problem statement

v1 has four pain points, all confirmed:

1. **Too heavy to adopt** — too many files, too much setup ceremony (installing meant
   hand-copying files one screen at a time). For personal use this shows up as: painful
   to stand up on a new machine, and high friction to keep current.
2. **Knowledge goes stale / unread** — the *existential* failure: artifacts get written
   but future agents don't read them. If retrieval doesn't pay off, capture is pure tax.
3. **Learning protocol is weak** — hit-counted graduation into `AGENTS.md` suffers from
   wrong thresholds, bloat, non-generalizing patterns, and low trust.
4. **Too coupled / not portable** — capture is entangled with swarm planning; hard to
   swap tools or run outside the original setup.

**Root cause of #2 (the one that matters most): discovery.** The relevant artifact
exists but never surfaces at the right moment. v1's discovery is a manually-maintained
`_tags.md` registry — it depends on the capturing agent tagging well *and* the future
agent choosing to grep and read. Two opt-in steps, both fragile.

**Priority retrieval problem:** cross-story / cross-repo recall — a *new* task should
surface relevant decisions from past, unrelated stories in any repo. (Intra-story
continuity matters too but is the easier "load latest state" problem.)

### v2 north star

> When an agent starts a task, the relevant prior decisions — from any past story, in
> any repo — surface automatically, without anyone tagging well or remembering to
> search. Capture stays cheap, tool-agnostic, and light to adopt.

## Architecture spine — Hybrid (markdown is truth, the index is a disposable cache)

The central tension: v1 is git-backed markdown (portable, reviewable, no infra — keep
this), but cross-repo semantic recall is exactly what markdown + a manual tag file is
worst at. Resolution:

- **Artifacts stay plain markdown in git** — the source of truth. Portable, diffable,
  tool-agnostic.
- **The search layer is a derived, rebuildable cache** — never the source of truth.
  Day 1 it is a generated `INDEX.md` that the model reads and matches against
  (zero infra). There is a clean seam to swap in embeddings/vector search later
  **without changing any artifact format**.
- **Decouple *what we store* from *how we search*** — this is the architectural mistake
  v1 made, and the fix.

This single choice attacks all four pains: discovery (auto-injection + a real index),
heaviness (markdown + model, no infra to start), coupling (markdown is tool-agnostic),
and it reframes the learning protocol as promoting decisions up an index hierarchy.

## 1. Knowledge model & layout

One **personal knowledge repo** (standalone git, separate from code repos) that agents
in all your repos read and write — this is what makes cross-repo recall possible, and
git-backing it gives you history + cross-machine sync. (v1's `team_base_path`, renamed
to a personal `knowledge_base_path`; kept.)

Collapse v1's five artifact types (planning artifacts, decision rationale, agent
changelogs, session logs, tags) into **two durable types + one derived type**:

```
knowledge/
  stories/
    webapp/2026-06-05-auth-token-refresh/
      story.md          # SOURCE OF TRUTH: problem, key decisions + why, outcome
      sessions/01.md    # continuity handoff (intra-story)
      sessions/02.md
  AGENTS.md             # graduated patterns, global/cross-repo (learning protocol output)
  INDEX.md              # DERIVED/disposable: one line per story → decision + keys + path
```

- **`story.md`** merges decision rationale + agent changelog into one tight per-task
  record. The cross-story recall payload. Answers *why it was built this way*.
- **`sessions/NN.md`** — lightweight handoffs for intra-story continuity. Raw scratch.
- **`AGENTS.md`** — top tier: patterns graduated into global rules (your personal rules,
  applied across all repos). Per-repo rules live in that repo's own `AGENTS.md`.
- **`INDEX.md`** — disposable search cache. Regenerated, never hand-edited. Replaces
  `_tags.md`.

**Three-tier hierarchy:** `sessions` (transient) → `story.md` (durable per-task) →
`AGENTS.md` (durable, global across your repos), with `INDEX.md` as the lens over the
middle tier.

## 2. Discovery & injection (the heart of v2)

**Index line** — one per story, written for single-read fuzzy matching by the model:

```
- [webapp/auth-token-refresh] Moved refresh from cron to lazy-on-401 — cron drift
  caused thundering-herd reauth. keys: auth, token, rate-limit, webapp
  → stories/webapp/2026-06-05-auth-token-refresh/story.md
```

Repo + slug, the decision *and its "because,"* keywords, path. Hundreds fit in one
context read — why the markdown-index approach is viable on day one.

**When recall fires — "push, not pull" (the cure for the discovery pain):**

1. **Mandatory first phase of the planning workflow.** Before any story is planned, the
   agent reads `INDEX.md`, matches against the task, and pulls the top 1–3 `story.md`
   files into context. Automatic — you cannot start planning without it.
2. **A standalone `/recall <topic>` command** for ad-hoc "has anyone touched X?" lookups.

**Deliberately no always-on hook** that injects on every prompt — that is token noise
and reintroduces heaviness. Recall fires at the moment work begins, not constantly.

**Upgrade seam (the C promise, concrete):** recall hides behind one interface —
*"given a task description, return the N most relevant story paths."* Day 1 = model
reads `INDEX.md`. Later = vector query returns the same paths. Capture format and
everything downstream never change.

**Freshness:** `INDEX.md` is regenerated, never hand-edited — a line appended at
`finish-story`, plus a `reindex` command that rebuilds from all `story.md` files.
Because it is derived, drift is fixed by rebuild. No stale-truth problem.

## 3. Capture flow (cheap, or it won't happen)

Capture is a **byproduct of doing the work**, prompted when the agent already has the
context in head — the human writes nothing. Three lifecycle commands:

- **`/start-story`** — creates the story dir, seeds `story.md` with the problem, opens
  `sessions/01.md`. Granularity: **roughly one story per PR/feature** — fine enough that
  decisions aren't buried, coarse enough that the index isn't noise.
- **`/end-session`** — at the end of each context window, writes the next
  `sessions/NN.md` handoff while fresh. Intra-story continuity. Shape:
  ```
  State: <where things stand>
  Done: <this session>
  Next: <immediate next steps>
  Watch out: <blockers / open questions>
  ```
- **`/finish-story`** — the *one* distillation moment. Reads session logs + the diff,
  writes durable `story.md`, appends the `INDEX.md` line.

**`story.md` is tight by design** (kills "too verbose"):

```
## Problem        (1–3 lines)
## Decisions      - <decision> — because <why> — rejected <alternative>
## Outcome        gotchas, what to watch
## Links          PRs, key files
```

The **decision → because → rejected-alternative** triplet is the payload — the thing a
future agent cannot recover from reading code. Sessions are raw; `story.md` is the
edited summary. Distillation happens once, at finish. Session logs are disposable after
a story closes (archive/prune) — `story.md` is the durable truth.

## 4. Learning protocol (rebuilt for trust)

Candidates accrue **evidence**, not just hits. A learning starts in a `LEARNINGS.md`
candidate ledger with provenance:

```
- [hits: 3] Pin the auth client version — floating versions broke 3 repos.
  stories: webapp/auth-token-refresh, api/login-retry, foo/sso  status: candidate
```

**Key insight: cross-repo hit count *is* the generalization signal — and picks the
destination:**

- Hit repeatedly in **one repo** → graduates to that **repo's own `AGENTS.md`**
  (local rule, scoped to that project).
- Hit across **multiple of your repos** → graduates to your **global `AGENTS.md`** in the
  knowledge repo (a personal rule, *proven* general by evidence — it kept recurring no
  matter which project you were in).

**Graduation is a proposal, not an automatic write — your personal curation gate.**
Hitting the threshold (default 3, tunable) surfaces: *"Hit 3× across 3 repos — promote
to global AGENTS.md? [y/n]."* Yes → moves up **with provenance attached**. No → marked
`won't-graduate` so it stops nagging. The gate exists so your global rules don't bloat;
trust comes from traceability — every rule shows which stories earned it.

**Anti-bloat:** rules carry a last-reinforced date; `/prune-learnings` flags entries not
hit in ages or contradicted by a newer decision, for demotion. `AGENTS.md` stays small
and current.

**Two-tier information architecture (the payoff):**

- **`AGENTS.md`** = *always-on* context. Small, high-confidence, auto-loaded by every
  agent (the standard file agents already read). Graduated learnings become rules
  everywhere, for free.
- **`story.md` via `INDEX.md`** = *on-demand* recall. Larger, specific, pulled only when
  relevant (Section 2).

Individual learnings → evidence → personal global rules → automatic context. Your own
mistakes stop repeating across projects.

## 5. Decoupling — a tiny portable kernel, a swappable toolkit

v1's coupling: knowledge capture entangled inside swarm-planning logic. v2 splits into
two layers with a strict dependency direction.

**The Knowledge Contract (kernel — tiny, tool-agnostic, mandatory):**
- `recall` — read the relevant past (Section 2)
- `start-story` / `end-session` / `finish-story` — capture (Section 3)
- `graduate` / `prune-learnings` — the learning loop (Section 4)

That is the whole contract. It does not know *how* you plan or write code. To contribute
to the KB, a workflow only **bookends itself**: `recall` before work, `finish-story`
after. Two touchpoints — the swap seam.

**The Toolkit (optional, swappable, layered on top):**
- **Swarm planning** — the *default* planner, shipped as the reference implementation of
  "plan a story." A dev with their own planning/impl tool wraps it with the two bookend
  calls and is a full citizen — no rewrite.
- **Workflow automations** — PR creation, PR review, addressing feedback, daily status.
  Independent bottleneck-killers that *also* feed the KB (a review writes a session log;
  addressing feedback updates the story), but none required.

**Dependency rule: Toolkit → depends on → Kernel. Kernel never depends on Toolkit.**
That keeps it portable: rip out swarm planning, swap the PR tooling, run it under
different conventions — the knowledge base behaves identically.

Maps onto install modes:
- **Minimal** = kernel only (contribute with any workflow) — the portable core.
- **Custom** = kernel + chosen workflow groups.
- **All** = kernel + swarm + all workflows + skills.

## 6. Adoption / install

**Two repos, clean roles** (v1 blurs them):
- **Toolkit repo** = the *code* (commands, skills, scripts), installed into `~/.claude/`.
- **Personal knowledge repo** = the *data* (`stories/`, `AGENTS.md`, `INDEX.md`); the
  `knowledge_base_path`. Git-backed so it syncs across your machines and keeps history.

Install = clone the toolkit, run `/setup`, point at your personal knowledge repo, pick a
mode. One config file (`~/.claude/akt-config.md`) holds paths + mode (as in v1).

**Distribute as one installable unit** — a Claude Code plugin (or one-command installer
that clones + links). "Photograph the repo screen-by-screen" must never be the install
path; `add plugin` is. Mechanical fix for heaviness.

**Adoption gradient:** start in Minimal (kernel only), get value day one — `recall` +
capture work immediately with any existing workflow — opt into more toolkit later. Low
activation energy because the **zero-infra default is real**: day-1 recall is just
markdown + the model, nothing to provision.

## Build order (decomposition for implementation)

v2 is large (kernel + recall/index + capture + learning + swarm + workflows + install).
The whole design is captured here as one coherent architecture, but **implementation
decomposes into sequenced plans**:

1. **Kernel first — the MVP.** `recall` + `INDEX.md`, the capture lifecycle
   (`start/end-session/finish`), the model, layout, config, and `/setup` Minimal mode.
   This alone delivers discovery + capture + continuity — the core value.
2. **Learning protocol** — `LEARNINGS.md`, `graduate`, `prune-learnings`, `AGENTS.md`
   tiers.
3. **Toolkit layers** — swarm planning (reference planner), then PR/daily workflow
   automations, each as its own plan.
4. **Distribution** — plugin packaging / one-command install.

Each layer is independently shippable on top of the kernel.

## Open questions / deferred

- **Embeddings upgrade trigger** — at what story count / recall-quality threshold do we
  flip the recall interface from index-read to vector search? Deferred until the kernel
  is in use and we can measure.
- **Session log retention policy** — archive vs prune after story close; exact policy TBD
  during kernel implementation.
- **`reindex` / migration from v1** — how to bulk-generate `INDEX.md` and migrate v1
  artifacts (tags/stories) into the v2 layout. Belongs to the kernel plan.
