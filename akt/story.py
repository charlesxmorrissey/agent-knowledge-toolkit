"""Story lifecycle: start, per-session handoff, finish (distill + index)."""
from pathlib import Path

from akt.frontmatter import build_frontmatter, parse_frontmatter, split_keys
from akt.paths import slugify, story_dir, next_session_number, rel_to_kb
from akt.index import build_index_line, append_index_line

_STORY_TEMPLATE = """

## Problem
{title}

## Decisions
- <decision> — because <why> — rejected <alternative>

## Outcome
<gotchas, what to watch>

## Links
"""

_SESSION_TEMPLATE = """# Session {n}

State:
Done:
Next:
Watch out:
"""

_REQUIRED_SECTIONS = ["## Problem", "## Decisions", "## Outcome"]
# keys is deliberately NOT required: it is a recall aid, and recall already
# tokenizes the slug, so an absent keys line costs little — while requiring
# it left stories half-written whenever a caller omitted it (issue #43).
_REQUIRED_META = ["repo", "slug", "summary"]


def _validate(text, meta):
    # Report every problem in one pass so a body that's wrong in both ways
    # costs one round trip, not two (issue #33).
    problems = []
    sections = [s for s in _REQUIRED_SECTIONS if s not in text]
    if sections:
        problems.append("missing sections: {}".format(sections))
    keys = [k for k in _REQUIRED_META if not meta.get(k, "").strip()]
    if keys:
        problems.append("frontmatter missing: {}".format(keys))
    if problems:
        raise ValueError("story.md " + "; ".join(problems))


def _normalize_keys(keys):
    return ", ".join(split_keys(keys or ""))


def start_story(kb_path, repo, title, date, keys=None):
    slug = slugify(title)
    d = story_dir(kb_path, repo, date, slug)
    if d.exists():
        raise FileExistsError(str(d))
    (d / "sessions").mkdir(parents=True)
    meta = {"repo": repo, "slug": slug, "date": date, "summary": "",
            "keys": _normalize_keys(keys)}
    (d / "story.md").write_text(build_frontmatter(meta) + _STORY_TEMPLATE.format(title=title))
    # Session handoffs are written by end_session (starting at 01.md), not pre-seeded —
    # so a single-session story has an empty sessions/ rather than a blank placeholder.
    return d


def end_session(story_path, body):
    sessions = Path(story_path) / "sessions"
    sessions.mkdir(exist_ok=True)
    n = next_session_number(sessions)
    f = sessions / "{:02d}.md".format(n)
    f.write_text(body if body and body.strip() else _SESSION_TEMPLATE.format(n=n))
    return f


def update_story(story_path, body, date):
    """Append a dated '## Update' section to an existing story.md."""
    story_md = Path(story_path) / "story.md"
    if not story_md.exists():
        raise FileNotFoundError(str(story_md))
    if not (body and body.strip()):
        raise ValueError("update body is empty")
    text = story_md.read_text()
    # No meta validation here: an update just appends text, so the fresh
    # start-story skeleton (empty summary/keys) is a valid target (issue #23).
    # finish_story validates when the story is indexed.
    story_md.write_text(
        text.rstrip("\n") + "\n\n## Update — {}\n\n{}\n".format(date, body.strip())
    )
    return story_md


def finish_story(kb_path, story_path, body=None, keys=None):
    """Write (if `body`) and index story.md. `keys` overrides the frontmatter's."""
    story_path = Path(story_path)
    story_md = story_path / "story.md"
    if body is not None:
        # Merge the body's frontmatter over the skeleton's so repo/slug/date
        # survive a body that omits them, and validate the composed text
        # BEFORE writing so a bad body can't destroy the skeleton (issue #26).
        old_meta, _ = parse_frontmatter(story_md.read_text()) if story_md.exists() else ({}, "")
        new_meta, new_body = parse_frontmatter(body)
        old_meta.update(new_meta)
        if keys is not None:
            old_meta["keys"] = _normalize_keys(keys)
        # Drop blank values (the skeleton's empty summary/keys): a blank
        # `keys: ` line in a written-but-unindexed story collided with the
        # caller's obvious repair, an insert of the missing line (issue #43).
        meta = {k: v for k, v in old_meta.items() if v.strip()}
        text = build_frontmatter(meta) + "\n" + new_body
    else:
        text = story_md.read_text()
        if keys is not None:
            meta, existing_body = parse_frontmatter(text)
            meta["keys"] = _normalize_keys(keys)
            text = build_frontmatter(meta) + "\n" + existing_body
    meta, _ = parse_frontmatter(text)
    try:
        _validate(text, meta)
    except ValueError as err:
        if body is None:
            raise
        if all(s in text for s in _REQUIRED_SECTIONS):
            # Body is structurally complete and only the frontmatter is short
            # (typically the fresh skeleton's blank summary/keys): keep it rather
            # than discard the distilled text (issue #39). Not indexed yet.
            story_md.write_text(text)
            raise ValueError(
                "{}; body written to story.md but NOT indexed — fill in the "
                "frontmatter and re-run finish-story without --stdin".format(err)
            )
        raise ValueError(
            "{}; nothing written — the --stdin body must carry a summary in "
            "its frontmatter and all required sections".format(err)
        )
    if body is not None or keys is not None:
        story_md.write_text(text)
    line = build_index_line(meta, rel_to_kb(kb_path, story_md))
    append_index_line(kb_path, line)
    return line
