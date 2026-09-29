#!/usr/bin/env python3
"""Dispatch every invocation headless and land each reply in the findings directory.

The transport half of a consumer's bookkeeping, between `dispatch.py` and
`report.py`. Each judge runs as its own `claude -p --agent gauntlet:<judge>`
session, in parallel; the runner — never the judge — writes the reply's text to
`<findings>/<judge>.json`, byte for byte. The orchestrating session never carries
a reply, so it never retypes one.

Two rules this holds rather than restates:

- **A judge never produces** (`reference/charter.md`, rule 2). The judge returns
  text; this script is the consumer persisting it. Each session is granted exactly
  the tools its agent file declares, and nothing is added to them.
- **An unparseable reply is a lane that did not report.** The runner writes what
  came back without looking at it — parsing is `report.py`'s verdict. When no reply
  came back at all (the process failed, timed out, or said it errored), nothing is
  written, and `report.py --expect` names the lane as one that wrote nothing.

Runtime dependency: the `claude` CLI on PATH (or `--claude`). Without it this
exits 3 and writes nothing, and the caller falls back to its own transport —
`commands/review.md` §3 names that path. Anything after `--` is passed to every
`claude` call unchanged: `--plugin-dir`, `--settings`, `--disallowedTools`, and
the like.

Every session starts in the caller's working directory, never in the tree it
judges: a session started inside a PR's worktree would load that tree's
CLAUDE.md and `.claude/` settings — hooks included — as trusted project config.
The tree is reached through `--add-dir` instead, which grants file access and
loads nothing.

Standard library only, 3.9-compatible: this ships to consuming projects.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_independence as charter

#: The plugin namespace a co-installed consumer's session resolves agents under.
PLUGIN = "gauntlet"

#: What the judge is told besides its invocation — the same sentence the Task
#: path in `commands/review.md` §3 gives it.
INSTRUCTION = (
    "Your entire reply must be the findings document, one JSON object and "
    "nothing else. The invocation follows."
)

#: Exit status when the CLI cannot be found — distinct from a lane failing (1)
#: and from an argparse usage error (2).
NO_CLI = 3

#: Seconds before a judge is abandoned, so one hung session cannot stall the run.
TIMEOUT = 1800.0


def prompt(invocation: Dict[str, object]) -> str:
    """The judge's whole prompt: the instruction, then its invocation verbatim."""
    return f"{INSTRUCTION}\n\n{json.dumps(invocation, indent=2)}\n"


def declared_tools(agent_file: Path) -> List[str]:
    """The tools the judge's agent file declares — the grant, never widened.

    Read with the independence check's own parser, so the runner grants exactly
    what that check guards. An agent file declaring nothing readable is refused:
    a session with no grant cannot read the artifact it judges.
    """
    frontmatter = charter._frontmatter(agent_file.read_text(encoding="utf-8"))
    tools = charter._declared_tools(frontmatter) if frontmatter is not None else None
    if not tools:
        raise ValueError(f"{agent_file}: declares no readable `tools:`")
    return tools


def command(
    claude: str,
    judge: str,
    tools: Sequence[str],
    root: Optional[str],
    extra: Sequence[str],
) -> List[str]:
    return [
        claude,
        "-p",
        "--agent",
        f"{PLUGIN}:{judge}",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--allowedTools",
        ",".join(tools),
        *(["--add-dir", root] if root else []),
        *extra,
    ]


def reply(stdout: str) -> Optional[str]:
    """The judge's reply from `--output-format json`, or `None` when there is none.

    The CLI prints either the result object or, under verbose settings, the whole
    message list with the result last; both are read. A result flagged `is_error`
    is the CLI's text, not the judge's, so it is no reply.
    """
    try:
        parsed = json.loads(stdout)
    except ValueError:
        return None
    candidates = parsed if isinstance(parsed, list) else [parsed]
    results = [
        c for c in candidates if isinstance(c, dict) and c.get("type") == "result"
    ]
    if not results or results[-1].get("is_error"):
        return None
    text = results[-1].get("result")
    return text if isinstance(text, str) else None


