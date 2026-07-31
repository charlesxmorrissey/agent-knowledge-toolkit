"""LEARNINGS.md — the evidence ledger for the learning protocol.

Source of truth (NOT derived): hits and statuses can't be rebuilt from
stories. One parseable line per candidate, in the index.py idiom.
"""
import re
from datetime import date as _date, timedelta
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
        elif line.strip().startswith("- ["):
            # LEARNINGS.md is source of truth, not derived — a silently
            # skipped line here gets permanently deleted on the next write.
            raise ValueError("malformed ledger line: {}".format(line))
    return entries


def write_learnings(kb_path, entries):
    body = "\n".join(build_learning_line(e) for e in entries)
    _ledger_file(kb_path).write_text(_HEADER + "\n" + body + ("\n" if body else ""))


def scope(entry):
    """Derived, never stored: 1 distinct repo -> repo-local, >=2 -> global."""
    repos = {s.split("/", 1)[0] for s in entry["stories"]}
    return "global" if len(repos) >= 2 else "repo"


AGENTS_FILE = "AGENTS.md"


def rule_block(entry):
    """The graduated-rule format: rule text agents read, provenance in a comment."""
    return "- {}\n  <!-- akt: {} | {} hits | {} -->".format(
        entry["rule"], entry["id"], entry["hits"], ", ".join(entry["stories"])
    )


def _find(entries, learn_id):
    for e in entries:
        if e["id"] == learn_id:
            return e
    raise ValueError("no learning with id '{}'".format(learn_id))


def add(kb_path, learn_id, rule, story, today):
    if "|" in rule:
        raise ValueError("rule text must not contain '|'")
    if not re.fullmatch(r"[a-z0-9-]+", learn_id):
        raise ValueError("id must be kebab-case: '{}'".format(learn_id))
    entries = read_learnings(kb_path)
    if any(e["id"] == learn_id for e in entries):
        raise ValueError("duplicate learning id '{}'".format(learn_id))
    entry = {"id": learn_id, "rule": rule, "hits": 1, "status": "candidate",
             "last": today, "stories": [story]}
    entries.append(entry)
    write_learnings(kb_path, entries)
    return entry


def _proposal(entry):
    sc = scope(entry)
    repos = {s.split("/", 1)[0] for s in entry["stories"]}
    where = "GLOBAL ({} hits across {} repos)".format(entry["hits"], len(repos)) \
        if sc == "global" else \
        "REPO-LOCAL to '{}' ({} hits in one repo)".format(next(iter(repos)), entry["hits"])
    return "PROPOSE: graduate '{}' as {} — run: akt learn graduate {}".format(
        entry["id"], where, entry["id"])


def reinforce(kb_path, learn_id, story, today, threshold):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    entry["hits"] += 1
    entry["last"] = today
    if story not in entry["stories"]:
        entry["stories"].append(story)
    write_learnings(kb_path, entries)
    proposal = _proposal(entry) \
        if entry["status"] == "candidate" and entry["hits"] >= threshold else None
    return entry, proposal


def graduate(kb_path, learn_id):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    if entry["status"] != "candidate":
        raise ValueError("'{}' is already {}".format(learn_id, entry["status"]))
    sc = scope(entry)
    entry["status"] = "graduated-global" if sc == "global" else "graduated-repo"
    block = rule_block(entry)
    write_learnings(kb_path, entries)
    if sc == "global":
        agents = Path(kb_path) / AGENTS_FILE
        existing = agents.read_text() if agents.exists() else ""
        prefix = existing.rstrip("\n") + "\n\n" if existing.strip() else ""
        agents.write_text(prefix + block + "\n")
    return entry, block


def wont(kb_path, learn_id):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    entry["status"] = "wont-graduate"
    write_learnings(kb_path, entries)
    return entry


def prune_report(kb_path, today, cutoff_days):
    """Print-only staleness report; never writes. Returns (candidates, graduated)."""
    cutoff = _date.fromisoformat(today) - timedelta(days=cutoff_days)
    stale_candidates, stale_graduated = [], []
    for e in read_learnings(kb_path):
        if _date.fromisoformat(e["last"]) >= cutoff:
            continue
        if e["status"] == "candidate":
            stale_candidates.append(e)
        elif e["status"].startswith("graduated"):
            stale_graduated.append(e)
    return stale_candidates, stale_graduated
