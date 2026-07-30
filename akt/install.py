"""One-command setup: symlink the launcher, slash commands, and rule file into
place so `git pull` on this repo updates the global install with no sync step.

Safety rules (see docs/superpowers/specs/2026-07-30-akt-install-command-design.md):
correct symlink → skip silently; stale symlink → replace; real file → warn and
leave untouched. Always exits 0 — warnings on stderr carry the signal.
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMPORT_LINE = "@AKT.md"


def _link(source, dest):
    if dest.is_symlink():
        if dest.resolve() == source.resolve():
            return
        dest.unlink()
        dest.symlink_to(source)
        print("relinked {} -> {}".format(dest, source))
        return
    if dest.exists():
        sys.stderr.write(
            "⚠ {} exists and is not a symlink — left untouched "
            "(remove it and re-run to link)\n".format(dest)
        )
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(source)
    print("linked {} -> {}".format(dest, source))


def _ensure_import(claude_md):
    text = claude_md.read_text() if claude_md.exists() else ""
    if IMPORT_LINE in [line.strip() for line in text.splitlines()]:
        return
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    prefix = text.rstrip("\n") + "\n" if text.strip() else ""
    claude_md.write_text(prefix + IMPORT_LINE + "\n")
    print("added {} import to {}".format(IMPORT_LINE, claude_md))


def install(home=None):
    home = Path(home) if home else Path.home()
    bin_dir = home / ".local" / "bin"
    _link(REPO_ROOT / "bin" / "akt", bin_dir / "akt")
    for cmd in sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")):
        _link(cmd, home / ".claude" / "commands" / cmd.name)
    _link(REPO_ROOT / "claude" / "akt-rule.md", home / ".claude" / "AKT.md")
    _ensure_import(home / ".claude" / "CLAUDE.md")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        sys.stderr.write("⚠ {} is not on PATH — add it so `akt` works everywhere\n".format(bin_dir))
    return 0
