#!/usr/bin/env python3
"""Assert every registered judge stays a judge.

`reference/charter.md` states two rules; this file enforces the mechanically
checkable half of them. What a judge may never do:

1. **Carry a mutation tool.** `Write`, `Edit`, `Task` and friends in an agent's
   `tools:` frontmatter are the difference between "returns findings" and
   "changes the artifact" — the whole basis for treating findings as machine
   facts rather than a participant's opinion.
2. **Name a slash command.** A gauntlet judge is dispatched by a consumer (a viva
   bundle, CI, a bare session) and routes no one anywhere. This is also the
   migration tripwire: the studious fleet mentions `/review`, `/retro`, and
   `/setup` about twenty times.
3. **Require a producer-private artifact.** `PLAN.md`, the build-evidence stores.
   The evidence contract a judge may cite is `docs/findings-contract.md` §6,
   which any executor can satisfy.

Plus charter integrity, so the roster cannot rot: every registered judge has a
file, declares at least one mount from the contract's own enum (imported, never
restated), and has exactly one anchor row.

**The surface is derived, never hardcoded** — the charter's Judges table names
the guarded files. A judge renamed in the charter but not on disk fails here
rather than silently falling off the surface, which is the failure mode a glob
would hide.

Standard library only, 3.9-compatible: this ships to consuming projects.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema

REPO = Path(__file__).resolve().parent.parent
CHARTER = REPO / "reference" / "charter.md"

#: A Judges-table row: | `judge` | lane | `mount`… | `standard` | `agents/file.md` |
JUDGE_ROW = re.compile(
    r"^\|\s*`(?P<judge>[a-z][a-z0-9-]*)`\s*\|"
    r"(?P<lane>[^|]*)\|"
    r"(?P<mounts>[^|]*)\|"
    r"(?P<standard>[^|]*)\|"
    r"\s*`(?P<path>[^`]+)`\s*\|",
    re.MULTILINE,
)

#: An Anchors-table row: | `judge` | what a critical must cite |
ANCHOR_ROW = re.compile(
    r"^\|\s*`(?P<judge>[a-z][a-z0-9-]*)`\s*\|\s*(?P<anchor>[^|]+?)\s*\|\s*$",
    re.MULTILINE,
)

#: Tools that change something. A judge carrying one of these has stopped being a
#: judge, whatever its prompt says. `Task` is here because dispatching another
#: agent is orchestration — a judge is a leaf, and gauntlet owns no scheduler.
MUTATION_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Task")

#: Artifacts only a producer run creates.
ARTIFACTS = re.compile(
    r"(?<![\w/-])(PLAN\.md|docs/jig/evidence|\.studious/build-evidence)"
)

#: Any slash-command invocation. Filesystem roots are paths, not commands — the
#: allowlist is about the filesystem and stays stable, unlike a list of door
#: names in somebody else's repo (which is what drifts).
FS_ROOTS = ("tmp", "usr", "etc", "var", "dev", "opt", "bin", "home")
#: A `/cmd` token that is not a path segment. Leading context is classified in
#: `_slash_command` rather than here, because one character — the backtick — is
#: genuinely ambiguous and a regex cannot see which way it points.
SLASH_COMMAND = re.compile(
    r"/(?!(?:{})(?![\w-]))(?P<cmd>[a-z][a-z0-9-]+)(?![\w/-])".format("|".join(FS_ROOTS))
)


def _slash_command(line: str) -> Optional[str]:
    """The slash command this line names, if any.

    A backtick before the slash points both ways, and both forms are real in the
    fleet being migrated:

    - `` `/review --delivery` `` — an **opening** backtick. A door reference, and
      the dominant form: missing it would let contamination through silently.
    - `` `git`/`grep`/file reads `` — a **closing** backtick. Ordinary prose.

    Which one it is depends on how many backticks precede it: an even count means
    the next backtick opens a code span, an odd count means it closes one. That is
    the whole reason this is a function and not another alternation.
    """
    for match in SLASH_COMMAND.finditer(line):
        start = match.start()
        if start == 0:
            return match.group("cmd")
        before = line[start - 1]
        if before in "`" and line.count("`", 0, start - 1) % 2 == 0:
            return match.group("cmd")  # opening backtick: a quoted command
        if before not in "`" and not (before.isalnum() or before in "_/-"):
            return match.group("cmd")  # space, paren, bracket, start of a clause
    return None

#: A Standard cell declaring that the judge's own prompt is the rubric.
INLINE_STANDARD = "(inline)"

#: `tools: Read, Grep, Bash` in YAML frontmatter.
TOOLS_LINE = re.compile(r"^tools:\s*(?P<tools>.+)$", re.MULTILINE)


def parse_charter(text: str) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    """The charter's two tables: the roster, and judge -> anchor requirement.

    An empty roster parses to `[]` — legitimate before the fleet migrates (#2),
    and reported as a count by `main()` so it can never masquerade as coverage.
    """
    judges = [
        {k: v.strip() for k, v in m.groupdict().items()}
        for m in JUDGE_ROW.finditer(text)
    ]
    # No overlap between the two row shapes: ANCHOR_ROW's second cell forbids an
    # interior pipe and must end the line, so a five-column roster row can never
    # match it.
    anchors = {
        m.group("judge"): m.group("anchor").strip() for m in ANCHOR_ROW.finditer(text)
    }
    return judges, anchors


def _cell_tokens(cell: str) -> List[str]:
    """Backticked tokens in a table cell, in order."""
    return re.findall(r"`([^`]+)`", cell)


def _standard_problems(judge: str, cell: str) -> List[str]:
    """Validate one roster row's Standard cell.

    Three legal forms, and the distinction between them is the ruling in the
    charter's "Two kinds of standard" section:

    - `` `name` `` — lookup data at `reference/name.md`. Sinks, defaults,
      signatures: the specifics a judge consults but would not recall verbatim.
    - `` `name/` `` — lookup data that varies by dimension, at `reference/name/`
      with at least one entry. The code lane's per-language idioms are the case
      this exists for.
    - `(inline)` — the judge's own prompt is the rubric, so `standard.name`
      echoes the judge name and `version` is the plugin's. Correct wherever the
      rubric is judgment rather than data; extracting one of those to a file
      splits a judge from its own identity and leaves both halves thinner.
    """
    problems: List[str] = []
    tokens = _cell_tokens(cell)
    # `(inline)` is legal bare or backticked, and both go through the same token
    # parse — a raw substring test would also match a Standard cell that merely
    # mentioned the word in a parenthetical.
    bare = cell.replace("`", " ").replace(",", " ").split()
    inline = INLINE_STANDARD in tokens or INLINE_STANDARD in bare
    named = [t for t in tokens if t != INLINE_STANDARD]

    if inline and named:
        return [
            f"charter: `{judge}` declares both {INLINE_STANDARD} and a rubric file "
            f"({', '.join(named)}) — a lane judges against one standard, not two"
        ]
    if not inline and not named:
        return [
            f"charter: `{judge}` names no standard — the invocation's `standard.name` "
            f"would have no source (contract §3). Use {INLINE_STANDARD} when the "
            f"judge's own prompt is the rubric"
        ]
    if len(named) > 1:
        # The invocation carries one `standard.name`, so a second rubric leaves the
        # consumer nothing defined to send.
        return [
            f"charter: `{judge}` names {len(named)} rubrics "
            f"({', '.join(named)}) — a lane judges against one standard, not two"
        ]

    for name in named:
        # A charter row is repo data, but the token reaches the filesystem: keep it
        # inside reference/ rather than trusting it to be well-behaved.
        if name.startswith("/") or ".." in Path(name).parts:
            problems.append(
                f"charter: `{judge}` judges against `{name}`, which escapes reference/"
            )
        elif name.endswith("/"):
            directory = REPO / "reference" / name.rstrip("/")
            if not directory.is_dir():
                problems.append(
                    f"charter: `{judge}` judges against `{name}`, but "
                    f"reference/{name} is not a directory"
                )
            elif not any(directory.glob("*.md")):
                problems.append(
                    f"charter: `{judge}` judges against `{name}`, but "
                    f"reference/{name} holds no rubric files"
                )
        elif not (REPO / "reference" / f"{name}.md").is_file():
            problems.append(
                f"charter: `{judge}` judges against `{name}`, but "
                f"reference/{name}.md does not exist — a standard nothing can read is "
                f"a lane with no rubric"
            )
    return problems


def charter_problems(text: str) -> List[str]:
    """Roster integrity: mounts valid, anchors paired, names unique."""
    judges, anchors = parse_charter(text)
    problems: List[str] = []

    counts = Counter(j["judge"] for j in judges)
    problems.extend(
        f"charter: `{name}` is registered {count} times — one judge, one row"
        for name, count in counts.items()
        if count > 1
    )

    for j in judges:
        mounts = _cell_tokens(j["mounts"])
        if not mounts:
            problems.append(
                f"charter: `{j['judge']}` declares no mount — a consumer would have "
                f"nothing valid to request (contract §3)"
            )
        problems.extend(
            f"charter: `{j['judge']}` declares mount {mount!r}, which is not "
            f"in the contract's enum {schema.MOUNTS}"
            for mount in mounts
            if mount not in schema.MOUNTS
        )
        problems.extend(_standard_problems(j["judge"], j["standard"]))

    roster = {j["judge"] for j in judges}
    problems.extend(
        f"charter: `{name}` has no anchor row — a critical from this lane would "
        f"have nothing to cite, so every one would be demoted at ingest"
        for name in sorted(roster - set(anchors))
    )
    problems.extend(
        f"charter: `{name}` has an anchor row but is not on the roster"
        for name in sorted(set(anchors) - roster)
    )
    return problems


def scan(rel: str, text: str) -> List[str]:
    """Check one judge file against the three prohibitions. Pure: text in,
    problems out, so tests drive it without touching disk."""
    problems: List[str] = []

    if match := TOOLS_LINE.search(text):
        tools = [t.strip() for t in match.group("tools").split(",")]
        problems.extend(
            f"{rel}: declares the {tool} tool — a judge returns findings and "
            f"never changes the artifact (charter rule 2). The consumer "
            f"persists the findings document."
            for tool in tools
            if tool in MUTATION_TOOLS
        )

    for n, line in enumerate(text.splitlines(), 1):
        if cmd := _slash_command(line):
            problems.append(
                f"{rel}:{n}: names the slash command /{cmd} — a judge is "
                f"dispatched by a consumer and routes no one anywhere\n"
                f"    {line.strip()}"
            )
        if match := ARTIFACTS.search(line):
            problems.append(
                f"{rel}:{n}: requires {match.group(1)}, which only a producer run "
                f"creates. The citable evidence contract is "
                f"docs/findings-contract.md §6\n    {line.strip()}"
            )
    return problems


def unregistered_agents(
    judges: List[Dict[str, str]], agents_dir: Optional[Path] = None
) -> List[str]:
    """Agent files that ship but appear on no charter row.

    The mirror of the missing-file check, and the one that actually matters at
    runtime: a file in `agents/` is dispatchable the moment the plugin is
    installed, whether or not anything governs it. Unregistered means no lane,
    no declared mount, and no anchor — so its criticals could never be demoted
    by the ingest rule that assumes an anchor requirement exists.
    """
    if agents_dir is None:
        agents_dir = REPO / "agents"
    if not agents_dir.is_dir():
        return []
    registered = {j["path"] for j in judges}
    return [
        f"{rel}: ships in agents/ but is registered on no charter row — an "
        f"unregistered judge is dispatchable but ungoverned (no lane, no mount, "
        f"no anchor)"
        for path in sorted(agents_dir.glob("*.md"))
        for rel in [f"agents/{path.name}"]
        if rel not in registered
    ]


def surface_paths(judges: Optional[List[Dict[str, str]]] = None) -> List[Path]:
    """Every guarded file: exactly the charter's registered judges."""
    if judges is None:
        judges, _ = parse_charter(CHARTER.read_text(encoding="utf-8"))
    return [REPO / j["path"] for j in judges]


def main() -> int:
    if not CHARTER.exists():
        print(f"Independence check FAILED: charter not found at {CHARTER}")
        return 1
    text = CHARTER.read_text(encoding="utf-8")
    judges, _ = parse_charter(text)

    problems = charter_problems(text)
    problems.extend(unregistered_agents(judges))
    for j in judges:
        path = REPO / j["path"]
        if not path.is_file():
            problems.append(
                f"charter: `{j['judge']}` is registered as {j['path']}, but that file "
                f"does not exist"
            )
            continue
        problems.extend(scan(j["path"], path.read_text(encoding="utf-8")))

    if problems:
        print("Independence check FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1

    if not judges:
        print(
            "Independence check passed: 0 judges registered — the roster is empty "
            "until the fleet migrates (issue #2). This is a vacuous pass; "
            "tests/test_independence.py is what proves the check has teeth."
        )
        return 0
    plural = "judge" if len(judges) == 1 else "judges"
    print(
        f"Independence check passed: {len(judges)} {plural}, derived from "
        f"reference/charter.md — none produces, routes, or requires a producer artifact."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
