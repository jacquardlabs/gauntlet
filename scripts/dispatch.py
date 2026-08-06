#!/usr/bin/env python3
"""Build the invocations a consumer dispatches, from the charter.

The dispatch half of a consumer's bookkeeping, and the counterpart to
`report.py`. It reads the roster, selects the judges whose lane the paths in
scope could touch, resolves each one's Standard cell into a `standard` object,
and **validates every invocation before it leaves** — the contract says both
validators are called where payloads cross the boundary, and prose cannot call a
validator.

Selection is a cost decision, never a judgment: every judge self-skips when its
lane does not apply, so a wrong guess wastes a dispatch and never a verdict.

Standard library only, 3.9-compatible: this ships to consuming projects.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_independence as charter
import schema

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / ".claude-plugin" / "plugin.json"

#: Which changed paths could put a lane in scope, keyed by **registered judge
#: name** so the table joins to the charter roster rather than to prose. A judge
#: with no rule here is dispatched unconditionally: the safe default is to run a
#: lane and let it self-skip, never to drop one because nobody wrote its rule.
PATH_SIGNALS: Dict[str, List[str]] = {
    "infra-auditor": [
        r"\.tf$", r"\.tfvars$", r"Dockerfile", r"docker-compose", r"\.github/workflows/",
        r"(^|/)(k8s|kubernetes|deploy|charts|helm)/", r"\.(ya?ml)$",
    ],
    "dependency-auditor": [
        r"(^|/)package(-lock)?\.json$", r"(^|/)yarn\.lock$", r"(^|/)pnpm-lock\.yaml$",
        r"(^|/)requirements[^/]*\.txt$", r"(^|/)pyproject\.toml$", r"(^|/)uv\.lock$",
        r"(^|/)poetry\.lock$", r"(^|/)go\.(mod|sum)$", r"(^|/)Gemfile(\.lock)?$",
        r"(^|/)Cargo\.(toml|lock)$",
    ],
    "frontend-reviewer": [
        r"\.(tsx|jsx|vue|svelte|astro|js|ts|mjs|cjs)$",
        r"(^|/)(components|pages|routes|layouts|features|views)/",
        r"(^|/)package\.json$",
    ],
    "ux-reviewer": [
        r"\.(tsx|jsx|vue|svelte|astro|html|hbs|erb)$",
        r"\.(css|scss|sass|less)$",
        r"(^|/)(components|pages|layouts|templates|views|styles)/",
    ],
    # Kept in step with reference/prompt-checklist.md's own signature table —
    # the lane it gates is the one that reads that table, so a signal list
    # narrower than the standard drops the lane instead of running it.
    "prompt-auditor": [
        r"(^|/)(agents|prompts|skills|commands|reference|output-styles)/",
        r"(^|/)(CLAUDE|AGENTS|SKILL|GEMINI)\.md$",
        r"(^|/)\.claude/",
        r"(^|/)\.cursorrules$",
        r"(^|/)\.cursor/rules/",
        r"(^|/)copilot-instructions\.md$",
        r"(^|/)system_prompt\.",
        r"\.prompt\.md$",
    ],
    "accessibility-auditor": [
        r"\.(tsx|jsx|vue|svelte|html|hbs|erb|css|scss|sass|less)$",
        r"(^|/)(components|pages|layouts|templates|views|styles)/",
    ],
}


#: Lanes that need an input beyond the artifact, keyed by registered judge name.
#: Without it the judge can only self-skip, so dispatching it costs a model call to
#: be told nothing. Matched against the invocation's `context` paths, not the
#: changed paths — a pre-mortem register is a file that exists, rarely one the
#: changeset touches.
CONTEXT_SIGNALS: Dict[str, str] = {
    "premortem-auditor": r"premortem|pre-mortem",
    "product-reviewer": r"PRODUCT\.md$",
}


def plugin_version() -> str:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


def standard_for(judge: str, cell: str) -> dict:
    """Resolve a charter Standard cell into the invocation's `standard` object.

    The cell is charter shorthand and the contract wants a name a reader can
    retrieve, so this maps rather than copies. `(inline)` means the judge's own
    prompt is the rubric — the charter rules that `standard.name` echoes the
    judge and `version` is the plugin's, which is what makes an inline standard
    citable at a version. Copying the literal `(inline)` through, as prose
    instructions did, cites nothing.
    """
    tokens = [t for t in charter._cell_tokens(cell) if t != charter.INLINE_STANDARD]
    if not tokens:
        return {"name": judge, "version": plugin_version()}
    return {"name": tokens[0].rstrip("/")}


def build_artifact(
    ref: Optional[str] = None,
    base: Optional[str] = None,
    head: Optional[str] = None,
    root: Optional[str] = None,
    pr: Optional[str] = None,
) -> dict:
    """The artifact this run judges: a `repository` when `ref` is given, a
    `changeset` otherwise (contract §3).

    The two are mutually exclusive rather than merged, because a repository
    artifact carries no `base` by design — a posture review measures the
    repository against a standard, never against an earlier revision of itself.
    Silently ignoring a stray `--base` would let a caller believe it scoped a
    standing review to a diff.
    """
    if ref:
        conflicting = [
            flag for flag, value in (("--base", base), ("--head", head), ("--pr", pr))
            if value
        ]
        if conflicting:
            raise ValueError(
                "--ref judges a repository at one point in time and takes no "
                + ", ".join(conflicting)
            )
        artifact = {"kind": "repository", "ref": ref}
    else:
        if not (base and head):
            raise ValueError(
                "a changeset needs --base and --head; pass --ref instead to judge "
                "a whole repository"
            )
        artifact = {"kind": "changeset", "base": base, "head": head}
        if pr:
            artifact["pr"] = pr
    if root:
        artifact["root"] = root
    return artifact


def selected(
    judges: List[dict],
    paths: List[str],
    mount: str,
    context: Optional[List[str]] = None,
) -> List[dict]:
    """The judges to dispatch.

    Every judge declaring `mount`, minus two exclusions: those whose path signals
    match nothing in the changeset, and those needing a context input that was not
    supplied. The second is not an optimization — a lane with no register or no
    product definition cannot answer its question at all, so dispatching it buys a
    self-skip at the price of a model call, on every run, forever.
    """
    chosen = []
    for judge in judges:
        name = judge["judge"]
        if mount not in charter._cell_tokens(judge["mounts"]):
            continue
        signals = PATH_SIGNALS.get(name)
        if signals and not any(
            re.search(pattern, path) for pattern in signals for path in paths
        ):
            continue
        needs = CONTEXT_SIGNALS.get(name)
        if needs and not any(re.search(needs, c) for c in (context or [])):
            continue
        chosen.append(judge)
    return chosen


def invocations(
    judges: List[dict],
    paths: List[str],
    mount: str,
    artifact: dict,
    context: Optional[List[str]] = None,
    receipts_path: Optional[str] = None,
) -> List[dict]:
    built = []
    for judge in selected(judges, paths, mount, context):
        invocation = {
            "contract_version": schema.CONTRACT_VERSION,
            "judge": judge["judge"],
            "mount": mount,
            "artifact": artifact,
            "standard": standard_for(judge["judge"], judge["standard"]),
        }
        if context:
            invocation["context"] = context
        if receipts_path:
            invocation["receipts_path"] = receipts_path
        schema.validate_invocation(invocation)
        built.append(invocation)
    return built


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="Base sha of the changeset")
    parser.add_argument("--head", help="Head sha of the changeset")
    parser.add_argument("--pr", help="Pull-request URL, when the changeset is a PR")
    parser.add_argument(
        "--ref",
        help="Judge a whole repository at this sha or ref, instead of a changeset",
    )
    parser.add_argument("--root", help="Repo root; defaults to the working directory")
    parser.add_argument(
        "--mount",
        default=None,
        choices=schema.MOUNTS,
        help="Defaults to posture with --ref, acceptance otherwise",
    )
    parser.add_argument(
        "--paths",
        required=True,
        help="File holding the paths in scope, one per line, or - for stdin. "
        "For a changeset these are the changed paths; for --ref, the repository's "
        "tracked files (git ls-files) — path signals scope lanes either way",
    )
    parser.add_argument("--context", default="", help="Comma-separated grounding docs")
    parser.add_argument("--receipts-path", help="Evidence log this run may cite")
    args = parser.parse_args()

    text = sys.stdin.read() if args.paths == "-" else Path(args.paths).read_text()
    paths = [line.strip() for line in text.splitlines() if line.strip()]

    judges, _ = charter.parse_charter(charter.CHARTER.read_text(encoding="utf-8"))
    if not judges:
        print("gauntlet: the charter registers no judges", file=sys.stderr)
        return 1

    mount = args.mount or ("posture" if args.ref else "acceptance")
    context = [c.strip() for c in args.context.split(",") if c.strip()]
    try:
        artifact = build_artifact(
            args.ref, args.base, args.head, args.root, args.pr
        )
        built = invocations(
            judges, paths, mount, artifact, context, args.receipts_path
        )
    except ValueError as exc:
        print(f"gauntlet: invalid invocation — {exc}", file=sys.stderr)
        return 1

    if not built:
        print(f"gauntlet: no judge declares mount {mount!r}", file=sys.stderr)
        return 1

    print(json.dumps(built, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
