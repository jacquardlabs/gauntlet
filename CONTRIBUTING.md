# Contributing

## Repo settings

Matched to the sibling repos (studious, viva), with one deliberate difference:

| Setting | Value | Why |
|---|---|---|
| Merge method | squash only | One commit per PR on `main`; merge commits and rebase-merge are off. |
| Delete branch on merge | on | Branches are disposable; the PR is the record. |
| Force push to `main` | blocked | |
| Delete `main` | blocked | |
| Pull request required | yes, 0 approvals | A solo repo still gets the PR surface — CI, diff, discussion — without a second person to wait for. |
| Branches up to date before merge | yes | Stacked PRs rebase onto `main` as each lands. |
| **Status checks required** | **yes — all four** | **The deliberate difference.** studious and viva have branch protection but do not require checks, so a red PR is mergeable there. Here the checks *are* the product's own discipline; a fleet whose independence check is advisory is a fleet with no independence check. |

Required contexts, matching the CI job names exactly — renaming a job means updating
the protection in the same change, or the old context never reports and every PR wedges:

- `unit tests (Python 3.9)`
- `unit tests (Python 3.13)`
- `judge independence`
- `ruff + version floor`

## Local checks

The full CI suite, all stdlib except the linters:

```bash
for t in tests/test_*.py; do python3 "$t"; done
python3 scripts/check_independence.py
uv run --no-project --with ruff==0.16.0 ruff check scripts tests
uv run --no-project --with vermin==1.8.0 vermin --no-tips -t=3.9- scripts/
```

## Conventions

- **Conventional Commits** for commit subjects and PR titles.
- **3.9 floor for `scripts/`**, enforced by vermin: those files ship to consuming
  projects and run on whatever `python3` is there. `tests/` may use anything the CI
  matrix covers.
- **Ruff's rule set is pinned explicitly** in `pyproject.toml`, not extended from the
  defaults — a floating rule set turns a pinned linter into an unpinned one.
- **Register a judge in `reference/charter.md` first**, then add its file. The check
  derives its surface from the charter, so an unregistered agent file fails and a
  registered-but-missing file fails.
