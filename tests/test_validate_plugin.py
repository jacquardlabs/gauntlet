#!/usr/bin/env python3
"""Unit tests for scripts/validate_plugin.py.

Self-running: `python3 tests/test_validate_plugin.py` prints OK.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import validate_plugin  # noqa: E402 — sys.path must be set first


def _manifest():
    return {
        "name": "gauntlet",
        "description": "Independent judges for pre-delivery artifacts.",
        "version": "0.1.0",
        "author": {"name": "Jacquard Labs"},
        "repository": "https://github.com/jacquardlabs/gauntlet",
        "license": "MIT",
        "keywords": ["review", "audit"],
    }


def _has(errors, fragment):
    assert any(fragment in e for e in errors), (
        f"expected an error containing {fragment!r}, got: {errors}"
    )


def test_the_real_manifest_is_valid():
    data = json.loads((REPO / ".claude-plugin/plugin.json").read_text())
    assert validate_plugin.validate(data) == []


def test_the_real_manifest_ships_the_registered_agents():
    """The manifest is what makes agents/ dispatchable, so its name must match
    the repo the charter's paths are relative to."""
    data = json.loads((REPO / ".claude-plugin/plugin.json").read_text())
    assert data["name"] == "gauntlet"
    assert (REPO / "agents").is_dir()


def test_valid_manifest_passes():
    assert validate_plugin.validate(_manifest()) == []


def test_required_fields():
    for field in validate_plugin.REQUIRED:
        data = _manifest()
        del data[field]
        _has(validate_plugin.validate(data), f"missing required field: {field}")


def test_name_must_be_kebab():
    data = _manifest()
    data["name"] = "Gauntlet Judges"
    _has(validate_plugin.validate(data), "must match")


def test_version_must_be_semver():
    data = _manifest()
    data["version"] = "v0.1"
    _has(validate_plugin.validate(data), "is not semver")


def test_author_must_carry_a_name():
    data = _manifest()
    data["author"] = {"url": "https://example.com"}
    _has(validate_plugin.validate(data), "author.name is required")
    data["author"] = "Jacquard Labs"
    _has(validate_plugin.validate(data), "must be an object")


def test_keywords_must_be_a_list():
    data = _manifest()
    data["keywords"] = "review"
    _has(validate_plugin.validate(data), "keywords must be an array")


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
