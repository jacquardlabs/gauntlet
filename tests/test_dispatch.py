#!/usr/bin/env python3
"""Unit tests for scripts/dispatch.py — the consumer's dispatch bookkeeping.

Self-running: `python3 tests/test_dispatch.py` prints OK.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import dispatch  # noqa: E402 — sys.path must be set first
import schema  # noqa: E402

ARTIFACT = {"kind": "changeset", "base": "a1b2c3d4e5f6", "head": "f6e5d4c3b2a1"}


def _judge(name, mounts="`acceptance`", standard="`security-checklist`"):
    return {
        "judge": name,
        "lane": "some lane",
        "mounts": mounts,
        "standard": standard,
        "path": f"agents/{name}.md",
    }


# ── standard resolution (the ruling that prose got wrong) ─────────────────────
def test_inline_standard_becomes_judge_name_plus_plugin_version():
    resolved = dispatch.standard_for("test-auditor", "(inline)")
    assert resolved["name"] == "test-auditor"
    assert resolved["version"] == dispatch.plugin_version() != "unknown"


def test_file_standard_keeps_its_own_name():
    assert dispatch.standard_for("security-auditor", "`security-checklist`") == {
        "name": "security-checklist"
    }


def test_directory_standard_drops_the_trailing_slash():
    assert dispatch.standard_for("code-auditor", "`idioms/`") == {"name": "idioms"}


def test_no_standard_object_ever_carries_the_charter_shorthand():
    for cell in ("(inline)", "`idioms/`", "`security-checklist`"):
        assert "(inline)" not in dispatch.standard_for("x", cell)["name"]
        assert not dispatch.standard_for("x", cell)["name"].endswith("/")


# ── selection ─────────────────────────────────────────────────────────────────
def test_a_judge_with_no_path_rule_always_runs():
    chosen = dispatch.selected([_judge("code-auditor")], ["README.md"], "acceptance")
    assert [j["judge"] for j in chosen] == ["code-auditor"]


def test_path_signals_drop_a_lane_the_artifact_cannot_touch():
    judges = [_judge("dependency-auditor"), _judge("accessibility-auditor")]
    assert dispatch.selected(judges, ["src/main.py"], "acceptance") == []
    chosen = dispatch.selected(judges, ["package-lock.json"], "acceptance")
    assert [j["judge"] for j in chosen] == ["dependency-auditor"]
    chosen = dispatch.selected(judges, ["src/components/Card.tsx"], "acceptance")
    assert [j["judge"] for j in chosen] == ["accessibility-auditor"]


def test_a_judge_not_declaring_the_mount_is_never_selected():
    judges = [_judge("security-auditor", mounts="`acceptance`")]
    assert dispatch.selected(judges, ["a.py"], "intake") == []


def test_every_path_signal_is_keyed_to_a_registered_judge():
    """The table joins to the roster by name; a stale key would silently stop
    filtering the lane it was written for."""
    registered = {
        j["judge"]
        for j in dispatch.charter.parse_charter(
            dispatch.charter.CHARTER.read_text()
        )[0]
    }
    assert set(dispatch.PATH_SIGNALS) <= registered, (
        f"unregistered keys: {set(dispatch.PATH_SIGNALS) - registered}"
    )


# ── invocations ───────────────────────────────────────────────────────────────
def test_every_invocation_is_contract_valid():
    judges = [_judge("code-auditor", standard="`idioms/`"), _judge("test-auditor", standard="(inline)")]
    built = dispatch.invocations(judges, ["a.py"], "acceptance", ARTIFACT, ["PRODUCT.md"])
    assert len(built) == 2
    for invocation in built:
        schema.validate_invocation(invocation)


def test_optional_fields_are_omitted_rather_than_nulled():
    built = dispatch.invocations([_judge("x")], ["a.py"], "acceptance", ARTIFACT)
    assert "context" not in built[0] and "receipts_path" not in built[0]


def test_a_bad_artifact_is_caught_before_dispatch_not_after():
    try:
        dispatch.invocations([_judge("x")], ["a.py"], "acceptance", {"kind": "changeset"})
    except ValueError as exc:
        assert "base" in str(exc)
        return
    raise AssertionError("expected validate_invocation to reject a headless changeset")


# ── the CLI ───────────────────────────────────────────────────────────────────
def test_cli_emits_valid_invocations_for_the_real_roster():
    with tempfile.TemporaryDirectory() as tmp:
        paths = Path(tmp) / "paths.txt"
        paths.write_text("scripts/report.py\ntests/test_report.py\n")
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts/dispatch.py"),
             "--base", "a1b2c3d4e5f6", "--head", "f6e5d4c3b2a1",
             "--paths", str(paths), "--context", "PRODUCT.md"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        built = json.loads(proc.stdout)
        assert built, "the real roster should select at least one judge"
        for invocation in built:
            schema.validate_invocation(invocation)
        names = {i["judge"] for i in built}
        assert "accessibility-auditor" not in names, "no frontend files changed"
        assert "dependency-auditor" not in names, "no manifest changed"


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
