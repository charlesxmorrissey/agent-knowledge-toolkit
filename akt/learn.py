"""LEARNINGS.md — the evidence ledger for the learning protocol.

Source of truth (NOT derived): hits and statuses can't be rebuilt from
stories. One parseable line per candidate, in the index.py idiom.
"""
import math
import re
from datetime import date as _date, timedelta
from pathlib import Path

from akt.rank import scores, tokenize

LEARNINGS_FILE = "LEARNINGS.md"
_HEADER = "# Learnings\n\nOne entry per candidate. Managed by `akt learn` — do not hand-edit.\n"
_LINE = re.compile(
    r"^- \[([a-z0-9-]+)\] (.*) \| hits: (\d+) \| status: ([a-z-]+)"
    r" \| last: (\d{4}-\d{2}-\d{2}) \| stories: (.*)$"
)

# Two global statuses (issue #77). `graduated-global` is a core rule: its block
# is in the KB AGENTS.md and loads in every session. `graduated-recall` is a
# rule that stays in this ledger and is printed by `akt recall` when a task
# matches it, so the always-loaded file does not grow with every narrow rule.
STATUSES = ("candidate", "graduated-global", "graduated-recall", "graduated-repo",
            "wont-graduate")

# A rule is printed by recall when its score is above this many times the
# weight of a word that only one entry holds. On a real ledger of 571 entries,
# 9 task lines with a known rule scored 1.7 to 3.4 times that weight and 8
# task lines with none scored 0.1 to 1.3.
RULE_CUTOFF = 1.5


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


def compact_line(entry):
    """Scan-pass format (issue #31): id + truncated rule, no stories."""
    rule = entry["rule"] if len(entry["rule"]) <= 80 else entry["rule"][:79] + "…"
    return "- [{}] {} | hits: {} | status: {}".format(
        entry["id"], rule, entry["hits"], entry["status"])


def match_line(entry, score=None):
    """Match-pass format: the whole rule, no stories. A handful of lines print,
    so the rule needs no truncation and no follow-up `show`.

    `score` is in the unit RULE_CUTOFF uses: 1.0 is one shared word that only
    one entry holds. Printed so real runs show what a true match scores
    against a loose one (issue #75).
    """
    line = "- [{}] {} | hits: {} | status: {}".format(
        entry["id"], entry["rule"], entry["hits"], entry["status"])
    return line if score is None else "{} | score: {:.1f}".format(line, score)


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
    line = "PROPOSE: graduate '{}' as {} — run: akt learn graduate {}".format(
        entry["id"], where, entry["id"])
    if sc == "global":
        line += " (add --core to load it in every session; without it, recall prints it when a task matches)"
    return line


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


def _append_rule(kb_path, block):
    agents = Path(kb_path) / AGENTS_FILE
    existing = agents.read_text() if agents.exists() else ""
    prefix = existing.rstrip("\n") + "\n\n" if existing.strip() else ""
    agents.write_text(prefix + block + "\n")


def _remove_rule(kb_path, learn_id):
    """Take a rule block out of AGENTS.md. True when a block was found.

    The block is found by its `<!-- akt: <id> ` comment, which survives a
    hand-trimmed provenance list. The rule line above it goes with it.
    """
    agents = Path(kb_path) / AGENTS_FILE
    if not agents.exists():
        return False
    lines = agents.read_text().split("\n")
    marker = re.compile(r"<!--\s*akt:\s*{}\s*(\||-->)".format(re.escape(learn_id)))
    for i, line in enumerate(lines):
        if marker.search(line):
            start = i - 1 if i > 0 and lines[i - 1].startswith("- ") else i
            end = i + 1
            # One blank line separates blocks; take the one after this block.
            if end < len(lines) and not lines[end].strip() and start > 0:
                end += 1
            del lines[start:end]
            agents.write_text("\n".join(lines).rstrip("\n") + "\n")
            return True
    return False


def graduate(kb_path, learn_id, core=False):
    """Promote a candidate. Global scope: `core` writes the rule block to the
    KB AGENTS.md (loads in every session); without it the rule stays in the
    ledger and `akt recall` prints it when a task matches. Repo scope ignores
    `core`: the caller appends the block to that repo's own rule file."""
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    if entry["status"] != "candidate":
        raise ValueError("'{}' is already {}".format(learn_id, entry["status"]))
    if scope(entry) == "repo":
        entry["status"] = "graduated-repo"
    else:
        entry["status"] = "graduated-global" if core else "graduated-recall"
    block = rule_block(entry)
    write_learnings(kb_path, entries)
    if entry["status"] == "graduated-global":
        _append_rule(kb_path, block)
    return entry, block


def set_load(kb_path, learn_id, where):
    """Move a graduated global rule between `core` (AGENTS.md, every session)
    and `recall` (ledger only, printed by recall on a match).

    Returns (entry, found): `found` is False when moving to `recall` and
    AGENTS.md held no block for the id. The status still changes then, so a
    block removed by hand can be brought in line with one command.
    """
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    want = {"core": "graduated-global", "recall": "graduated-recall"}[where]
    if entry["status"] not in ("graduated-global", "graduated-recall"):
        raise ValueError("'{}' is {}; only a graduated global rule can move".format(
            learn_id, entry["status"]))
    if entry["status"] == want:
        raise ValueError("'{}' is already {}".format(learn_id, want))
    entry["status"] = want
    found = True
    if where == "core":
        _remove_rule(kb_path, learn_id)  # never two blocks for one id
        _append_rule(kb_path, rule_block(entry))
    else:
        found = _remove_rule(kb_path, learn_id)
    write_learnings(kb_path, entries)
    return entry, found


