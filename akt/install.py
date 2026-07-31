"""One-command setup: symlink the launcher, slash commands, and rule file into
place so `git pull` on this repo updates the global install with no sync step.

Safety rules (see docs/superpowers/specs/2026-07-30-akt-install-command-design.md):
correct symlink → skip silently; stale symlink → replace; real file → warn and
leave untouched. Always exits 0 — warnings on stderr carry the signal.
"""
import os
import sys
from pathlib import Path

from akt import config

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


def _ensure_import(claude_md, line):
    text = claude_md.read_text() if claude_md.exists() else ""
    if line in [ln.strip() for ln in text.splitlines()]:
        return
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    prefix = text.rstrip("\n") + "\n" if text.strip() else ""
    claude_md.write_text(prefix + line + "\n")
    print("added {} import to {}".format(line, claude_md))


def install(home=None):
    home = Path(home) if home else Path.home()
    bin_dir = home / ".local" / "bin"
    _link(REPO_ROOT / "bin" / "akt", bin_dir / "akt")
    for cmd in sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")):
        _link(cmd, home / ".claude" / "commands" / cmd.name)
    _link(REPO_ROOT / "claude" / "akt-rule.md", home / ".claude" / "AKT.md")
    claude_md = home / ".claude" / "CLAUDE.md"
    _ensure_import(claude_md, IMPORT_LINE)
    kb = config.get("knowledge_base_path")
    if kb:
        # Graduated global rules auto-load in every session via this import.
        _ensure_import(claude_md, "@{}/AGENTS.md".format(kb))
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        sys.stderr.write("⚠ {} is not on PATH — add it so `akt` works everywhere\n".format(bin_dir))
    return 0
