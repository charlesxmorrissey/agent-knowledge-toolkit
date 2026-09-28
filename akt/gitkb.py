"""Graceful git helpers for the knowledge base.

Every function is a no-op when git is unavailable, the KB isn't a repo, or the
network is down — capture must never block or error on git trouble (see the AKT
graceful no-op rule).
"""
import subprocess
from pathlib import Path


def _git(kb, *args):
    """Run a git command scoped to `kb`; return (ok, stdout). Never raises."""
    try:
        r = subprocess.run(
            ["git", "-C", str(kb), *args],
            capture_output=True, text=True,
        )
        # rstrip only: porcelain status lines carry meaning in their leading
        # column (" M" = unstaged edit), so a full strip() would corrupt them.
        return r.returncode == 0, r.stdout.rstrip("\n")
    except (OSError, ValueError):
        return False, ""


def is_repo(kb):
    ok, out = _git(kb, "rev-parse", "--is-inside-work-tree")
    return ok and out == "true"


def is_dirty(kb):
    if not is_repo(kb):
        return False
    ok, out = _git(kb, "status", "--porcelain")
    return ok and bool(out)


def status_entries(kb):
    """(code, path) pairs from `git status --porcelain`, one per file.

    Untracked files are listed individually (not collapsed to their directory)
    so callers can tell an open story's skeleton from stray files. [] when
    `kb` isn't a repo.
    """
    if not is_repo(kb):
        return []
    ok, out = _git(kb, "status", "--porcelain", "--untracked-files=all")
    if not ok:
        return []
    entries = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]  # git quotes paths with spaces/special chars
        entries.append((code, path))
    return entries


def commit_kb(kb, message):
    """add -A, commit, and push (if an origin exists). Returns a status line."""
    kb = Path(kb)
    if not is_repo(kb):
        return "knowledge base is not a git repo (commit skipped)"
    if not is_dirty(kb):
        return "knowledge base already clean (nothing to commit)"
    _git(kb, "add", "-A")
    ok, _ = _git(kb, "commit", "-m", message)
    if not ok:
        return "knowledge base commit failed (left uncommitted)"
    has_remote, _ = _git(kb, "remote", "get-url", "origin")
    if not has_remote:
        return "knowledge base committed locally (no remote)"
    pushed, _ = _git(kb, "push")
    return "knowledge base committed and pushed" if pushed \
        else "knowledge base committed locally (push skipped: offline?)"
