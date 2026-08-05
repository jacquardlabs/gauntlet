---
description: Run a changeset through the gauntlet — dispatch the judges whose lanes it touches, compile their findings, and optionally post them to a PR.
allowed-tools: Bash, Read, Glob, Grep, Task
---

# Run the gauntlet

A consumer, not a methodology (`PRODUCT.md`, "Consumers are thin"). You select the
judges that apply, dispatch them, compile what they return, and show it. **You never
decide what happens next** — no verdict of your own, no gate, no ledger, no follow-on
door. Every side effect is one the human confirms in this same invocation.

`$ARGUMENTS` may name a PR (number or URL). Empty means the current branch.

## 1. Resolve the artifact

**No arguments** — diff the current branch against its merge-base:

```bash
BASE=$(git merge-base HEAD "$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)")
HEAD=$(git rev-parse HEAD)
```

**A PR was named** — resolve it to the same two shas, and keep the URL:

```bash
gh pr view <n> --json baseRefOid,headRefOid,url,files
```

Use `baseRefOid` as `base` and `headRefOid` as `head`. If `gh` fails (wrong account, no
remote), say so and stop — do not silently fall back to the local branch, which would
judge a different artifact than the one asked for.

**Then read the PR's tree from a worktree — never `gh pr checkout`.**

```bash
git fetch origin pull/<n>/head
git worktree add --detach <tmp>/tree <head-sha>
```

Two reasons, and the second is not politeness. `gh pr checkout` switches the human's
working tree and refuses outright when they have conflicting local changes — on this
tool's first real run, the target repo was mid-work on another branch. And a judge must
read the tree it is judging: the code lane's idiom linter runs against the working
directory, so reviewing a PR whose head was never checked out lints code that is not
under review.

Pass the worktree as `--root` to the dispatcher, so every judge's `artifact.root` points
at it. Remove it when you are done (`git worktree remove --force <tmp>/tree`), even if
the run failed.

Get the changed paths (`git diff --name-only $BASE..$HEAD`, or the PR's `files`). Report
the artifact and the file count before dispatching anything, and say which tree the
judges are reading.

## 2. Build the invocations

Selection, the standard mapping, and validation all live in code — a prompt cannot call
a validator, and the contract requires the invocation be validated where it crosses the
boundary:

```bash
git diff --name-only $BASE..$HEAD > <tmp>/paths.txt
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py" \
  --base $BASE --head $HEAD ${PR:+--pr $PR} \
  --paths <tmp>/paths.txt \
  --context "CLAUDE.md,DESIGN.md,PRODUCT.md" > <tmp>/invocations.json
```

Pass `--context` only the files that exist, and `--receipts-path` only when the human
named an evidence log — never invent one. The script reads the charter roster, drops a
lane whose path signals nothing in the changeset matches, resolves each Standard cell
into a citable `standard` (an `(inline)` judge gets its own name plus the plugin
version, never the literal shorthand), and rejects a malformed invocation before it
reaches a judge.

**Report which judges it selected, and which lanes it dropped**, before dispatching. An
unrun lane the human does not know about reads as a clean one. Selection is a cost
decision, not a judgment: every judge self-skips when its lane does not apply, so a
wrong guess wastes a dispatch and never a verdict.

## 3. Dispatch

Dispatch every invocation **in parallel**, one `Task` call each, in a single message.
Give each judge its own invocation object from `invocations.json` verbatim, and tell it
its entire reply must be the findings document, one JSON object and nothing else.

Write each reply verbatim to `<tmp>/findings/<judge>.json`.

**A judge that returns something unparseable is a lane that did not report.** Keep the
file as it came back. Do not repair it, re-ask for it, or drop it — a lane silently
missing from a report is the one failure mode this whole repo exists to prevent, and the
compiler is built to say so out loud.

## 4. Compile

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" \
  --findings <tmp>/findings \
  --expect "$(python3 -c 'import json,sys; print(",".join(i["judge"] for i in json.load(open(sys.argv[1]))))' <tmp>/invocations.json)"
```

`--expect` is what lets the compiler see a judge that died before writing anything:
without it, absence is indistinguishable from a lane with no findings.

It validates every document at the boundary, applies the ingest rules (anchor-or-demote,
taste-caps-at-track) and names what it changed, checks the documents agree about which
artifact they judged, orders findings most-severe-first, and renders. A non-zero exit
means at least one lane did not report — pass that on; it is not a failure of the run to
hide.

Show the report. **Do not summarize it into a verdict of your own** — "3 critical, 2
important" is the tally the compiler already printed; whether that ships is the human's
call, and stating it as one would make this a gate.

## 5. Post to the PR — only if a PR was named, and only on confirmation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" --findings <tmp>/findings \
  --format pr-comments > <tmp>/review.json
```

`report.py` splits the findings itself: those whose locus lands on a line the diff
actually contains become `comments[]`, and the rest ride in `summary`, most severe first.
That split is not cosmetic — **the reviews API rejects the entire review if any one
comment names a line outside the diff**, so an unfiltered payload loses every finding
rather than one. Expect the un-anchorable set to hold your best findings: "you changed X
and never updated Y" is inherently about lines that did not change.

Show the human how many comments would post and to which files, name how many are riding
in the summary instead, then ask. `gh pr review` cannot post per-file comments — it has
no such flag — so on an explicit yes, post through the reviews API, which takes the
emitted shape directly:

```bash
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); json.dump({"event":"COMMENT","body":d["summary"],"comments":d["comments"]}, sys.stdout)' <tmp>/review.json \
  | gh api "repos/$OWNER/$REPO/pulls/$NUMBER/reviews" --input -
```

Anything other than an explicit yes: stop, and leave the report on screen.

**Never approve or request changes on the PR.** Comments only. A verdict is derived by
the human from open findings, never posted by a consumer — that is the no-verdict rule in
`docs/findings-contract.md` §4, and posting an approval would launder a tally into a
judgment nobody made.

Clean up the scratch directory when you are done, unless the human asked to keep it.
