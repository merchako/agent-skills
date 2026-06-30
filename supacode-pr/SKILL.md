---
name: supacode-pr
description: >
  Open (a.k.a. "run") a GitHub pull request OR a git branch as a worktree in
  Supacode, then focus it. Accepts a bare PR number ("2467"), a "#"-prefixed
  number ("#2467"), a full GitHub PR URL
  (https://github.com/owner/repo/pull/2467), or a branch name
  ("claude/stoic-gates-eus13i", "feat/foo"). Use this whenever the user says
  things like "open this PR in supacode", "run PR #2467 in supacode", "open
  branch X in supacode", "check out this PR in supacode", "spin up <branch> in
  supacode", or invokes /supacode-pr with a number, URL, or branch — even if
  they don't say the word "worktree". Supacode has no single "open PR" command;
  this skill is the correct way to do it.
---

# Open a PR or branch in Supacode

There is no `supacode open-pr` command. In Supacode, "opening a PR or branch"
means **creating a worktree on that ref and focusing it**. This skill wraps the
whole flow — resolve repo → resolve the PR's head branch → create the worktree →
find its id → bring the app forward → focus — into one script.

## Usage

Run the bundled script with whatever the user gave you:

```bash
~/Developer/agent-skills/supacode-pr/scripts/open-in-supacode.sh "<input>" [--repo <path|owner/repo>]
```

Examples:

```bash
# PR by URL (owner/repo is read from the URL and matched to a local checkout)
~/Developer/agent-skills/supacode-pr/scripts/open-in-supacode.sh \
  "https://github.com/paranext/paranext-core/pull/2467"

# Bare PR number — run from inside the checkout, or pass --repo
~/Developer/agent-skills/supacode-pr/scripts/open-in-supacode.sh 2467 --repo paranext/paranext-core

# A branch name
~/Developer/agent-skills/supacode-pr/scripts/open-in-supacode.sh claude/stoic-gates-eus13i \
  --repo /Users/merc/Developer/paranext/core
```

The script prints the PR URL (if any), the branch + base, and the new worktree
path, then opens and focuses it. Relay that summary back to the user.

## How it resolves things (so you can debug failures)

- **Which local repo.** In priority order: `--repo` (a path is used directly; an
  `owner/repo` is matched against each registered repo's `origin`) → the
  owner/repo embedded in a PR URL → `$SUPACODE_REPO_ID` → the current directory's
  git root. Supacode must already know that repo; if not, the script tells you to
  run `supacode repo open <path>` first. List known repos with `supacode repo list`.
- **PR → branch.** Uses `gh pr view` to get `headRefName`. For a **fork PR**
  (`isCrossRepository`), the head branch isn't on `origin`, so it fetches
  `pull/<n>/head` into a local `pr-<n>` branch and builds the worktree from that.
- **Branch → base.** Prefers the branch on `origin`; falls back to an existing
  local branch; otherwise creates a new branch off the repo's default base.
- **Already open → reuse.** Before creating, the script checks whether the
  target branch is already checked out in a Supacode worktree (via
  `git worktree list`, mapping the path to a Supacode id). If so it just focuses
  that worktree instead of creating a duplicate — so re-running is safe and idempotent.
- **Finding the new worktree.** `supacode repo worktree-new` doesn't print the
  new id, so the script snapshots `supacode worktree list` before and after and
  diffs. `focus` can time out while the worktree initializes, so it retries.

## When it can't auto-detect / errors

- "Supacode doesn't know repo …" → `supacode repo open '<path>'`, then rerun.
- Re-opening a PR/branch that's already open just re-focuses it (see reuse above) —
  no error, no duplicate.
- Needs `gh` (for PRs) and `jq` on PATH. `gh` must be authed for private repos.

## Doing it by hand (no script)

```bash
gh pr view <N> --repo <owner/repo> --json headRefName,baseRefName,isCrossRepository,url
supacode repo list                 # find the percent-encoded repo id
supacode repo worktree-new -r "<repo-id>" --branch "<headRefName>" \
  --base "origin/<headRefName>" --fetch
supacode worktree list             # diff to find the new id (the new folder)
supacode open
supacode worktree focus -w "<new-worktree-id>"
```

For lower-level Supacode operations (tabs, surfaces, running scripts in a
worktree), see the separate `supacode-cli` skill.
