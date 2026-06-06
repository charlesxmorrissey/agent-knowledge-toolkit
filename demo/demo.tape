# AKT demo — renders a GIF of the capture → recall loop.
#
# Render with (from the repo root):
#   brew install vhs        # https://github.com/charmbracelet/vhs
#   vhs demo/demo.tape      # writes demo/akt-demo.gif
#
# Safe to run: it sets a throwaway $HOME, so it never touches your real
# ~/knowledge base or ~/.claude config. Requires `akt` to be on your PATH.

Output demo/akt-demo.gif

Require akt

Set Shell "zsh"
Set FontSize 18
Set Width 1200
Set Height 760
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 35ms

# --- sandbox setup (hidden): fresh HOME + pre-staged story body ---
Hide
Type "export HOME=$(mktemp -d) && cd $HOME" Enter
Type "cat > body.md <<'EOF'" Enter
Type "---" Enter
Type "repo: myapp" Enter
Type "slug: add-auth-retry" Enter
Type "date: 2026-06-10" Enter
Type "summary: Retry auth on 401 with one token refresh before giving up" Enter
Type "keys: auth, retry, token, 401, backoff" Enter
Type "---" Enter
Type "## Problem" Enter
Type "Transient 401s were dropping user sessions." Enter
Type "## Decisions" Enter
Type "- Retry once after a token refresh on 401 — because most 401s were just expired tokens — rejected blanket retry-all" Enter
Type "## Outcome" Enter
Type "Session drops down ~90%." Enter
Type "## Links" Enter
Type "EOF" Enter
Type "clear" Enter
Show

Type "# 1. one-time: point AKT at a knowledge base" Enter
Sleep 600ms
Type "akt init ~/knowledge" Enter
Sleep 1500ms

Type "# 2. start a story in whatever repo you're working in" Enter
Sleep 600ms
Type 'STORY=$(akt start-story myapp "Add auth retry" --date 2026-06-10) && echo "$STORY"' Enter
Sleep 1500ms

Type "# 3. when the work wraps, capture the *why* (auto-commits + pushes)" Enter
Sleep 600ms
Type 'akt finish-story "$STORY" --stdin < body.md' Enter
Sleep 1800ms

Type "# 4. later — even from a DIFFERENT repo — recall it" Enter
Sleep 600ms
Type 'akt recall "how do we retry auth on a 401?"' Enter
Sleep 2000ms

Type "# the captured decision is right there:" Enter
Sleep 600ms
Type 'cat ~/knowledge/$(akt recall "retry auth 401" | head -1)' Enter
Sleep 3500ms
