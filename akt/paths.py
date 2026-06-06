"""Path helpers: slugify titles, build story dirs, number sessions."""
import re
from pathlib import Path

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_SESSION = re.compile(r"^(\d+)\.md$")


def slugify(title):
    s = _SLUG_STRIP.sub("-", title.lower())
    return s.strip("-")


def story_dir(kb_path, repo, date, slug):
    return Path(kb_path) / "stories" / repo / "{}-{}".format(date, slug)


def next_session_number(sessions_dir):
    sessions_dir = Path(sessions_dir)
    if not sessions_dir.exists():
        return 1
    nums = []
    for p in sessions_dir.glob("*.md"):
        m = _SESSION.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def rel_to_kb(kb_path, target):
    return str(Path(target).relative_to(Path(kb_path)))
