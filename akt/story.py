"""Story lifecycle: start, per-session handoff, finish (distill + index)."""
from pathlib import Path

from akt.frontmatter import build_frontmatter, parse_frontmatter
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


def start_story(kb_path, repo, title, date):
    slug = slugify(title)
    d = story_dir(kb_path, repo, date, slug)
    if d.exists():
        raise FileExistsError(str(d))
    (d / "sessions").mkdir(parents=True)
    meta = {"repo": repo, "slug": slug, "date": date, "summary": "", "keys": ""}
    (d / "story.md").write_text(build_frontmatter(meta) + _STORY_TEMPLATE.format(title=title))
    (d / "sessions" / "01.md").write_text(_SESSION_TEMPLATE.format(n=1))
    return d


def end_session(story_path, body):
    sessions = Path(story_path) / "sessions"
    sessions.mkdir(exist_ok=True)
    n = next_session_number(sessions)
    f = sessions / "{:02d}.md".format(n)
    f.write_text(body if body and body.strip() else _SESSION_TEMPLATE.format(n=n))
    return f


def finish_story(kb_path, story_path, body=None):
    story_path = Path(story_path)
    story_md = story_path / "story.md"
    if body is not None:
        story_md.write_text(body)
    text = story_md.read_text()
    missing = [s for s in _REQUIRED_SECTIONS if s not in text]
    if missing:
        raise ValueError("story.md missing sections: {}".format(missing))
    meta, _ = parse_frontmatter(text)
    if not meta.get("summary"):
        raise ValueError("story.md frontmatter missing 'summary'")
    line = build_index_line(meta, rel_to_kb(kb_path, story_md))
    append_index_line(kb_path, line)
    return line
