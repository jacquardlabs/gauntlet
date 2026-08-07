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

#: Everything an invocation needs except `artifact`, so an artifact built here
#: is proven to satisfy the contract's validator and not just this test's idea.
_INVOCATION_SHELL = {
    "contract_version": schema.CONTRACT_VERSION,
    "judge": "security-auditor",
    "mount": "acceptance",
    "standard": {"name": "security-checklist"},
}


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


# ── artifact construction ─────────────────────────────────────────────────────
def test_build_artifact_changeset():
    built = dispatch.build_artifact(base="a1b2c3d", head="e4f5a6b", pr="http://pr/1")
    assert built == {
        "kind": "changeset", "base": "a1b2c3d", "head": "e4f5a6b", "pr": "http://pr/1"
    }
    schema.validate_invocation({**_INVOCATION_SHELL, "artifact": built})


def test_build_artifact_repository():
    built = dispatch.build_artifact(ref="a1b2c3d", root="/srv/repo")
    assert built == {"kind": "repository", "ref": "a1b2c3d", "root": "/srv/repo"}
    schema.validate_invocation(
        {**_INVOCATION_SHELL, "mount": "posture", "artifact": built}
    )


def _build_raises(kwargs, fragment):
    try:
        dispatch.build_artifact(**kwargs)
    except ValueError as exc:
        assert fragment in str(exc), exc
        return
    raise AssertionError(f"expected ValueError containing {fragment!r} for {kwargs}")


def test_build_artifact_document():
    built = dispatch.build_artifact(document="docs/plan.md")
    assert built == {"kind": "document", "path": "docs/plan.md"}
    schema.validate_invocation(
        {**_INVOCATION_SHELL, "mount": "intake", "artifact": built}
    )


def test_build_artifact_document_carries_root():
    # `root` scopes every artifact kind (contract §3): the document path
    # resolves relative to it at ingest, so dispatch must pass it through.
    built = dispatch.build_artifact(document="docs/plan.md", root="/srv/repo")
    assert built == {"kind": "document", "path": "docs/plan.md", "root": "/srv/repo"}
    schema.validate_invocation(
        {**_INVOCATION_SHELL, "mount": "intake", "artifact": built}
    )


def test_build_artifact_refuses_a_diff_scoped_posture_run():
    """A stray --base on a repository run must fail loudly: silently dropping it
    would let a caller believe a standing review was scoped to a diff."""
    for kwargs in (
        {"ref": "a1b2c3d", "base": "e4f5a6b"},
        {"ref": "a1b2c3d", "head": "e4f5a6b"},
        {"ref": "a1b2c3d", "pr": "http://pr/1"},
    ):
        _build_raises(kwargs, "takes no")


def test_build_artifact_needs_base_and_head_without_a_ref():
    for kwargs in ({}, {"base": "a1b2c3d"}, {"head": "e4f5a6b"}):
        _build_raises(kwargs, "--base and --head")


def test_build_artifact_refuses_a_document_with_changeset_or_repo_scope():
    """A document is one named file, whole — a stray sha would let a caller
    believe it scoped the run to something else. `root` is not scope creep:
    every kind carries it (contract §3)."""
    for kwargs in (
        {"document": "docs/plan.md", "ref": "a1b2c3d"},
        {"document": "docs/plan.md", "base": "a1b2c3d"},
        {"document": "docs/plan.md", "head": "e4f5a6b"},
        {"document": "docs/plan.md", "pr": "http://pr/1"},
    ):
        _build_raises(kwargs, "takes no")


# ── mount selection ───────────────────────────────────────────────────────────
def test_posture_and_acceptance_select_disjoint_judges():
    # Judges with no path or context signal, so this isolates mount filtering.
    roster = [
        _judge("code-auditor", mounts="`acceptance`"),
        _judge("review-security", mounts="`posture`"),
        _judge("test-auditor", mounts="`acceptance`, `posture`"),
    ]
    at_posture = {j["judge"] for j in dispatch.selected(roster, ["a.py"], "posture")}
    at_acceptance = {
        j["judge"] for j in dispatch.selected(roster, ["a.py"], "acceptance")
    }
    assert at_posture == {"review-security", "test-auditor"}
    assert at_acceptance == {"code-auditor", "test-auditor"}


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


