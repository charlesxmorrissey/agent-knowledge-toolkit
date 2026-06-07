# AKT demo — the practical payoff: recall surfaces past decisions across repos.
#
# Render (from the repo root):
#   brew install vhs        # https://github.com/charmbracelet/vhs
#   vhs demo/demo.tape      # writes demo/akt-demo.gif
#
# Safe to run: it uses a throwaway $HOME, so it never touches your real
# ~/knowledge base or ~/.claude config. Requires `akt` on your PATH.

Output demo/akt-demo.gif

Require akt

Set Shell "zsh"
Set FontSize 18
Set Width 1200
Set Height 820
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 35ms

# --- hidden: sandbox + two stories you "captured weeks ago, in other repos" ---
Hide
Type "setopt interactive_comments" Enter
Type "export HOME=$(mktemp -d) && cd $HOME && akt init ~/knowledge >/dev/null" Enter
Type 'S=$(akt start-story api "Retry upstream calls" --date 2026-05-12)' Enter
Type "akt finish-story $S --stdin >/dev/null <<'EOF'" Enter
Type "---" Enter
Type "repo: api" Enter
Type "slug: retry-upstream-calls" Enter
Type "date: 2026-05-12" Enter
Type "summary: Retry upstream calls with exponential backoff + jitter, cap 3 tries" Enter
Type "keys: retry, backoff, jitter, upstream, api, timeout" Enter
Type "---" Enter
Type "## Problem" Enter
Type "Transient upstream failures cascaded; immediate retries made incidents worse." Enter
Type "## Decisions" Enter
Type "- Exponential backoff + jitter, max 3 attempts — because synchronized immediate retries hammered the upstream during outages — rejected fixed-interval retry" Enter
Type "## Outcome" Enter
Type "Retry storms gone; incident blast radius shrank." Enter
Type "## Links" Enter
Type "EOF" Enter
Type 'S=$(akt start-story payments "Make charge retries safe" --date 2026-05-20)' Enter
Type "akt finish-story $S --stdin >/dev/null <<'EOF'" Enter
Type "---" Enter
Type "repo: payments" Enter
Type "slug: make-charge-retries-safe" Enter
Type "date: 2026-05-20" Enter
Type "summary: Require an Idempotency-Key on writes so retried requests never double-charge" Enter
Type "keys: idempotency, retry, payments, writes, safety" Enter
Type "---" Enter
Type "## Problem" Enter
Type "Network retries could submit the same charge twice." Enter
Type "## Decisions" Enter
Type "- Require Idempotency-Key on POSTs — because retries are unavoidable and must be safe — rejected dedupe-by-amount" Enter
Type "## Outcome" Enter
Type "Zero duplicate charges since rollout." Enter
Type "## Links" Enter
Type "EOF" Enter
Type "clear" Enter
Show

Sleep 600ms
Type "# New day, working in the 'web' repo. Task: add retry logic to the API client." Enter
Sleep 1400ms
Type "# First — what have I already figured out about this, anywhere?" Enter
Sleep 1400ms
Type 'akt recall "retry api calls with backoff"' Enter
Sleep 2600ms
Type "# Two past decisions — from OTHER repos. Open the most relevant:" Enter
Sleep 1400ms
Type 'cat ~/knowledge/$(akt recall "retry api calls with backoff" | head -1)' Enter
Sleep 4500ms
Type "# the decision AND the why — so you build on it instead of relearning it." Enter
Sleep 3000ms
