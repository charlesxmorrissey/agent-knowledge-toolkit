"""Command-line dispatch for the AKT kernel."""
import argparse
import sys
from datetime import date as _date
from pathlib import Path

from akt import config
from akt import story as story_mod
from akt import recall as recall_mod
from akt import index as index_mod
from akt import init as init_mod
from akt import install as install_mod
from akt import gitkb
from akt import learn as learn_mod


def _warn_if_dirty(kb):
    if gitkb.is_dirty(kb):
        sys.stderr.write(
            "⚠ knowledge base has uncommitted changes — a prior story "
            "may not have been saved; run /finish-story or commit it\n"
        )


def _print_entry(entry):
    # Path first on its own line (consumers parse paths), summary indented under it.
    print(entry["path"])
    if entry.get("summary"):
        print("    " + entry["summary"])


def _resolve_story_dir(kb, story_path):
    """Resolve a story-path argument to an existing story directory.

    Accepts the forms agents actually pass: absolute, KB-relative (as recall
    prints), or CWD-relative — with or without a trailing /story.md.
    Exits cleanly instead of letting a raw FileNotFoundError escape.
    """
    p = Path(story_path)
    if p.name == "story.md":
        p = p.parent
    if p.is_absolute() or not kb:
        candidates = [p]
    else:
        # Accept both <repo>/<date>-<slug> and the stories/-prefixed form
        # recall prints, so either can be copy-pasted (issue #21).
        candidates = [Path(kb) / p, p]
        if p.parts and p.parts[0] != "stories":
            candidates.insert(1, Path(kb) / "stories" / p)
    for c in candidates:
        if c.is_dir():
            return c
    sys.stderr.write(
        "story not found: {} (tried: {})\n".format(
            story_path, ", ".join(str(c) for c in candidates)
        )
    )
    sys.exit(2)


