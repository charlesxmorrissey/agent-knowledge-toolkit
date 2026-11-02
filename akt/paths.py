"""Path helpers: slugify titles, build story dirs, number sessions."""
import hashlib
import re
from pathlib import Path

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_SESSION = re.compile(r"^(\d+)\.md$")


def slugify(title):
    """ASCII slug of `title`. A title with no ASCII letters or digits (Japanese,
    Cyrillic, an emoji) used to slug to "", which made a `<date>-/` story dir
    with a blank `slug:` that finish-story could never index (issue #59). Such
    a title now slugs to `title-<8 hex of sha1>`: deterministic, so the same
    title still collides on the same day like any duplicate, and ASCII, so the
    index line and `learn --story` shape checks hold. The title itself is kept
    verbatim in the story's heading."""
    s = _SLUG_STRIP.sub("-", title.lower()).strip("-")
    if not s:
        s = "title-" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return s


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