def _set_rule_hits(kb_path, learn_id, hits):
    """Bring the hit count in a core rule's AGENTS.md comment in line. True
    when a comment with a count was found. Only the number changes, so a
    hand-trimmed provenance list stays as it is."""
    agents = Path(kb_path) / AGENTS_FILE
    if not agents.exists():
        return False
    pattern = re.compile(r"(<!--\s*akt:\s*{}\s*\|\s*)\d+( hits)".format(re.escape(learn_id)))
    text, count = pattern.subn(r"\g<1>{}\g<2>".format(hits), agents.read_text(), count=1)
    if count:
        agents.write_text(text)
    return bool(count)


def merge(kb_path, keep_id, drop_id, threshold, rule=None):
    """Fold `drop_id` into `keep_id`: two entries that are one lesson (issue #80).

    Counted apart, two wordings of one lesson sit at one hit each and never
    reach the threshold. The kept entry gets both story lists, and the dropped
    entry leaves the ledger.

    Hits are the two counts added, less one for each story that both entries
    list: a story that reinforced both is one piece of evidence. For entries
    whose hits equal their story count this is the number of distinct stories.
    It is not simply that number because some entries hold more hits than
    stories (one story reinforced them twice), and a merge must not lower a
    count.

    Returns (entry, proposal, note). `note` says what the caller still has to
    tell the user when the kept entry is a graduated rule.
    """
    if keep_id == drop_id:
        raise ValueError("cannot merge '{}' into itself".format(keep_id))
    if rule is not None and "|" in rule:
        raise ValueError("rule text must not contain '|'")
    entries = read_learnings(kb_path)
    keep, drop = _find(entries, keep_id), _find(entries, drop_id)
    if drop["status"].startswith("graduated"):
        # Its rule text is live in a rule file; removing the entry would orphan it.
        raise ValueError(
            "'{}' is {}: a graduated rule cannot be the dropped entry. "
            "Merge the other way: akt learn merge {} {}".format(
                drop_id, drop["status"], drop_id, keep_id))
    if rule is not None and keep["status"].startswith("graduated"):
        raise ValueError(
            "'{}' is {}: its rule text is already in a rule file, so --rule "
            "cannot replace it".format(keep_id, keep["status"]))
    shared = set(keep["stories"]) & set(drop["stories"])
    keep["hits"] = keep["hits"] + drop["hits"] - len(shared)
    keep["stories"] += [s for s in drop["stories"] if s not in keep["stories"]]
    keep["last"] = max(keep["last"], drop["last"])
    if rule is not None:
        keep["rule"] = rule
    entries.remove(drop)
    write_learnings(kb_path, entries)
    note = None
    if keep["status"] == "graduated-global":
        note = "(core: the hit count in the knowledge base AGENTS.md is now {})".format(
            keep["hits"]) if _set_rule_hits(kb_path, keep_id, keep["hits"]) else \
            "(core: no comment for this id was in the knowledge base AGENTS.md, " \
            "so only the ledger changed)"
    elif keep["status"] == "graduated-repo":
        note = "(repo-local: the comment in that repo's AGENTS.md/CLAUDE.md still " \
               "shows the old hit count)"
    proposal = _proposal(keep) \
        if keep["status"] == "candidate" and keep["hits"] >= threshold else None
    return keep, proposal, note


def wont(kb_path, learn_id):
    entries = read_learnings(kb_path)
    entry = _find(entries, learn_id)
    entry["status"] = "wont-graduate"
    write_learnings(kb_path, entries)
    return entry


def _tokens(entry):
    return set(tokenize(entry["rule"])) | set(tokenize(entry["id"]))


def _ranked(entries, text):
    """(-score, position, entry) for every entry that shares a word, best first."""
    ranked = [
        (-s, pos, entry)
        for pos, (s, entry) in enumerate(zip(scores(text, [_tokens(e) for e in entries]), entries))
        if s > 0
    ]
    ranked.sort(key=lambda t: t[:2])
    return ranked


def match_scored(kb_path, lesson, limit=5, status=None):
    """Ledger entries ranked against one lesson, best first.

    The scan pass used to read every candidate, and that list grows with every
    story. This ranks in the CLI and returns a handful, so the cost of the pass
    no longer depends on the ledger size.

    Ranking is `rank.scores`: a word in a few rules counts for a lot, a word in
    every rule for very little. Every status is ranked unless `status` is
    given, so a lesson that is already a graduated rule shows up as one and is
    not added again as a new candidate.

    Returns (entry, score) pairs. The score is divided by the weight of a word
    that one entry holds, so it reads the same as the ledger grows.
    """
    entries = read_learnings(kb_path)
    unit = math.log(len(entries) + 1) or 1.0
    found = [(e, -neg / unit) for neg, _, e in _ranked(entries, lesson)
             if not status or e["status"] == status]
    return found[:limit]


def match(kb_path, lesson, limit=5, status=None):
    """`match_scored` without the scores."""
    return [e for e, _ in match_scored(kb_path, lesson, limit, status)]


def rules_for(kb_path, task, limit=3):
    """`graduated-recall` rules that match a task description, best first.

    Scored against the whole ledger so a word's weight does not depend on how
    many rules happen to be on recall. Unlike `match`, a loose result is
    dropped (RULE_CUTOFF): a rule printed here reads as an instruction, so a
    wrong one costs more than a missing line.
    """
    entries = read_learnings(kb_path)
    floor = RULE_CUTOFF * math.log(len(entries) + 1)
    return [e for neg, _, e in _ranked(entries, task)
            if e["status"] == "graduated-recall" and -neg >= floor][:limit]


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
