"""LEARNINGS.md — the evidence ledger for the learning protocol.

Source of truth (NOT derived): hits and statuses can't be rebuilt from
stories. One parseable line per candidate, in the index.py idiom.
"""
import re
from pathlib import Path

LEARNINGS_FILE = "LEARNINGS.md"
_HEADER = "# Learnings\n\nOne entry per candidate. Managed by `akt learn` — do not hand-edit.\n"
_LINE = re.compile(
    r"^- \[([a-z0-9-]+)\] (.*) \| hits: (\d+) \| status: ([a-z-]+)"
    r" \| last: (\d{4}-\d{2}-\d{2}) \| stories: (.*)$"
)

STATUSES = ("candidate", "graduated-global", "graduated-repo", "wont-graduate")


def build_learning_line(entry):
    return "- [{}] {} | hits: {} | status: {} | last: {} | stories: {}".format(
        entry["id"], entry["rule"], entry["hits"], entry["status"],
        entry["last"], ", ".join(entry["stories"]),
    )


def parse_learning_line(line):
    m = _LINE.match(line.strip())
    if not m:
        return None
    return {
        "id": m.group(1),
        "rule": m.group(2),
        "hits": int(m.group(3)),
        "status": m.group(4),
        "last": m.group(5),
        "stories": [s.strip() for s in m.group(6).split(",") if s.strip()],
    }


def _ledger_file(kb_path):
    return Path(kb_path) / LEARNINGS_FILE


def read_learnings(kb_path):
    f = _ledger_file(kb_path)
    if not f.exists():
        return []
    entries = []
    for line in f.read_text().splitlines():
        parsed = parse_learning_line(line)
        if parsed:
            entries.append(parsed)
    return entries


def write_learnings(kb_path, entries):
    body = "\n".join(build_learning_line(e) for e in entries)
    _ledger_file(kb_path).write_text(_HEADER + "\n" + body + ("\n" if body else ""))


def scope(entry):
    """Derived, never stored: 1 distinct repo -> repo-local, >=2 -> global."""
    repos = {s.split("/", 1)[0] for s in entry["stories"]}
    return "global" if len(repos) >= 2 else "repo"
