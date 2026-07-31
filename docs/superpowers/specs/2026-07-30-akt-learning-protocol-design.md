# AKT Learning Protocol — design

Layer 2 of the build order in
[`2026-06-05-agent-knowledge-toolkit-design.md`](2026-06-05-agent-knowledge-toolkit-design.md)
(Section 4, "Learning protocol"). Recurring lessons accrue evidence in a
`LEARNINGS.md` ledger and graduate — through a human gate — into always-on
`AGENTS.md` rules, with provenance.

## Why now

The deferral condition ("until stories accumulate and patterns repeat") is met:
the KB holds ~30 stories across 8 repos, with visibly recurring lessons —
CodeMirror-6 paste gotchas across 3+ stories, Formcrafts `values()` prefill
across 3 repos, HeyFlow shadow-root blindness across 4+ stories in one repo.

## Decisions (settled during brainstorm)

- **Detection is capture-time + one bootstrap mine** — the `finish-story` /
  `update-story` flows check each new story's lessons against the ledger;
  a one-time `/mine-learnings` sweep seeds it from the existing corpus.
  Rejected: periodic mining as the primary mechanism (a new habit to forget).
- **Global rules reach agents via an `@import`** wired by `akt install` into
  `~/.claude/CLAUDE.md` — same mechanism as `@AKT.md`. Rejected: manual
  copying (rules rot unread — the design's "existential failure").
- **Repo-local rules are written by the agent, in-repo, at capture time** —
  graduation proposals surface during `finish-story`, which runs while working
  in that repo. The CLI never writes outside the KB. Rejected: a `--repo-path`
  CLI write (surprising cross-repo mutation).
- **Entry bar is `hits: 1` for any transferable lesson** — the ledger is cheap
  and never auto-loaded; the hits threshold keeps `AGENTS.md` clean; the
  evidence decides, not upfront judgment. Rejected: enter-on-second-sighting
  (first sightings recorded nowhere → fragile).
- **CLI/LLM split follows the kernel pattern** — deterministic ledger ops in
  `akt learn` subcommands with atomic KB commits; fuzzy matching and rule
  wording in slash-command prose. The threshold-crossing nudge is printed by
  the CLI itself (mechanical, not agent-remembered — the PR #8 lesson).
  Rejected: free-form LLM-edited ledger (no dedupe/validation/atomicity);
  auto-graduation with similarity scoring (spec requires a human gate).

## 1. Data model — `LEARNINGS.md`

One file in the KB root, sibling to `INDEX.md`. Line-oriented and
machine-parseable like the index, but **source of truth, not derived** —
hits and statuses cannot be rebuilt from stories.

```
# Learnings

One entry per candidate. Managed by `akt learn` — do not hand-edit.

- [cm6-paste-appends] Verify live bundle bytes after CodeMirror-6 paste — paste can silently APPEND instead of replace | hits: 3 | status: candidate | last: 2026-07-30 | stories: heyflow/2026-07-29-loader-interstitials-button-system-and-pronoun-case-fix-overnight-figma-batch, heyflow/2026-07-29-dead-end-conf-homepage-link-styled-as-filled-button, heyflow/2026-07-27-capture-method-webform-constant-and-the-restricted-picklist-probe
```

Per entry:

- **id** — short kebab-case handle, supplied by the agent at `add` time; the
  key for all CLI operations. Unique.
- **rule text** — one sentence phrased as an instruction (it is destined for
  an `AGENTS.md`). Must not contain `|`.
- **hits** — integer, starts at 1.
- **status** — `candidate` | `graduated-global` | `graduated-repo` |
  `wont-graduate`. Graduated / wont entries stay in the ledger (provenance and
  stop-nagging marker); nothing is deleted.
- **last** — ISO date of the last reinforcement; feeds pruning.
- **stories** — comma-separated story dir names (`<repo>/<date>-<slug>`), the
  provenance trail. Deduplicated.

**Scope is derived, never stored:** count distinct repos across `stories` —
1 repo → repo-local proposal, ≥2 repos → global proposal.

Parser/serializer follows the `index.py` idiom (one regex; build / parse /
read / write functions). Every mutating command commits (and pushes, if a
remote is set) the KB via the existing `gitkb` module — the same atomicity
guarantee `finish-story` has.

## 2. CLI — the `akt learn` family

New module `akt/learn.py` plus dispatch in `cli.py`, mirroring `story.py`
wiring. All subcommands are deterministic file/text work.

- `akt learn add "<id>" "<rule text>" --story <repo/date-slug>` — create an
  entry at `hits: 1`, `status: candidate`, `last:` today. Fails on duplicate id.
- `akt learn reinforce <id> --story <repo/date-slug>` — bump hits, set `last`,
  append the story (deduped). **When hits reaches the threshold (default 3,
  config key `learn_threshold`) and status is `candidate`, the command prints
  the graduation proposal itself**, e.g.
  `PROPOSE: graduate 'cm6-paste-appends' as GLOBAL (3 hits across 2 repos) — run: akt learn graduate cm6-paste-appends`.
  It keeps printing on every subsequent reinforce until the entry is graduated
  or marked `wont-graduate`.
- `akt learn graduate <id>` — derive scope; set status to `graduated-global`
  or `graduated-repo`. For **global**: append the rule block (see Section 4)
  to the KB's `AGENTS.md` in the same atomic commit. For **repo-local**: flip
  status only and print the rule block to stdout for the agent to paste into
  the repo's own rules file — the CLI never writes outside the KB.
- `akt learn wont <id>` — set `wont-graduate`; suppresses future proposals.
- `akt learn list [--status <status>]` — print the ledger (optionally
  filtered). The agent's view for capture-time matching.
- `akt learn prune` — print-only report: candidates whose `last` is older than
  the cutoff (default 90 days, config key `prune_days`), and graduated entries
  ripe for demotion review. The human decides; no automatic writes.

No `remove` subcommand — `wont` covers retirement; git history covers true
mistakes.

## 3. Judgment layer — capture-flow integration

Prompt-only changes to existing commands (repo `.claude/commands/`, already
symlinked globally by `akt install`) and `AKT.md`.

**`finish-story` and `update-story` gain a learnings pass** (after the story
commit):

1. Run `akt learn list --status candidate`.
2. For each transferable lesson in the story just captured: if it matches an
   existing candidate → `akt learn reinforce <id> --story <this-story>`; if
   new → `akt learn add`. Matching is deliberately the model's job — "is
   'CM6 paste appends' the same lesson as 'verify bundle bytes after paste'?"
   is fuzzy-language work, which the kernel's split reserves for prompts.
3. If any command printed a `PROPOSE:` line, relay it to the user verbatim and
   act on their answer: `graduate` (for repo-local, also append the printed
   rule block to *this* repo's `AGENTS.md` / `CLAUDE.md` and commit it with
   the work) or `wont`.

**New slash command `/mine-learnings`** — the bootstrap and re-sweep tool.
Walks every `story.md` in the KB oldest-first, extracts transferable lessons,
and performs the same add/reinforce dance. Graduation proposals are batched
and presented at the end of the sweep, not mid-walk. Run once to seed the
ledger from the existing ~30 stories; keep for occasional manual re-sweeps
(e.g., after threshold tuning).

**`AKT.md`** gains two lines in the capture section describing the learnings
pass, keeping the ambient rule and the commands in sync.

**Non-goal:** no learnings check at `recall` time. Graduated rules are already
auto-loaded via the import; candidates are unproven and would be noise.

## 4. Rule delivery

**Global:** `akt install` gains one idempotent step — ensure
`~/.claude/CLAUDE.md` contains an import line for the KB's `AGENTS.md`
(path resolved from `knowledge_base_path`), exactly as it already ensures
`@AKT.md`. Existing installs pick it up by re-running `akt install`.

**Graduated rule block format** (written by `graduate` for global; printed for
repo-local):

```
- Verify live bundle bytes after CodeMirror-6 paste — paste can silently APPEND instead of replace.
  <!-- akt: cm6-paste-appends | 3 hits | heyflow/2026-07-29-loader-interstitials-button-system-and-pronoun-case-fix-overnight-figma-batch, heyflow/2026-07-27-capture-method-webform-constant-and-the-restricted-picklist-probe -->
```

Rule text is what agents read; provenance rides in an HTML comment —
greppable by id, so `prune` and humans can trace any rule back to its ledger
entry. The `AGENTS.md` header seeded by `init.py` is unchanged.

**Repo-local:** same block format, appended by the *agent* to the repo's own
rules file at graduation time and committed with the work (Section 3).

## 5. Precursor fix — INDEX.md hygiene (separate PR, ships first)

The current index is degraded: ~12 entries render as `- [/] ...` with empty
`repo`/`slug`/`keys` (stories captured without full frontmatter), and three
are exact duplicates — the malformed lines fail the index-line regex, so
path-dedupe in `append_index_line` never matches them and they accumulate.

Three fixes, in one small PR before the learning layer (which mines this
corpus and should mine clean data):

1. `finish-story` / `update-story` validate non-empty `repo`, `slug`, and
   `keys` frontmatter (today only `summary` is validated).
2. Dedupe in `append_index_line` tolerates malformed lines (falls back to
   raw-path substring match) so they cannot duplicate.
3. Repair the broken stories' frontmatter in the KB, then `reindex` once.

## Error handling

- `learn` commands fail loudly: unknown id, duplicate id, or a malformed
  ledger line → print the offending detail to stderr, exit 2.
- Dirty-KB warning on stderr, same as `recall` / `start-story`.
- `graduate` on an already-graduated or `wont-graduate` entry is an error
  (state is explicit, never silently re-applied).

## Testing

`tests/test_learn.py` in the house style (stdlib `unittest`, temp dirs):

- Ledger entry round-trip (build → parse).
- `add` starts at hits 1; duplicate id rejected.
- `reinforce` bumps hits, updates `last`, dedupes stories; proposal printed at
  exactly the threshold and again until resolved.
- Scope derivation: 1 repo → repo-local, 2 repos → global.
- `graduate` global appends the rule block with provenance comment to
  `AGENTS.md`; repo-local flips status and writes nothing outside the ledger.
- `wont` suppresses proposals.
- `prune` date cutoff math.
- One `cli.py` dispatch test per subcommand family.

Install change covered in `tests/test_install.py` (import line added,
idempotent). Slash-command prose is verified by an end-to-end manual task in
the implementation plan, like kernel plan Task 11.

## Out of scope (unchanged from the master design)

- Swarm planning / workflow toolkit (Layer 3) and plugin distribution
  (Layer 4).
- Embeddings recall upgrade.
- Automatic demotion — `prune` only reports.
