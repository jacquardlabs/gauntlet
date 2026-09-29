#!/usr/bin/env python3
"""A type standard can scope the document lanes: a PRD defers its technical half to its tech spec.

The shape lives in reference/type-standard-format.md; the lanes that read it are
falsifiability-auditor and product-reviewer. These tests hold the three in step: every
shipped standard has the required parts, its `## Defers to` section names one receiving
type and a claim table, and both lanes name the deferral rule and its guard.
Self-running: `python3 tests/test_type_standards.py` prints OK.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dispatch  # noqa: E402 — sys.path must be set first

FORMAT = ROOT / "reference" / "type-standard-format.md"
LANES = ("falsifiability-auditor", "product-reviewer")
DEFERS = re.compile(r"^## Defers to `([a-z][a-z0-9-]*)`$", re.MULTILINE)


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def _claims(section):
    """Rows of the claim table: (claim, [dimensions])."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|") and not set(line) <= set("|- ")
    ]
    return [(row[0], re.findall(r"`([a-z-]+)`", row[1])) for row in rows[1:]]


def _dimensions(judge):
    text = (ROOT / "agents" / f"{judge}.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\d+\. \*\*[^*]+\*\* \(`([a-z-]+)`\)", text, re.MULTILINE))


def test_every_shipped_standard_has_the_required_parts():
    for name, rel in dispatch.TYPE_STANDARDS.items():
        text = (ROOT / "reference" / rel).read_text(encoding="utf-8")
        assert text.startswith(f"# Type standard — {name}\n"), rel
        assert "\n## Must commit to\n" in text, rel
        assert "type-standard-format.md" in text, f"{rel} does not cite its shape"


def test_a_deferral_names_one_receiving_type_and_real_dimensions():
    known = set().union(*(_dimensions(j) for j in LANES))
    for rel in dispatch.TYPE_STANDARDS.values():
        text = (ROOT / "reference" / rel).read_text(encoding="utf-8")
        receivers = DEFERS.findall(text)
        assert len(receivers) <= 1, f"{rel} defers to {receivers}: one type only"
        if not receivers:
            continue
        claims = _claims(_section(text, "## Defers to"))
        assert claims, f"{rel} declares a deferral with no claims"
        for claim, dims in claims:
            assert dims, f"{rel}: '{claim}' names no dimension"
            assert set(dims) <= known, f"{rel}: '{claim}' names {set(dims) - known}"


def test_the_prd_defers_the_technical_half_to_tech_spec():
    text = (ROOT / "reference" / dispatch.TYPE_STANDARDS["prd"]).read_text(encoding="utf-8")
    assert DEFERS.findall(text) == ["tech-spec"]
    deferred = {d for _, dims in _claims(_section(text, "## Defers to")) for d in dims}
    # The five technical importants on the viva #239 PRD run filed under these.
    assert {"sequencing", "verifiability", "commitment", "simplicity"} <= deferred
    committed = _section(text, "## Must commit to")
    assert "success signal" in committed.lower(), "the product signal must not defer"


def test_both_document_lanes_carry_the_rule_and_its_guard():
    for judge in LANES:
        text = " ".join((ROOT / "agents" / f"{judge}.md").read_text(encoding="utf-8").split())
        assert "## Defers to" in text, judge
        assert "reference/type-standard-format.md" in text, judge
        assert "filed at `track` with its summary beginning `Deferred to <type>:`" in text, judge
        assert 'the spec will cover this" defers nothing' in text or (
            'the spec will cover this" is a `commitment` finding' in text
        ), f"{judge} lets the judged document declare its own deferral"


def test_the_format_keeps_deferral_declared_data():
    text = " ".join(FORMAT.read_text(encoding="utf-8").split())
    assert "**Only a standard declares a deferral.**" in text
    assert "is filed at `track`, whatever tier it would have had" in text
    assert "`coverage` names the standard, the receiving type, and the count deferred" in text


def main():
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    for name, fn in tests:
        fn()
        print(f"  {name}")
    print(f"OK ({len(tests)} tests)")


if __name__ == "__main__":
    main()
