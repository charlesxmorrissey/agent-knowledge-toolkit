"""A small log of `learn match` scores and what the agent did next (issue #75).

`learn match` prints a score per result, but the numbers are gone when the
session ends. This log keeps them so a cutoff can be chosen from real runs:
a match followed by a reinforce of one of its ids is a true match with a known
score, and a match followed by an add is a lesson with no match, whose top
score is the best loose one. `learn add --lesson` names the lesson an add
belongs to, so a pass where another lesson was dropped still pairs (issue #91).

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


def log_action(op, learn_id, lesson=None):
    """`op` is "reinforce" or "add". `lesson` is the text an add was matched as."""
    record = {"op": op, "id": learn_id}
    if lesson:
        record["lesson"] = lesson
    _append(record)


def _norm(lesson):
    """Lesson text compared without regard to case or spacing. Nothing looser:
    a closest-words pairing never fails and can pair the wrong lesson."""
    return " ".join((lesson or "").split()).casefold()


def lesson_in_last_pass(lesson, records=None):
    """True when the newest pass in the log matched this lesson text."""
    last = None
    for last in _batches(read_log() if records is None else records):
        pass
    return bool(last) and _norm(lesson) in {_norm(m.get("lesson")) for m in last["matches"]}


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
                batch, seen_action = {"matches": [], "reinforced": [], "adds": []}, False
            batch["matches"].append(r)
        elif batch is not None:
            seen_action = True
            if r["op"] == "reinforce":
                batch["reinforced"].append(r.get("id"))
            else:
                batch["adds"].append(r.get("lesson"))  # None when the add names no lesson
    if batch:
        yield batch


def outcomes(records):
    """Pair each matched lesson with what happened to it.

    Returns (true, loose, unresolved):
      true:  (score, id, lesson) when one of the lesson's result ids was
             reinforced in the same pass. An id that several lessons list
             counts for the lesson where it scored highest.
      loose: (top score, top id or None, lesson) when no result id was
             reinforced and an add names the lesson (`learn add --lesson`), or
             when the pass has an add without a name for every lesson that is
             still left over.
      unresolved: the count of lessons that fit neither. A pass with fewer
             such adds than leftover lessons does not say which lesson was
             dropped, so none of those leftovers are counted as loose.
    """
    true, loose, unresolved = [], [], 0
    for batch in _batches(records):
        leftover = []
        # A reinforced id credits one lesson: the one where it scored highest.
        # Two lessons in a pass can both list the entry, and the loose listing
        # would otherwise be recorded as a true match with a low score.
        owner = {}
        for i, m in enumerate(batch["matches"]):
            for r in m.get("results", []):
                if len(r) == 2 and r[0] in batch["reinforced"] \
                        and (r[0] not in owner or r[1] > owner[r[0]][0]):
                    owner[r[0]] = (r[1], i)
        for i, m in enumerate(batch["matches"]):
            results = [r for r in m.get("results", []) if len(r) == 2]
            hit = max((r for r in results if owner.get(r[0], (None, None))[1] == i),
                      key=lambda r: r[1], default=None)
            if hit:
                true.append((hit[1], hit[0], m.get("lesson", "")))
            else:
                top = results[0] if results else [None, 0.0]
                leftover.append((top[1], top[0], m.get("lesson", "")))
        named = {_norm(lesson) for lesson in batch["adds"] if lesson}
        loose.extend(item for item in leftover if _norm(item[2]) in named)
        leftover = [item for item in leftover if _norm(item[2]) not in named]
        unnamed = sum(1 for lesson in batch["adds"] if not lesson)
        if leftover and unnamed >= len(leftover):
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
        lines.append("unresolved (not reinforced, and no add names the lesson): {}".format(
            unresolved))
    if true and loose:
        lines.append("lowest true match: {:.1f} | highest loose result: {:.1f}".format(
            min(true)[0], max(loose)[0]))
    return lines
