"""Recall: rank INDEX.md entries against a free-text query.

This is the single seam behind which retrieval lives: query -> ranked story paths.
Today it is keyword overlap; it can later become vector search without changing
callers or artifacts.
"""
import re

from akt.index import read_index_lines, parse_index_line

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _TOKEN.findall(text.lower())


def _haystack(entry):
    tokens = set(tokenize(entry["summary"]))
    tokens |= set(tokenize(entry["repo"]))
    tokens |= set(tokenize(entry["slug"]))
    for key in entry["keys"]:
        tokens |= set(tokenize(key))
    return tokens


def score(query_tokens, entry):
    hay = _haystack(entry)
    return sum(1 for qt in set(query_tokens) if qt in hay)


def recall(kb_path, query, limit=3):
    qtokens = tokenize(query)
    scored = []
    for line in read_index_lines(kb_path):
        entry = parse_index_line(line)
        if not entry:
            continue
        s = score(qtokens, entry)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["path"]))
    return [entry for _, entry in scored[:limit]]