# ── context gating ────────────────────────────────────────────────────────────
def test_a_lane_needing_context_it_did_not_get_is_not_dispatched():
    """A lane with no register cannot answer its question, so dispatching it buys
    a self-skip at the price of a model call — on every run, forever."""
    judges = [_judge("premortem-auditor"), _judge("code-auditor")]
    without = dispatch.selected(judges, ["a.py"], "acceptance", ["CLAUDE.md"])
    assert [j["judge"] for j in without] == ["code-auditor"]


def test_the_same_lane_is_dispatched_once_its_input_is_present():
    judges = [_judge("premortem-auditor")]
    with_reg = dispatch.selected(
        judges, ["a.py"], "acceptance", ["docs/premortems/loop-driver.md"]
    )
    assert [j["judge"] for j in with_reg] == ["premortem-auditor"]


def test_product_lane_needs_a_product_definition():
    judges = [_judge("product-reviewer", mounts="`intake`, `acceptance`")]
    assert dispatch.selected(judges, ["a.py"], "acceptance", ["CLAUDE.md"]) == []
    got = dispatch.selected(judges, ["a.py"], "acceptance", ["PRODUCT.md"])
    assert [j["judge"] for j in got] == ["product-reviewer"]


def test_document_selection_skips_path_signals():
    """A document has no changed paths to sniff — the consumer named it — so a
    lane whose path signals would drop it from any changeset still runs."""
    judges = [
        _judge("dependency-auditor", mounts="`intake`"),
        _judge("code-auditor", mounts="`intake`"),
    ]
    chosen = dispatch.selected(judges, None, "intake")
    assert [j["judge"] for j in chosen] == ["dependency-auditor", "code-auditor"]


def test_document_selection_keeps_the_context_gates():
    judges = [_judge("product-reviewer", mounts="`intake`, `acceptance`")]
    assert dispatch.selected(judges, None, "intake") == []
    got = dispatch.selected(judges, None, "intake", ["PRODUCT.md"])
    assert [j["judge"] for j in got] == ["product-reviewer"]


def test_document_selection_keeps_the_mount_gate():
    judges = [_judge("security-auditor", mounts="`acceptance`")]
    assert dispatch.selected(judges, None, "intake") == []


def test_the_signal_tables_share_no_key():
    """The empty-selection message derives each dropped judge's reason from
    which table holds it; a judge in both would make that reason a guess."""
    assert not set(dispatch.PATH_SIGNALS) & set(dispatch.CONTEXT_SIGNALS)


def test_context_signals_are_keyed_to_registered_judges():
    registered = {
        j["judge"]
        for j in dispatch.charter.parse_charter(
            dispatch.charter.CHARTER.read_text()
        )[0]
    }
    assert set(dispatch.CONTEXT_SIGNALS) <= registered


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


def test_cli_document_needs_no_paths_and_defaults_mount_to_intake():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--document", "docs/plan.md", "--context", "PRODUCT.md"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    built = json.loads(proc.stdout)
    assert {i["judge"] for i in built} == {
        "falsifiability-auditor", "product-reviewer"
    }, (
        "intake is the ungated falsifiability lane plus the context-gated product "
        "lane today; a new declarer means this assertion is stale, not wrong"
    )
    for invocation in built:
        schema.validate_invocation(invocation)
        assert invocation["mount"] == "intake"
        assert invocation["artifact"] == {"kind": "document", "path": "docs/plan.md"}


def test_cli_changeset_still_requires_paths():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--base", "a1b2c3d4e5f6", "--head", "f6e5d4c3b2a1"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
    assert "--paths" in proc.stderr


def test_cli_refuses_paths_beside_a_document():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--document", "docs/plan.md", "--paths", "paths.txt"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
    assert "takes no --paths" in proc.stderr


def test_cli_bare_document_run_dispatches_the_falsifiability_lane():
    """A document with no context selects exactly the ungated lane — the
    falsifiability question needs nothing beyond the document itself, while
    product-reviewer stays behind its PRODUCT.md gate. This replaces the
    empty-selection test that pinned the gate-naming message: an ungated
    declarer always survives intake selection now, so that branch is
    unreachable with the shipped roster."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--document", "docs/plan.md"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    built = json.loads(proc.stdout)
    assert {i["judge"] for i in built} == {"falsifiability-auditor"}
    schema.validate_invocation(built[0])
    assert built[0]["standard"]["name"] == "falsifiability-auditor", (
        "an (inline) standard resolves to the judge's own name plus the "
        "plugin version"
    )


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
