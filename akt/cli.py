"""Command-line dispatch for the AKT kernel."""
import argparse
import sys
from datetime import date as _date

from akt import config
from akt import story as story_mod
from akt import recall as recall_mod
from akt import index as index_mod
from akt import init as init_mod


def _require_kb():
    kb = config.get("knowledge_base_path")
    if not kb:
        sys.stderr.write("No knowledge_base_path configured. Run: python3 -m akt init <path>\n")
        sys.exit(2)
    return kb


def build_parser():
    p = argparse.ArgumentParser(prog="akt")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="create a knowledge base and record it in config")
    pi.add_argument("path")

    ps = sub.add_parser("start-story", help="scaffold a new story")
    ps.add_argument("repo")
    ps.add_argument("title")
    ps.add_argument("--date", default=None)

    pe = sub.add_parser("end-session", help="write a session handoff from stdin")
    pe.add_argument("story_path")

    pf = sub.add_parser("finish-story", help="distill story.md (from stdin) and index it")
    pf.add_argument("story_path")
    pf.add_argument("--stdin", action="store_true", help="read distilled story.md body from stdin")

    pr = sub.add_parser("recall", help="print ranked story paths for a query")
    pr.add_argument("query")
    pr.add_argument("--limit", type=int, default=3)

    sub.add_parser("reindex", help="rebuild INDEX.md from all story.md files")
    return p


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)

    if args.cmd == "init":
        print(init_mod.init_kb(args.path))
        return 0

    if args.cmd == "start-story":
        d = args.date or _date.today().isoformat()
        print(story_mod.start_story(_require_kb(), args.repo, args.title, d))
        return 0

    if args.cmd == "end-session":
        body = "" if sys.stdin.isatty() else sys.stdin.read()
        print(story_mod.end_session(args.story_path, body))
        return 0

    if args.cmd == "finish-story":
        body = sys.stdin.read() if args.stdin else None
        print(story_mod.finish_story(_require_kb(), args.story_path, body))
        return 0

    if args.cmd == "recall":
        for entry in recall_mod.recall(_require_kb(), args.query, args.limit):
            print(entry["path"])
        return 0

    if args.cmd == "reindex":
        lines = index_mod.reindex(_require_kb())
        print("{} stories indexed".format(len(lines)))
        return 0

    return 1
