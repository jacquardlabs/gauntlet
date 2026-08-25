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


def _git_repo(root: Path) -> str:
    """A one-commit repository at `root`, returning its sha.

    The tree-fidelity check reads the world, so the tests that exercise it need
    a world of their own — running them against this repo would pass or fail on
    whether the developer happened to have uncommitted work.
    """
    def git(*args):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root, check=True, capture_output=True, text=True,
        )

    git("init", "-q", "-b", "main")
    (root / "scripts").mkdir()
    (root / "scripts" / "report.py").write_text("# a tracked file\n")
    git("add", "-A")
    git("commit", "-qm", "one")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
    ).stdout.strip()

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
        "falsifiability-auditor", "trade-study-auditor", "product-reviewer"
    }, (
        "intake is the two ungated document lanes plus the context-gated product "
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


def test_cli_bare_document_run_dispatches_the_ungated_document_lanes():
    """A document with no context selects exactly the ungated lanes — the
    falsifiability and trade-study questions need nothing beyond the document
    itself, while product-reviewer stays behind its PRODUCT.md gate. Dispatch
    reads names, never content, so a document with no matrix still costs the
    trade-study lane a dispatch and buys a self-skip — the roster's safe
    default."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--document", "docs/plan.md"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    built = json.loads(proc.stdout)
    standards = {i["judge"]: i["standard"] for i in built}
    assert set(standards) == {"falsifiability-auditor", "trade-study-auditor"}
    for invocation in built:
        schema.validate_invocation(invocation)
    assert standards["falsifiability-auditor"]["name"] == "falsifiability-auditor", (
        "an (inline) standard resolves to the judge's own name plus the "
        "plugin version"
    )
    assert standards["trade-study-auditor"] == {"name": "trade-study-format"}, (
        "a file-backed standard keeps its own name, no version"
    )



# ── mount is derived from the kind, never picked (#67) ────────────────────────
def _mount_raises(kind, requested, fragment):
    try:
        dispatch.mount_for(kind, requested)
    except ValueError as exc:
        assert fragment in str(exc), exc
    else:
        raise AssertionError(f"a {kind} at {requested} was not refused")


def test_every_artifact_kind_has_exactly_one_mount():
    """The table is the doctrine `test_the_cli_reaches_every_mount` states, made
    enforceable: a kind with no mount is undispatchable, and a kind admitting two
    would put the choice back in the consumer's hands.
    """
    assert set(dispatch.MOUNT_FOR_KIND) == {"changeset", "document", "repository"}
    assert set(dispatch.MOUNT_FOR_KIND.values()) == set(schema.MOUNTS)


def test_an_asserted_mount_that_agrees_is_kept():
    assert dispatch.mount_for("document", "intake") == "intake"
    assert dispatch.mount_for("document") == "intake"


def test_a_document_is_refused_at_acceptance():
    """`--document --mount acceptance` dispatched the whole acceptance roster —
    eleven lanes whose standards read code, every one of them facing a document
    they were never told the quote rule for, so every critical demoted (#67).
    """
    for mount in ("acceptance", "posture"):
        _mount_raises("document", mount, "judged at 'intake'")


def test_a_changeset_and_a_repository_refuse_each_other_s_mount():
    for kind, wrong in (("changeset", "posture"), ("repository", "acceptance")):
        _mount_raises(kind, wrong, f"judged at {dispatch.MOUNT_FOR_KIND[kind]!r}")


def test_cli_refuses_an_off_mount_document_run():
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/dispatch.py"),
         "--document", "docs/plan.md", "--mount", "acceptance"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1, proc.stdout
    assert "judged at 'intake'" in proc.stderr, proc.stderr
    assert not proc.stdout.strip(), "a refused run still emitted invocations"


# ── the tree a posture run cites is the tree it reads (#65) ───────────────────
def test_tree_fidelity_passes_when_the_root_is_the_ref():
    with tempfile.TemporaryDirectory() as tmp:
        sha = _git_repo(Path(tmp))
        assert dispatch.tree_fidelity(sha, tmp) is None
        assert dispatch.tree_fidelity("HEAD", tmp) is None


def test_tree_fidelity_refuses_a_ref_that_is_not_the_tree():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _git_repo(root)
        (root / "second.txt").write_text("later\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "two"],
            cwd=root, check=True, capture_output=True,
        )
        mismatch = dispatch.tree_fidelity(first, tmp)
        assert mismatch and "cite another" in mismatch, mismatch


def test_tree_fidelity_refuses_a_dirty_tree_at_the_ref():
    """An untracked file is on disk and in no ref, so a judge reading
    `artifact.root` sees what the citation does not cover.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sha = _git_repo(root)
        (root / "untracked.py").write_text("# never committed\n")
        mismatch = dispatch.tree_fidelity(sha, tmp)
        assert mismatch and "uncommitted changes" in mismatch, mismatch


def test_tree_fidelity_refuses_what_git_cannot_resolve():
    """Refusal, not `report.py::diff_lines`'s degrade-to-empty: an unresolvable
    ref is exactly when the run would judge whatever is on disk.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _git_repo(Path(tmp))
        assert "cannot resolve" in (dispatch.tree_fidelity("v9.9.9", tmp) or "")
    with tempfile.TemporaryDirectory() as tmp:
        assert "cannot resolve" in (dispatch.tree_fidelity("HEAD", tmp) or "")


def test_cli_refuses_a_posture_run_whose_root_is_not_the_ref():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "tree"
        root.mkdir()
        sha = _git_repo(root)
        paths = Path(tmp) / "paths.txt"
        paths.write_text("scripts/report.py\n")
        (root / "untracked.py").write_text("# never committed\n")
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts/dispatch.py"),
             "--ref", sha, "--root", str(root), "--paths", str(paths)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 1, proc.stdout
        assert "uncommitted changes" in proc.stderr, proc.stderr
        assert "git worktree add --detach" in proc.stderr, (
            "the refusal never names the fix"
        )
        assert not proc.stdout.strip(), "a refused run still emitted invocations"


def test_a_changeset_run_never_pays_for_the_tree_check():
    """The check is scoped to `repository`: a changeset names two shas and a PR
    consumer already builds its worktree, so a git-less caller keeps working.
    """
    with tempfile.TemporaryDirectory() as tmp:
        paths = Path(tmp) / "paths.txt"
        paths.write_text("scripts/report.py\n")
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts/dispatch.py"),
             "--base", "a1b2c3d4e5f6", "--head", "f6e5d4c3b2a1",
             "--paths", str(paths)],
            capture_output=True, text=True, cwd=tmp,
        )
        assert proc.returncode == 0, proc.stderr


def test_the_cli_reaches_every_mount_the_contract_defines():
    """Mount is derived from the artifact kind, never picked by the consumer, so
    a mount no kind defaults to is a mount no entrypoint reaches without an
    explicit `--mount`. Pairs with test_independence's check that the command
    dispatches every kind: together they run from a typed argument to a judge.
    """
    with tempfile.TemporaryDirectory() as tmp:
        paths = Path(tmp) / "paths.txt"
        paths.write_text("scripts/report.py\n")
        tree = Path(tmp) / "tree"
        tree.mkdir()
        sha = _git_repo(tree)
        runs = (
            ["--base", "a1b2c3d4e5f6", "--head", "f6e5d4c3b2a1", "--paths", str(paths)],
            ["--document", "docs/plan.md"],
            ["--ref", sha, "--root", str(tree), "--paths", str(paths)],
        )
        reached = set()
        for args in runs:
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts/dispatch.py"), *args],
                capture_output=True, text=True,
            )
            assert proc.returncode == 0, proc.stderr
            mounts = {i["mount"] for i in json.loads(proc.stdout)}
            assert len(mounts) == 1, f"{args} produced mixed mounts: {mounts}"
            reached |= mounts
    assert reached == set(schema.MOUNTS), (
        f"no artifact kind defaults to {set(schema.MOUNTS) - reached}"
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