def _normalize_learn_story(s):
    """Ledger stories are <repo>/<date>-<slug>; also accept the
    stories/-prefixed (and /story.md-suffixed) form recall prints (issue #21)."""
    s = s.strip().strip("/")
    if s.endswith("/story.md"):
        s = s[: -len("/story.md")]
    if s.startswith("stories/"):
        s = s[len("stories/"):]
    return s


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

    sub.add_parser("install", help="symlink launcher, slash commands, and rule into ~/.claude and ~/.local/bin")

    ps = sub.add_parser("start-story", help="scaffold a new story")
    ps.add_argument("repo")
    ps.add_argument("title")
    ps.add_argument("--date", default=None)

    pe = sub.add_parser("end-session", help="write a session handoff from stdin")
    pe.add_argument("story_path")

    pf = sub.add_parser("finish-story", help="distill story.md (from stdin) and index it")
    pf.add_argument("story_path")
    pf.add_argument("--stdin", action="store_true", help="read distilled story.md body from stdin")

    pu = sub.add_parser("update-story", help="append a dated update section (from stdin) and commit")
    pu.add_argument("story_path")
    pu.add_argument("--stdin", action="store_true", help="read the update body from stdin")
    pu.add_argument("--date", default=None)

    pr = sub.add_parser("recall", help="print ranked story paths (with summaries) for a query")
    pr.add_argument("query")
    pr.add_argument("--limit", type=int, default=3)

    pl = sub.add_parser("latest", help="print the most recent story path for a repo")
    pl.add_argument("repo")

    sub.add_parser("reindex", help="rebuild INDEX.md from all story.md files")

    plearn = sub.add_parser("learn", help="evidence ledger: add/reinforce/graduate/wont/list/prune")
    lsub = plearn.add_subparsers(dest="learn_cmd", required=True)

    la = lsub.add_parser("add", help="new candidate at hits 1")
    # Positionals stay; --id/--rule are aliases agents guess from the sibling
    # verbs' flag style (issue #22).
    la.add_argument("id", nargs="?", default=None)
    la.add_argument("rule", nargs="?", default=None)
    la.add_argument("--id", dest="id_opt", help="alias for the positional id")
    la.add_argument("--rule", "--text", dest="rule_opt", help="alias for the positional rule")
    la.add_argument("--story", required=True, help="<repo>/<date>-<slug>")
    la.add_argument("--date", default=None)

    lr = lsub.add_parser("reinforce", help="bump hits; prints PROPOSE: at threshold")
    lr.add_argument("id")
    lr.add_argument("--story", required=True)
    lr.add_argument("--date", default=None)

    lg = lsub.add_parser("graduate", help="promote; global scope also writes KB AGENTS.md")
    lg.add_argument("id")

    lw = lsub.add_parser("wont", help="mark wont-graduate; stops proposals")
    lw.add_argument("id")

    ll = lsub.add_parser("list", help="print the ledger")
    ll.add_argument("--status", default=None, choices=learn_mod.STATUSES)

    lsub.add_parser("prune", help="print-only staleness report")

    return p


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)

    if args.cmd == "init":
        print(init_mod.init_kb(args.path))
        return 0

    if args.cmd == "install":
        return install_mod.install()

    if args.cmd == "start-story":
        kb = _require_kb()
        _warn_if_dirty(kb)
        d = args.date or _date.today().isoformat()
        print(story_mod.start_story(kb, args.repo, args.title, d))
        return 0

    if args.cmd == "end-session":
        sp = _resolve_story_dir(config.get("knowledge_base_path"), args.story_path)
        body = "" if sys.stdin.isatty() else sys.stdin.read()
        print(story_mod.end_session(sp, body))
        return 0

    if args.cmd == "finish-story":
        kb = _require_kb()
        sp = _resolve_story_dir(kb, args.story_path)
        body = sys.stdin.read() if args.stdin else None
        line = story_mod.finish_story(kb, sp, body)
        print(line)
        # Atomic capture: index + commit happen in one CLI invocation so the
        # commit can't be left as a separate step the agent forgets to run.
        sys.stderr.write(gitkb.commit_kb(kb, "story: {}/{}".format(sp.parent.name, sp.name)) + "\n")
        return 0

    if args.cmd == "update-story":
        kb = _require_kb()
        sp = _resolve_story_dir(kb, args.story_path)
        body = sys.stdin.read() if args.stdin else ""
        d = args.date or _date.today().isoformat()
        print(story_mod.update_story(sp, body, d))
        # Same atomic-capture rule as finish-story: append + commit in one invocation.
        sys.stderr.write(gitkb.commit_kb(kb, "story update: {}/{}".format(sp.parent.name, sp.name)) + "\n")
        return 0

    if args.cmd == "recall":
        kb = _require_kb()
        _warn_if_dirty(kb)
        for entry in recall_mod.recall(kb, args.query, args.limit):
            _print_entry(entry)
        return 0

    if args.cmd == "latest":
        kb = _require_kb()
        _warn_if_dirty(kb)
        entry = recall_mod.latest(kb, args.repo)
        if entry:
            _print_entry(entry)
        return 0

    if args.cmd == "reindex":
        lines = index_mod.reindex(_require_kb())
        print("{} stories indexed".format(len(lines)))
        return 0

    if args.cmd == "learn":
        kb = _require_kb()
        _warn_if_dirty(kb)
        today = getattr(args, "date", None) or _date.today().isoformat()
        try:
            _date.fromisoformat(today)  # reject e.g. --date 07/30/2026 before it ever hits the ledger
            if args.learn_cmd == "add":
                learn_id = args.id_opt or args.id
                rule = args.rule_opt or args.rule
                if not (learn_id and rule):
                    sys.stderr.write(
                        'usage: akt learn add <id> "<rule>" --story <repo>/<date>-<slug>\n'
                    )
                    sys.exit(2)
                entry = learn_mod.add(kb, learn_id, rule,
                                      _normalize_learn_story(args.story), today)
                print(learn_mod.build_learning_line(entry))
                sys.stderr.write(gitkb.commit_kb(kb, "learn: add {}".format(args.id)) + "\n")
            elif args.learn_cmd == "reinforce":
                threshold = int(config.get("learn_threshold") or 3)
                entry, proposal = learn_mod.reinforce(
                    kb, args.id, _normalize_learn_story(args.story), today, threshold)
                print(learn_mod.build_learning_line(entry))
                if proposal:
                    print(proposal)
                sys.stderr.write(gitkb.commit_kb(kb, "learn: reinforce {}".format(args.id)) + "\n")
            elif args.learn_cmd == "graduate":
                entry, block = learn_mod.graduate(kb, args.id)
                print(block)
                if entry["status"] == "graduated-repo":
                    print("(repo-local: append the block above to that repo's AGENTS.md/CLAUDE.md and commit it with the work)")
                sys.stderr.write(gitkb.commit_kb(kb, "learn: graduate {}".format(args.id)) + "\n")
            elif args.learn_cmd == "wont":
                entry = learn_mod.wont(kb, args.id)
                print(learn_mod.build_learning_line(entry))
                sys.stderr.write(gitkb.commit_kb(kb, "learn: wont-graduate {}".format(args.id)) + "\n")
            elif args.learn_cmd == "list":
                for entry in learn_mod.read_learnings(kb):
                    if args.status and entry["status"] != args.status:
                        continue
                    print(learn_mod.build_learning_line(entry))
            elif args.learn_cmd == "prune":
                cutoff = int(config.get("prune_days") or 90)
                stale_c, stale_g = learn_mod.prune_report(kb, today, cutoff)
                print("stale candidates (last reinforced > {} days ago):".format(cutoff))
                for entry in stale_c:
                    print("  " + learn_mod.build_learning_line(entry))
                print("graduated rules ripe for demotion review:")
                for entry in stale_g:
                    print("  " + learn_mod.build_learning_line(entry))
        except ValueError as err:
            sys.stderr.write(str(err) + "\n")
            sys.exit(2)
        return 0

    return 1
