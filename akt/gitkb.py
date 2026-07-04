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
        return r.returncode == 0, r.stdout.strip()
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