def run_one(
    invocation: Dict[str, object],
    tools: Sequence[str],
    findings: Path,
    claude: str,
    extra: Sequence[str],
    timeout: Optional[float],
) -> Tuple[str, Optional[str]]:
    """Run one judge; write its reply. Returns (judge, problem or None)."""
    judge = str(invocation["judge"])
    artifact = invocation.get("artifact")
    root = artifact.get("root") if isinstance(artifact, dict) else None
    try:
        proc = subprocess.run(
            command(claude, judge, tools, root, extra),
            input=prompt(invocation),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return judge, f"timed out after {timeout:g}s"
    except OSError as exc:
        return judge, f"could not start `{claude}`: {exc}"
    text = reply(proc.stdout)
    if proc.returncode != 0 or text is None:
        detail = (proc.stderr.strip() or proc.stdout.strip())[-500:]
        return judge, f"exited {proc.returncode} with no reply: {detail}"
    try:
        (findings / f"{judge}.json").write_bytes(text.encode("utf-8"))
    except OSError as exc:
        return judge, f"replied, but the reply could not be written: {exc}"
    return judge, None


def run(
    invocations: List[Dict[str, object]],
    findings: Path,
    claude: str,
    extra: Sequence[str],
    jobs: int,
    timeout: Optional[float],
) -> List[str]:
    """Run every invocation in parallel; return one problem line per failed lane."""
    judges, _ = charter.parse_charter(charter.CHARTER.read_text(encoding="utf-8"))
    files = {j["judge"]: charter.REPO / j["path"] for j in judges}
    unknown = sorted({str(i["judge"]) for i in invocations} - set(files))
    if unknown:
        raise ValueError(f"not a registered judge: {', '.join(unknown)}")
    grants = {str(i["judge"]): declared_tools(files[str(i["judge"])]) for i in invocations}
    findings.mkdir(parents=True, exist_ok=True)
    # A lane that fails writes nothing, so a file left by an earlier run into the
    # same directory would read as this run's reply. Clear each lane's file first.
    for judge in grants:
        (findings / f"{judge}.json").unlink(missing_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        outcomes = list(
            pool.map(
                lambda i: run_one(
                    i, grants[str(i["judge"])], findings, claude, extra, timeout
                ),
                invocations,
            )
        )
    return [f"{judge}: {problem}" for judge, problem in outcomes if problem]


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: List[str] = []
    if "--" in argv:
        cut = argv.index("--")
        argv, extra = argv[:cut], argv[cut + 1 :]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--invocations", required=True, help="dispatch.py's output")
    parser.add_argument("--findings", required=True, help="Directory each reply lands in")
    parser.add_argument("--claude", default="claude", help="The Claude Code CLI to run")
    parser.add_argument(
        "--jobs", type=int, default=0, help="Judges run at once; 0 means all of them"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT,
        help=f"Seconds before a judge is abandoned (default {TIMEOUT:g})",
    )
    args = parser.parse_args(argv)

    claude = shutil.which(args.claude)
    if claude is None:
        print(
            f"gauntlet: `{args.claude}` not found — no judge was run. Dispatch "
            f"through your own transport instead (commands/review.md §3).",
            file=sys.stderr,
        )
        return NO_CLI
    try:
        invocations = json.loads(Path(args.invocations).read_text(encoding="utf-8"))
        if not isinstance(invocations, list) or not all(
            isinstance(i, dict) and "judge" in i for i in invocations
        ):
            raise ValueError(
                f"{args.invocations}: not a list of invocations, each naming its judge"
            )
        problems = run(
            invocations,
            Path(args.findings),
            claude,
            extra,
            args.jobs or len(invocations),
            args.timeout,
        )
    except (OSError, ValueError) as exc:
        print(f"gauntlet: no judge was run — {exc}", file=sys.stderr)
        return 1
    for line in problems:
        print(f"gauntlet: {line}", file=sys.stderr)
    print(
        f"{len(invocations) - len(problems)} of {len(invocations)} judges replied "
        f"into {args.findings}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
