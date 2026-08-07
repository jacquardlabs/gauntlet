#!/usr/bin/env python3
"""Compile judges' findings documents into one report.

The bookkeeping half of a consumer: read each judge's findings document,
validate it at the boundary, apply the ingest rules, order the result, and
render it. Prompts carry judgment; this file carries none — it never decides
whether a finding is right, only where it belongs and how it reads.

Two renderings:

- `markdown` (default) — the report a human reads in a terminal.
- `pr-comments` — JSON a consumer can post as PR review comments, split into the
  findings that can anchor to a diff line and those that cannot. Emitting is not
  posting; the consumer still asks first.

Standard library only, 3.9-compatible: this ships to consuming projects.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema

#: Most severe first. The contract's ladder, used for ordering only.
TIER_ORDER = {tier: i for i, tier in enumerate(schema.TIERS)}

TIER_LABEL = {
    "critical": "Critical — blocks the stamp",
    "important": "Important — fix this cycle",
    "track": "Track — log and revisit",
}


def load(
    directory: Path, expected: Optional[List[str]] = None
) -> Tuple[List[dict], List[str], List[str]]:
    """Read every findings document in `directory`.

    Returns the normalized documents, the ingest notes they produced, and the
    load failures. A malformed document is reported, never silently dropped:
    a judge whose output could not be read is not a judge that found nothing.

    `expected` is the roster the caller dispatched. Without it this function can
    only see documents that exist, so a judge that died before writing anything
    is invisible — the report would simply not mention that lane, which reads
    exactly like a lane with no findings. With it, absence is a failure like any
    other.

    Documents are also held to agreeing about the artifact. A directory reused
    across runs, or one judge re-dispatched after a new commit, otherwise yields
    a report titled with one span while carrying findings graded against
    another — and PR comments anchored to lines that moved.

    Every accommodation this boundary makes lands in the returned notes. The
    accommodations are deliberate — a code fence is unwrapped, an unreadable
    document skips the quote check, a lane nobody dispatched is still ingested —
    but an invisible one is a report that reads identically whether the check
    ran or silently did not.
    """
    documents: List[dict] = []
    notes: List[str] = []
    failures: List[str] = []

    for path in sorted(directory.glob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            # ValueError, not json.JSONDecodeError: a reply truncated mid-multibyte
            # raises UnicodeDecodeError, which is a ValueError and was escaping this
            # handler — taking every other lane's findings down with it, which is the
            # one failure mode this function exists to prevent. JSONDecodeError is
            # itself a ValueError, so the wider tuple loses nothing.
            failures.append(f"{path.name}: could not be read as JSON — {exc}")
            continue
        unfenced = False
        try:
            data = json.loads(raw)
        except ValueError as exc:
            # Parse first, de-frame only on failure: a reply that is already one
            # JSON object takes the identical path it always did, and the unwrap
            # can only ever recover a lane, never reinterpret a working one.
            body = _unfenced(raw)
            if body is None:
                failures.append(
                    f"{path.name}: could not be read as JSON — {exc}"
                    + (
                        "; a code fence was present but did not wrap the whole "
                        "reply, so nothing was unwrapped"
                        if _looks_fenced(raw)
                        else ""
                    )
                )
                continue
            try:
                data = json.loads(body)
            except ValueError as inner:
                failures.append(
                    f"{path.name}: could not be read as JSON even after unwrapping "
                    f"the code fence it arrived in — {inner}"
                )
                continue
            unfenced = True
        try:
            schema.validate_findings(data)
        except ValueError as exc:
            failures.append(f"{path.name}: does not satisfy the findings contract — {exc}")
            continue
        text, unread = _document_text(data["artifact"])
        normalized, doc_notes = schema.normalize_findings(data, text, unread)
        if documents and normalized["artifact"] != documents[0]["artifact"]:
            failures.append(
                f"{path.name}: judged a different artifact than "
                f"{documents[0]['judge']} did — {_artifact_id(normalized['artifact'])} "
                f"vs {_artifact_id(documents[0]['artifact'])}"
            )
            continue
        documents.append(normalized)
        if unfenced:
            notes.append(
                f"{normalized['judge']}: fence-unwrapped: {path.name} arrived inside "
                "a code fence, stripped as transport packaging before parsing"
            )
        notes.extend(f"{normalized['judge']}: {note}" for note in doc_notes)

    reported = {doc["judge"] for doc in documents}
    failures.extend(
        f"{judge}: dispatched but wrote no findings document"
        for judge in sorted(set(expected or []) - reported)
    )
    if expected:
        # The mirror of the line above, and the same reasoning: without a roster
        # this function cannot know, but with one, a document from a lane nobody
        # dispatched is a stale file from an earlier run whose findings are now
        # in this report — graded against an artifact it happens to agree with.
        notes.extend(
            f"{judge}: undispatched-lane: filed a findings document this run never "
            "asked for; its findings were ingested anyway"
            for judge in sorted(reported - set(expected))
        )

    return documents, notes, failures


#: A fence line: three or more backticks, optionally an info string (```json).
_FENCE_OPEN = re.compile(r"^`{3,}[ \t]*[A-Za-z0-9_+-]*[ \t]*$")
_FENCE_CLOSE = re.compile(r"^`{3,}[ \t]*$")


def _looks_fenced(raw: str) -> bool:
    """Whether any line opens a fence — true even when `_unfenced` refuses to
    strip it, which is what lets a rejected wrapper be named rather than
    silently read as an ordinary parse failure."""
    return any(line.lstrip().startswith("```") for line in raw.split("\n"))


def _unfenced(raw: str) -> Optional[str]:
    """The body of a code fence wrapping a whole reply, or None if none does.

    A fence is transport packaging, not content — the contract puts transport
    out of scope entirely ("whether the judge runs as a Task-tool subagent, a
    workflow `agent()` call, or a bare prompt, the payloads are the contract"),
    so removing a wrapper is categorically different from repairing a malformed
    document. Judges are still told to emit no fence, and every unwrap is noted:
    the point is to recover the lane *and* keep the drift reportable, since two
    lanes in fifteen were total losses to this at opus and sonnet alike (#61).

    The wrapper must be genuine: optional leading prose, an opening fence line,
    and a closing fence as the last non-blank line. The bytes between them are
    returned untouched. Anything after the close is the judge's own content, and
    dropping content would be the repair this deliberately is not.
    """
    lines = raw.split("\n")
    opened = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            opened = i
            break
    if opened is None or not _FENCE_OPEN.match(lines[opened].strip()):
        return None
    closed = None
    for j in range(len(lines) - 1, opened, -1):
        if lines[j].strip():
            closed = j
            break
    if closed is None or not _FENCE_CLOSE.match(lines[closed].strip()):
        return None
    return "\n".join(lines[opened + 1:closed])


def _document_text(artifact: dict) -> Tuple[Optional[str], Optional[str]]:
    """The judged document's text for the quote-or-demote ingest rule, and why
    it is missing when it is.

    `schema.normalize_findings` is pure and reads no files, so the read lives
    here: `artifact.path`, relative to `artifact.root` when set. `(None, None)`
    for any other artifact kind — the rule does not apply there, so nothing was
    accommodated. `(None, why)` when a document artifact cannot be read: the
    read still fails open, so a consumer compiling findings away from where the
    document lives gets its report rather than every critical demoted against
    text nobody saw — but the reason travels back, because a check that silently
    did not run renders exactly like one that ran and passed (#68).
    """
    if artifact.get("kind") != "document":
        return None, None
    try:
        text = (Path(artifact.get("root") or ".") / artifact["path"]).read_text(
            encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        return None, str(exc)
    return text, None


def _artifact_id(artifact: dict) -> str:
    kind = artifact.get("kind")
    if kind == "changeset":
        return f"{artifact.get('base', '?')[:12]}..{artifact.get('head', '?')[:12]}"
    if kind == "repository":
        return artifact.get("ref", "?")[:12]
    return artifact.get("path", "?")


def merge_by_locus(findings: List[dict]) -> List[dict]:
    """Collapse findings that name the same place into one.

    Two lanes reaching the same `path:line` is strong evidence the defect is
    real — and two comments on one line is how a reader learns to stop opening
    them. Those are different audiences: convergence is signal to whoever ran
    the review, noise to whoever reads the PR. So the evidence is kept as a
    `judges` list on one finding rather than as repeated comments.

    The survivor is the most severe, and among equals the best anchored — an
    anchored critical says more than an unanchored one, and a `sourced` finding
    more than an `inferred` one. Findings with no `path` are never merged: a
    document locus is too coarse to prove two lanes mean the same thing.
    """
    TIER = {tier: i for i, tier in enumerate(schema.TIERS)}
    BASIS = {"sourced": 0, "inferred": 1, "taste": 2}

    grouped: Dict[tuple, List[dict]] = {}
    singles: List[dict] = []
    for f in findings:
        path = f["locus"].get("path")
        line = f["locus"].get("line")
        if path is None or line is None:
            singles.append(f)
        else:
            grouped.setdefault((path, line), []).append(f)

    merged: List[dict] = []
    for group in grouped.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        best = sorted(
            group,
            key=lambda f: (
                TIER.get(f["tier"], len(TIER)),
                0 if f.get("anchor") else 1,
                BASIS.get(f["basis"], len(BASIS)),
                -len(f.get("failure_scenario", "")),
            ),
        )[0]
        winner = dict(best)
        winner["judges"] = sorted({f["_judge"] for f in group})
        # Keep every lane's recommendation: they often differ usefully, and the
        # one the survivor carries is not automatically the most actionable.
        others = [
            f["recommendation"]
            for f in group
            if f is not best and f.get("recommendation")
        ]
        if others:
            winner["also_recommended"] = others
        merged.append(winner)

    return merged + singles


def flatten(documents: List[dict]) -> List[dict]:
    """Every finding, tagged with its judge, most severe first.

    Within a tier, order is by judge then by locus, so two runs over the same
    artifact read the same way — a report whose order churns cannot be diffed.
    """
    findings = merge_by_locus([
        {**finding, "_judge": doc["judge"]}
        for doc in documents
        for finding in doc["findings"]
    ])
    return sorted(
        findings,
        key=lambda f: (
            TIER_ORDER.get(f["tier"], len(TIER_ORDER)),
            f["_judge"],
            f["locus"].get("path", f["locus"].get("section", "")),
            f["locus"].get("line", 0),
        ),
    )


def counts(findings: List[dict]) -> Dict[str, int]:
    """Per-tier tally, zero-filled — the renderers index every tier unconditionally."""
    tallied = Counter(f["tier"] for f in findings)
    return {tier: tallied[tier] for tier in schema.TIERS}


def _comment_body(finding: dict) -> str:
    """One finding as a PR comment: the claim and the fix, evidence collapsed.

    A margin note is not a report. The reader has the code on screen and wants
    two things by default — what is wrong and what to do — so those are the only
    lines that render open. The failure scenario runs ~94 words and the anchor
    ~103; both earn that length exactly when a reader disagrees, which is when
    they open the disclosure, and cost attention every other time.

    The anchor belongs here in particular. It is the checkable fact that earns a
    critical its tier, and this renderer used to drop it entirely — leaving the
    reader the verdict without the evidence for it.
    """
    judges = " + ".join(finding.get("judges") or [finding["_judge"]])
    lines = [f"**{finding['summary']}**"]

    if finding.get("recommendation"):
        lines.append(f"\n→ {finding['recommendation']}")

    detail = []
    if finding.get("anchor"):
        detail.append(f"**Anchor.** {finding['anchor']}")
    if finding.get("failure_scenario"):
        detail.append(f"**Fails when.** {finding['failure_scenario']}")
    detail.extend(
        f"**Also suggested.** {extra}"
        for extra in finding.get("also_recommended", [])
    )
    if finding.get("receipts"):
        detail.append("**Receipts.** " + ", ".join(f"`{r}`" for r in finding["receipts"]))

    caption = (
        f"{judges} · {finding['tier']} · {finding['dimension']} · {_grounds(finding)}"
    )
    if detail:
        lines.append(
            f"\n<details><summary>{caption}</summary>\n\n"
            + "\n\n".join(detail)
            + "\n</details>"
        )
    else:
        lines.append(f"\n_{caption}_")
    return "\n".join(lines)


def _attribution(finding: dict) -> str:
    """Which lane(s) raised this — plural when they converged on one locus."""
    judges = finding.get("judges") or [finding["_judge"]]
    return " + ".join(f"`{j}`" for j in judges)


def _grounds(finding: dict) -> str:
    """How the finding is grounded — the contract's basis, refined by level."""
    return finding["basis"] + (f"/{finding['level']}" if "level" in finding else "")


def _locus(locus: dict) -> str:
    if "path" in locus:
        return f"{locus['path']}:{locus['line']}" if "line" in locus else locus["path"]
    parts = [locus[k] for k in ("section", "cell") if k in locus]
    return " · ".join(parts)


def _describe_artifact(documents: List[dict]) -> str:
    if not documents:
        return "no artifact"
    artifact = documents[0]["artifact"]
    kind = artifact.get("kind")
    if kind == "changeset":
        span = f"{artifact.get('base', '?')[:12]}..{artifact.get('head', '?')[:12]}"
        return f"{artifact.get('pr') or 'changeset'} {span}"
    if kind == "repository":
        return f"repository at {artifact.get('ref', '?')[:12]}"
    return artifact.get("path", "document")


def render_markdown(
    documents: List[dict], notes: List[str], failures: List[str]
) -> str:
    findings = flatten(documents)
    tally = counts(findings)
    judges = ", ".join(sorted(d["judge"] for d in documents)) or "none"

    lines = [
        f"# Gauntlet — {_describe_artifact(documents)}",
        "",
        f"{tally['critical']} critical · {tally['important']} important · "
        f"{tally['track']} track — from {len(documents)} judges: {judges}",
        "",
    ]

    if failures:
        lines += ["## Judges that did not report", ""]
        lines += [f"- {failure}" for failure in failures]
        lines += ["", "These lanes are unjudged. Absence of findings here is not a clean result.", ""]

    for tier in schema.TIERS:
        in_tier = [f for f in findings if f["tier"] == tier]
        if not in_tier:
            continue
        lines += [f"## {TIER_LABEL[tier]}", ""]
        for f in in_tier:
            lines.append(
                f"### {f['summary']}\n\n"
                f"{_attribution(f)} · {f['dimension']} · {_locus(f['locus'])} "
                f"· {_grounds(f)}"
            )
            for label, key in (
                ("Anchor", "anchor"),
                ("Fails when", "failure_scenario"),
                ("Do", "recommendation"),
            ):
                if f.get(key):
                    lines.append(f"\n**{label}.** {f[key]}")
            for extra in f.get("also_recommended", []):
                lines.append(f"\n**Also.** {extra}")
            if f.get("receipts"):
                lines.append("\n**Receipts.** " + ", ".join(f"`{r}`" for r in f["receipts"]))
            lines.append("")

    if notes:
        # Not "Recorded differently than claimed": the list now also carries
        # checks that did not run and wrappers that were stripped, and filing
        # those under a heading about demotions would hide them in plain sight.
        lines += ["## What ingest changed or could not check", ""]
        lines += [f"- {note}" for note in notes]
        lines += [""]

    lines += ["## Coverage", ""]
    lines += [f"**{doc['judge']}** — {doc['coverage']}\n" for doc in sorted(documents, key=lambda d: d["judge"])]

    return "\n".join(lines).rstrip() + "\n"


def diff_lines(base: str, head: str, root: Optional[str] = None) -> Dict[str, set]:
    """Right-side line numbers present in the diff, per path.

    The reviews API rejects a comment on a line the diff does not contain, and it
    rejects the *whole review* — so one un-anchorable finding loses every finding.
    Returns an empty mapping if git cannot be run, which the caller treats as
    "anchor nothing" rather than "anchor everything".
    """
    try:
        diff = subprocess.run(
            ["git", "diff", "-U0", f"{base}..{head}"],
            cwd=root or None, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}

    valid: Dict[str, set] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            valid.setdefault(current, set())
        elif line.startswith("@@") and current:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or 1)
                valid[current].update(range(start, start + count))
    return valid


def render_pr_comments(
    documents: List[dict], notes: List[str], failures: List[str]
) -> str:
    """Actionable, anchorable findings as comments; everything else in the body.

    A finding anchors only when its locus names a path *and* a line the diff
    actually contains. Two ways to miss: a document locus with no path at all,
    and — the one that matters — a finding about a line that did not change.

    That second case is not an edge. "You changed X and never updated Y" is the
    shape of the most valuable findings a review produces: an undocumented status
    code in a versioned contract, an architecture doc the change falsified, a
    known-problems entry it silently resolved. None of those have a diff line,
    and on this tool's first real PR run all three were criticals. So the summary
    leads with them rather than trailing them.
    """
    findings = flatten(documents)
    tally = counts(findings)
    anchorable = (
        diff_lines(
            documents[0]["artifact"].get("base", ""),
            documents[0]["artifact"].get("head", ""),
            documents[0]["artifact"].get("root"),
        )
        if documents and documents[0]["artifact"].get("kind") == "changeset"
        else {}
    )
    comments = []
    unanchored = []

    for f in findings:
        body = _comment_body(f)
        locus = f["locus"]
        line = locus.get("line")
        # `track` means "revisit later"; an inline comment demands attention on
        # that line now. Posting one is a tier contradicting its own channel, and
        # a reader who opens three no-action comments stops opening them.
        if (
            f["tier"] != "track"
            and line is not None
            and line in anchorable.get(locus.get("path", ""), set())
        ):
            comments.append({"path": locus["path"], "line": line, "body": body})
        else:
            unanchored.append(f)

    summary = [
        f"**Gauntlet** — {tally['critical']} critical · {tally['important']} important · "
        f"{tally['track']} track, from {len(documents)} judges.",
    ]
    if failures:
        summary.append(
            "\n**Lanes that did not report** (unjudged, not clean):\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )
    if unanchored:
        # Most severe first: these are the findings a reader would otherwise never
        # see, since nothing in the diff carries them.
        summary.append(
            "\n**Findings with no diff line to anchor to** — mostly about what this "
            "change did *not* update:\n"
            + "\n\n".join(
                f"- `{_locus(f['locus'])}` **{f['tier'].upper()} · {f['_judge']}** — "
                f"{f['summary']}"
                + (f"\n\n  {f['recommendation']}" if f.get("recommendation") else "")
                for f in unanchored
            )
        )
    if notes:
        summary.append(
            "\n**What ingest changed or could not check:**\n"
            + "\n".join(f"- {note}" for note in notes)
        )
    summary.append(
        "\n**Coverage**\n"
        + "\n".join(f"- **{d['judge']}** — {d['coverage']}" for d in sorted(documents, key=lambda d: d["judge"]))
    )

    return json.dumps(
        {"summary": "\n".join(summary), "comments": comments}, indent=2
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--findings",
        required=True,
        help="Directory of findings documents, one JSON file per judge",
    )
    parser.add_argument(
        "--format", choices=("markdown", "pr-comments"), default="markdown"
    )
    parser.add_argument(
        "--expect",
        default="",
        help=(
            "Comma-separated judges the caller dispatched. Any that wrote no "
            "document are reported as lanes that did not report."
        ),
    )
    args = parser.parse_args()

    directory = Path(args.findings)
    if not directory.is_dir():
        print(f"gauntlet: not a directory: {directory}", file=sys.stderr)
        return 1

    expected = [j.strip() for j in args.expect.split(",") if j.strip()]
    documents, notes, failures = load(directory, expected)
    if not documents and not failures:
        print(f"gauntlet: no findings documents in {directory}", file=sys.stderr)
        return 1

    render = render_markdown if args.format == "markdown" else render_pr_comments
    print(render(documents, notes, failures))
    # A judge that could not be read leaves a lane unjudged, which the report
    # says out loud — and says again here, so a caller that only checks the exit
    # code cannot mistake a partial run for a complete one.
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
