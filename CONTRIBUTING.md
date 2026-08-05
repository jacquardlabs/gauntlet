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
| **Status checks required** | **pending — see below** | **The deliberate difference.** studious and viva have branch protection but do not require checks, so a red PR is mergeable there. Here the checks *are* the product's own discipline; a fleet whose independence check is advisory is a fleet with no independence check. |

### Branch protection is not applied yet

GitHub refuses branch protection on a **private** repo outside a paid plan, and
`jacquardlabs` is a personal account: studious and viva have protection only because
they are public. So this table describes the intended state, and the rows above the
divider are applied while protection itself is not. Two ways to close it — make this
repo public (free, matches the siblings, and is where #6 is headed anyway) or pay for
Pro.

Required contexts, once it can be applied — matching the CI job names exactly, because
renaming a job without updating the protection leaves a context that never reports and
wedges every PR:

- `unit tests (Python 3.9)` … `unit tests (Python 3.14)` — one per matrix leg, six today
- `judge independence`
- `ruff + version floor`

The matrix is contiguous from the floor to the current release, not a sample of the
ends: a stdlib removal can land in a middle version, and a leg costs ~15s. Adding a
Python version therefore adds a required context — update the protection in the same
change.

Alongside them: strict (branches up to date), no force push, no deletion, PR required
at 0 approvals, conversation resolution required.

## Local checks

The full CI suite, all stdlib except the linters:

```bash
for t in tests/test_*.py; do python3 "$t"; done
python3 scripts/check_independence.py
python3 scripts/validate_plugin.py
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
