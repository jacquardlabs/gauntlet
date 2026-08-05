#!/usr/bin/env python3
"""Shared schema contract for gauntlet's findings payloads (contract v1).

The one module a consumer imports at the boundary: `validate_invocation()` on
dispatch, `validate_findings()` on ingest, then `normalize_findings()` — the
reference implementation of the two ingest rules (anchor-or-demote,
taste-caps-at-track). `docs/findings-contract.md` is the normative text; where
this module and that doc disagree, the doc governs and the mismatch is a bug
here.

stdlib-only, no runtime dependency. Follows viva `scripts/schema.py`'s pattern:
TypedDicts document the shapes (no type checker in CI); the validators carry
the enforced rules.
"""
from __future__ import annotations

from typing import List, Tuple, TypedDict

CONTRACT_VERSION = 1
TIERS = ("critical", "important", "track")
BASES = ("sourced", "inferred", "taste")
LEVELS = ("high", "medium", "low")
MOUNTS = ("intake", "acceptance")
ARTIFACT_KINDS = ("changeset", "document")


# ── Shapes (documentation-only TypedDicts) ────────────────────────────────────
class Artifact(TypedDict, total=False):
    kind: str   # required — "changeset" | "document"
    base: str   # changeset: required — git sha
    head: str   # changeset: required — git sha
    root: str   # changeset: optional — defaults to the working directory
    pr: str     # changeset: optional — pull-request URL, carried through verbatim
    path: str   # document: required — markdown file


class Standard(TypedDict, total=False):
    name: str      # required
    version: str   # optional


class Invocation(TypedDict, total=False):
    contract_version: int   # required — exact match, CONTRACT_VERSION
    judge: str              # required — registered judge name
    mount: str              # required — "intake" | "acceptance"
    artifact: Artifact      # required
    standard: Standard      # required
    context: List[str]      # optional — grounding doc paths
    receipts_path: str      # optional — evidence log; absent = no citable receipts


class Locus(TypedDict, total=False):
    path: str      # code findings
    line: int      # optional, beside path
    section: str   # document findings
    cell: str      # matrix findings


class Finding(TypedDict, total=False):
    dimension: str          # required — the judge's own sub-check enum
    tier: str               # required — "critical" | "important" | "track"
    summary: str            # required — the claim, ≤15 words
    locus: Locus            # required — at least one of path / section / cell
    anchor: str             # required when tier == "critical"
    basis: str              # required — "sourced" | "inferred" | "taste"
    level: str              # optional — "high" | "medium" | "low"
    failure_scenario: str   # optional
    recommendation: str     # optional — advisory, never a patch
    receipts: List[str]     # optional — outputDigest citations


class FindingsDocument(TypedDict, total=False):
    contract_version: int   # required
    judge: str              # required — echoes the invocation
    mount: str              # required — echoes the invocation
    artifact: Artifact      # required — echoes the invocation
    standard: Standard      # required — echoes the invocation
    findings: List[Finding]  # required — may be empty; clean is valid
    coverage: str           # required — verified-clean / assumptions / limitations


# ── Field helpers ─────────────────────────────────────────────────────────────
def _require_str(obj: dict, field: str, where: str) -> None:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}.{field} must be a non-empty string")


def _optional_str(obj: dict, field: str, where: str) -> None:
    if field in obj and not isinstance(obj.get(field), str):
        raise ValueError(f"{where}.{field} must be a string")


def _require_version(obj: dict, where: str) -> None:
    value = obj.get("contract_version")
    # bool is an int subclass; `True` must not pass as version 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where}.contract_version must be an integer")
    if value != CONTRACT_VERSION:
        raise ValueError(
            f"{where}.contract_version {value} does not match "
            f"contract version {CONTRACT_VERSION} (exact match, no negotiation)"
        )


def _require_enum(obj: dict, field: str, allowed: tuple, where: str) -> None:
    if obj.get(field) not in allowed:
        raise ValueError(
            f"{where}.{field} must be one of {allowed}, got {obj.get(field)!r}"
        )


def _validate_artifact(artifact: object, where: str) -> None:
    if not isinstance(artifact, dict):
        raise ValueError(f"{where}.artifact must be an object")
    _require_enum(artifact, "kind", ARTIFACT_KINDS, f"{where}.artifact")
    if artifact["kind"] == "changeset":
        _require_str(artifact, "base", f"{where}.artifact")
        _require_str(artifact, "head", f"{where}.artifact")
        _optional_str(artifact, "root", f"{where}.artifact")
        _optional_str(artifact, "pr", f"{where}.artifact")
    else:  # document
        _require_str(artifact, "path", f"{where}.artifact")


