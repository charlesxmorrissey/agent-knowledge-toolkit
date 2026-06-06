---
description: Install or update the Agent Knowledge Toolkit
allowed-tools: Bash, Write, Read, AskUserQuestion
---

# Agent Knowledge Toolkit Setup

Install or update the Agent Knowledge Toolkit from this repository to `~/.claude/`.

## Steps

| Step | What | Detail |
|------|------|--------|
| 1 | Verify repo structure | inline |
| 2 | Detect install state | `@setup/scripts/detect-mode.sh` |
| 3 | Choose install mode | inline (interactive) |
| 3.5 | Select optional skills | `@setup/discovery.md` |
| 4 | Compare versions | `@setup/scripts/compare-versions.sh` |
| 5 | Get paths | `@setup/get-paths.md` |
| 6 | Clone team repo | inline |
| 7 | Create directories | inline |
| 8 | Copy files | `@setup/scripts/copy-files.sh` |
| 9 | Write config | `@setup/write-config.md` |
| 10 | Initialize tag registry | inline |
| 11 | CLAUDE.md guidance | `@setup/claude-md-guidance.md` |
| 12 | Verify installation | `@setup/scripts/verify-installation.sh` |
| 12.5 | Discover skill setups | `@setup/discovery.md` |
| 13 | Report results | `@setup/report.md` |

Managed file definitions: `@setup/constants.md`

---

## Step 1: Verify Repository Structure

```bash
ls -1 commands/ agents/ README.md 2>/dev/null | wc -l
```

Expected: At least 3 items. If not, stop: "Please run /setup from the agent-knowledge-toolkit repository root."

## Step 2: Detect Installation State

Migrate config filename if needed, then check:

```bash
# TODO: Remove these migrations once all users have re-installed
if [ -f ~/.claude/commands/.meta/session-config.md ] && [ ! -f ~/.claude/akt-config.md ]; then
  mv ~/.claude/commands/.meta/session-config.md ~/.claude/akt-config.md
  echo "Migrated: commands/.meta/session-config.md → ~/.claude/akt-config.md"
elif [ -f ~/.claude/commands/.meta/akt-config.md ] && [ ! -f ~/.claude/akt-config.md ]; then
  mv ~/.claude/commands/.meta/akt-config.md ~/.claude/akt-config.md
  echo "Migrated: commands/.meta/akt-config.md → ~/.claude/akt-config.md"
fi

ls ~/.claude/akt-config.md 2>/dev/null && echo "INSTALLED" || echo "FRESH"
```

- **FRESH**: New installation — will ask for paths and install mode
- **INSTALLED**: Update existing — preserve config and data

## Step 3: Choose Install Mode

Use AskUserQuestion:

**Question:** "Which installation mode?"

- `All` (Full framework with swarm planning, all commands, all agents) (Recommended)
- `Custom` (Core session management + pick which workflow tools you want)
- `Minimal` (Just /end-session + discovery — for teammates whose tools already create session folders)

Store as `{{install_mode}}`. For updates, mention the current detected mode.

### Custom Mode: Select Workflow Groups

**Only if `{{install_mode}}` is `Custom`.** Use AskUserQuestion with `multiSelect: true`:

**Question:** "Which workflow tools do you want? (Core session commands are always included)"

- `pr-workflow` — `/pr-create`, `/address-pr-comments`, `/pr-review`, `/pr-review-end` + `gh-cli`, `pr-demo` skills
- `daily-workflow` — `/daily-status`, `/eod` + `daily-note-sync` skill
- `ci-workflow` — `fix-pr-ci` skill for batch CI fixing
- `dev-toolkit` — `/audit-repos` + `audit-repos` skill for repository inventory auditing

Store as `{{selected_groups}}` (comma-separated kebab-case values, e.g., `pr-workflow,daily-workflow`).

**For updates:** Detect from existing config — see `@setup/detect-mode.md`.

## Step 3.5: Select Optional Skills

**For All or Custom mode (skip for Minimal).**

Follow `@setup/discovery.md` (Step 3.5: Optional Skill Menu) — discovers optional skills from SETUP.md metadata, presents multiSelect menu. Store as `{{selected_skills}}`.

**For updates:** Pre-select currently installed optional skills.

## Step 4: Compare Versions

**For updates only.** Run `@setup/scripts/compare-versions.sh` to show what will change. Tell the user what will be updated and what will be preserved.

## Step 5: Get Paths

Follow `@setup/get-paths.md` — asks up to 8 questions based on install mode. Skips questions for values already in config.

## Step 6: Clone Team Repo

```bash
if [ -n "{{team_repo_url}}" ] && [ ! -d "{{team_base_path}}/.git" ]; then
  git clone {{team_repo_url}} {{team_base_path}}
fi
```

If clone fails, warn but continue.

## Step 7: Create Directories

```bash
mkdir -p ~/.claude/commands ~/.claude/agents ~/.claude/skills
mkdir -p "{{team_base_path}}/stories"

if [ "{{install_mode}}" = "all" ] || [ "{{install_mode}}" = "custom" ]; then
  mkdir -p "{{personal_base_path}}" "{{learnings_path}}"
fi
```

## Step 8: Copy Files

Run `@setup/scripts/copy-files.sh` with the install mode, paths, and selected options. See `@setup/constants.md` for managed file definitions.

## Step 9: Write Config

Follow `@setup/write-config.md` — creates or updates `~/.claude/akt-config.md` based on install mode.

## Step 10: Initialize Tag Registry

Create `{{team_base_path}}/_tags.md` if it doesn't exist:

```markdown
# Session Tags

Tags enable cross-session discovery across all stories.

## Guidelines

- Reuse existing tags whenever possible
- Keep tags broad (e.g., `authentication` not `auth-cookie-handling`)
- Repo names are auto-tags
- Namespace generic terms under repo (e.g., `webapp.documentation`)

## Tags

(Added automatically as sessions complete)
```

## Step 11: CLAUDE.md Guidance

Follow `@setup/claude-md-guidance.md` — offers optional guidance sections for `~/.claude/CLAUDE.md`.

## Step 12: Verify Installation

Run `@setup/scripts/verify-installation.sh` to confirm what was installed and identify user files.

## Step 12.5: Discover Skill Setup Guides

Follow `@setup/discovery.md` (Step 12.5: Skill Setup Guides) — reads installed skills' SETUP.md files, extracts SETUP_COMMAND_OUTPUT content, evaluates template variables for inclusion in Step 13.

## Step 13: Report Results

Follow `@setup/report.md` — presents configuration summary, available commands, and any skill setup guides.

---

## Important Notes

- **Safe to run multiple times** — idempotent
- **Always updated**: Commands, agents, skills (get latest versions)
- **Never overwritten**: Config (`~/.claude/akt-config.md`) and learnings files
- **Must run from repo root**: Run `/setup` from wherever you cloned agent-knowledge-toolkit

## Scope

This framework only manages its own files. Users may have other commands, agents, and skills in `~/.claude/` — that's expected and fine.

**Framework-managed files:** Defined in `@setup/constants.md` (single source of truth). The Step 12 verification explicitly lists what's managed vs user-owned.

**Not managed:** Other user-installed commands/agents/skills, project-level `.claude/` folders, user's global `CLAUDE.md`.
