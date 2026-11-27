"""Shared ranking: score bags of words against a query by rare shared words.

`recall` (stories) and `learn match` (ledger entries) both ask the same
question: which of these texts is closest to this sentence. Plain overlap
counts "the" as much as "ledger", so a long text wins on common words
(issue #76). Here a shared word counts for more the fewer texts hold it, and
a long text is marked down for its length.
"""
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return _TOKEN.findall(text.lower())


# Length normalization, with the usual BM25 constants. A bag is a set, so a
# word is present or absent and only the length term of BM25 is left.
_K = 1.2
_B = 0.75


def scores(query, bags):
    """One score per bag, in order. 0.0 means no shared word.

    A shared word adds log((N + 1) / bags holding it). The +1 keeps the weight
    above zero when every bag holds the word, so a corpus of one text can still
    match; such a word then adds the least of any.

    The sum is then scaled down for a bag longer than the average and up for a
    shorter one. A long text holds more words of every kind, so without this it
    collects rare-word hits it has not earned.
    """
    if not bags:
        return []
    df = {}
    for bag in bags:
        for tok in bag:
            df[tok] = df.get(tok, 0) + 1
    n = len(bags)
    avg = sum(len(bag) for bag in bags) / n or 1
    wanted = set(tokenize(query))
    out = []
    for bag in bags:
        raw = sum(math.log((n + 1) / df[tok]) for tok in wanted & bag)
        out.append(raw * (_K + 1) / (1 + _K * (1 - _B + _B * len(bag) / avg)))
    return out