def _validate_standard(standard: object, where: str) -> None:
    if not isinstance(standard, dict):
        raise ValueError(f"{where}.standard must be an object")
    _require_str(standard, "name", f"{where}.standard")
    _optional_str(standard, "version", f"{where}.standard")


# ── Boundary validation ───────────────────────────────────────────────────────
def validate_invocation(data: dict) -> None:
    """Raise `ValueError` if `data` is not a structurally valid invocation
    payload (contract §3). Call on dispatch."""
    if not isinstance(data, dict):
        raise ValueError("invocation must be a JSON object")
    _require_version(data, "invocation")
    _require_str(data, "judge", "invocation")
    _require_enum(data, "mount", MOUNTS, "invocation")
    _validate_artifact(data.get("artifact"), "invocation")
    _validate_standard(data.get("standard"), "invocation")
    if "context" in data:
        context = data.get("context")
        if not isinstance(context, list) or not all(
            isinstance(p, str) for p in context
        ):
            raise ValueError("invocation.context must be a list of strings")
    _optional_str(data, "receipts_path", "invocation")


def validate_findings(data: dict) -> None:
    """Raise `ValueError` if `data` is not a structurally valid findings
    document (contract §4). Call on ingest, before `normalize_findings`.

    Structural only: the anchor-or-demote and taste-tier rules are ingest
    normalizations, not rejections — they live in `normalize_findings()`.
    """
    if not isinstance(data, dict):
        raise ValueError("findings document must be a JSON object")
    _require_version(data, "findings")
    _require_str(data, "judge", "findings")
    _require_enum(data, "mount", MOUNTS, "findings")
    _validate_artifact(data.get("artifact"), "findings")
    _validate_standard(data.get("standard"), "findings")
    _require_str(data, "coverage", "findings")
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings.findings must be a list (empty is valid)")
    for i, f in enumerate(findings):
        where = f"findings.findings[{i}]"
        if not isinstance(f, dict):
            raise ValueError(f"{where} must be an object")
        _require_str(f, "dimension", where)
        _require_enum(f, "tier", TIERS, where)
        _require_str(f, "summary", where)
        _validate_locus(f.get("locus"), where)
        _require_enum(f, "basis", BASES, where)
        if "level" in f:
            _require_enum(f, "level", LEVELS, where)
        for optional in ("anchor", "failure_scenario", "recommendation"):
            _optional_str(f, optional, where)
        if "receipts" in f:
            receipts = f.get("receipts")
            if not isinstance(receipts, list) or not all(
                isinstance(r, str) for r in receipts
            ):
                raise ValueError(f"{where}.receipts must be a list of strings")


def _validate_locus(locus: object, where: str) -> None:
    if not isinstance(locus, dict):
        raise ValueError(f"{where}.locus must be an object")
    keys = [k for k in ("path", "section", "cell") if k in locus]
    if not keys:
        raise ValueError(
            f"{where}.locus must carry at least one of 'path', 'section', 'cell'"
        )
    for k in keys:
        _require_str(locus, k, f"{where}.locus")
    if "line" in locus:
        line = locus.get("line")
        if isinstance(line, bool) or not isinstance(line, int):
            raise ValueError(f"{where}.locus.line must be an integer")


# ── Ingest rules (reference implementation) ───────────────────────────────────
def normalize_findings(data: dict) -> Tuple[dict, List[str]]:
    """Apply the two ingest rules to a validated findings document. Pure —
    returns a new document plus the notes a compiled report must name.

    1. **Anchor-or-demote** (contract §4): a `critical` with no non-empty
       `anchor` is recorded `important`.
    2. **Taste caps at track** (contract §4/§5): a `basis: taste` finding never
       ranks above `track`. Applied after rule 1, so a taste critical lands at
       `track` either way.
    """
    notes: List[str] = []
    out = dict(data)
    out["findings"] = []
    for f in data.get("findings", []):
        nf = dict(f)
        if nf.get("tier") == "critical" and not (nf.get("anchor") or "").strip():
            nf["tier"] = "important"
            notes.append(
                f"anchor-or-demote: {nf.get('summary', '?')!r} recorded important "
                "(critical cited no anchor)"
            )
        if nf.get("basis") == "taste" and nf.get("tier") != "track":
            notes.append(
                f"taste-caps-at-track: {nf.get('summary', '?')!r} recorded track "
                f"(was {nf.get('tier')})"
            )
            nf["tier"] = "track"
        out["findings"].append(nf)
    return out, notes
