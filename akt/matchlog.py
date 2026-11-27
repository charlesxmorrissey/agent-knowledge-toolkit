"""A small log of `learn match` scores and what the agent did next (issue #75).

`learn match` prints a score per result, but the numbers are gone when the
session ends. This log keeps them so a cutoff can be chosen from real runs:
a match followed by a reinforce of one of its ids is a true match with a known
score, and a match followed by an add is a lesson with no match, whose top
score is the best loose one.

The file sits beside the config file, outside the knowledge base, so a read
command never leaves the knowledge base dirty. One JSON object per line.
"""
import json
from datetime import datetime

from akt import config

LOG_FILE = "akt-match-log.jsonl"


def log_path():
    return config.config_path().parent / LOG_FILE


def _append(record):
    """Append one record. A log that cannot be written must not fail the command."""
    record = dict(record, t=datetime.now().isoformat(timespec="seconds"))
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def log_match(lesson, found):
    """`found` is the (entry, score) list `learn.match_scored` returns."""
    _append({"op": "match", "lesson": lesson,
             "results": [[e["id"], round(s, 2)] for e, s in found]})


def log_action(op, learn_id):
    """`op` is "reinforce" or "add"."""
    _append({"op": op, "id": learn_id})


def read_log():
    path = log_path()
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("op") in ("match", "reinforce", "add"):
            records.append(record)
    return records


def _batches(records):
    """Split the log into passes: a run of matches, then the actions after it."""
    batch, seen_action = None, False
    for r in records:
        if r["op"] == "match":
            if batch is None or seen_action:
                if batch:
                    yield batch
                batch, seen_action = {"matches": [], "reinforced": [], "adds": 0}, False
            batch["matches"].append(r)
        elif batch is not None:
            seen_action = True
            if r["op"] == "reinforce":
                batch["reinforced"].append(r.get("id"))
            else:
                batch["adds"] += 1
    if batch:
        yield batch


def outcomes(records):
    """Pair each matched lesson with what happened to it.

    Returns (true, loose, unresolved):
      true:  (score, id, lesson) when one of the lesson's result ids was
             reinforced in the same pass.
      loose: (top score, top id or None, lesson) when no result id was
             reinforced and the pass has an add for every such lesson.
      unresolved: the count of lessons that fit neither. A pass with fewer adds
             than leftover lessons does not say which lesson was dropped, so
             none of its leftovers are counted as loose.
    """
    true, loose, unresolved = [], [], 0
    for batch in _batches(records):
        leftover = []
        for m in batch["matches"]:
            results = [r for r in m.get("results", []) if len(r) == 2]
            hit = next((r for r in results if r[0] in batch["reinforced"]), None)
            if hit:
                true.append((hit[1], hit[0], m.get("lesson", "")))
            else:
                top = results[0] if results else [None, 0.0]
                leftover.append((top[1], top[0], m.get("lesson", "")))
        if leftover and batch["adds"] >= len(leftover):
            loose.extend(leftover)
        else:
            unresolved += len(leftover)
    return true, loose, unresolved


def report(records):
    """Lines for `akt learn scores`."""
    true, loose, unresolved = outcomes(records)
    lines = ["true matches (a result id was reinforced after the match): {}".format(len(true))]
    lines += ["  {:.1f}  [{}]  {}".format(s, i, lesson) for s, i, lesson in sorted(true)]
    lines.append("no match (the lesson was added as a new entry): {}".format(len(loose)))
    lines += ["  {:.1f}  [{}]  {}".format(s, i or "-", lesson)
              for s, i, lesson in sorted(loose, reverse=True)]
    if unresolved:
        lines.append("unresolved (no reinforce or add followed the match): {}".format(unresolved))
    if true and loose:
        lines.append("lowest true match: {:.1f} | highest loose result: {:.1f}".format(
            min(true)[0], max(loose)[0]))
    return lines
