#!/usr/bin/env bash
# Open a GitHub PR or a branch as a Supacode worktree, then focus it.
#
# Accepts as the positional argument:
#   - a bare PR number            42
#   - a "#"-prefixed PR number    #42
#   - a GitHub PR URL             https://github.com/owner/repo/pull/42[/anything]
#   - a branch name               feat/foo  or  claude/stoic-gates-eus13i
#
# Options:
#   --repo <path|owner/repo>  Disambiguate which local Supacode repo to use.
#                             A path is used directly; an owner/repo is matched
#                             against each registered repo's origin remote.
#   --pr                      Force PR mode (treat the input as a PR number).
#   --branch                  Force branch mode (treat a numeric input as a branch).
#
# Why a script: "open a PR in Supacode" isn't one CLI command. It is
# resolve-repo -> resolve-branch-from-PR -> create worktree -> discover the new
# worktree's id (worktree-new doesn't print it) -> bring app forward -> focus
# (which can time out while the worktree spins up). Doing this by hand is fiddly
# and easy to get wrong; the script makes it one call.
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

command -v supacode >/dev/null 2>&1 || die "supacode CLI not found (run this where the Supacode CLI is on PATH)"

# ---- parse args ---------------------------------------------------------
input="" repo_opt="" force_pr="" force_branch="" dry_run=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)    repo_opt="${2:-}"; shift 2 ;;
    --pr)      force_pr=1; shift ;;
    --branch)  force_branch=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) [[ -z "$input" ]] && input="$1" || die "unexpected argument: $1"; shift ;;
  esac
done
[[ -n "$input" ]] || die "usage: open-in-supacode.sh <pr-number | pr-url | branch> [--repo <path|owner/repo>] [--pr|--branch]"

# ---- percent-decode helper (Supacode repo/worktree ids are encoded paths) ----
decode() { printf '%b' "${1//%/\\x}"; }

# strip ANSI (the focused worktree is printed underlined) and blank lines
list_worktrees() { supacode worktree list 2>/dev/null | sed $'s/\x1b\\[[0-9;]*m//g' | sed '/^$/d'; }

# ---- classify input -----------------------------------------------------
owner_repo="" pr="" branch="" mode=""
if [[ -z "$force_branch" && "$input" =~ github\.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
  owner_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"; pr="${BASH_REMATCH[3]}"; mode="pr"
elif [[ -z "$force_branch" && ( -n "$force_pr" || "$input" =~ ^#?[0-9]+$ ) ]]; then
  pr="${input#\#}"; mode="pr"
else
  branch="$input"; mode="branch"
fi

# ---- resolve the local repo path ----------------------------------------
# We need (a) the filesystem path for git/gh -C and (b) the exact encoded repo
# id that `supacode repo worktree-new -r` expects. We get the id by decoding the
# entries of `supacode repo list` and matching the decoded path, so we never
# have to reproduce Supacode's encoding ourselves.
repo_path="" repo_id=""

resolve_id_from_path() {  # $1 = filesystem path -> sets repo_id if Supacode knows it
  local want; want="$(cd "$1" 2>/dev/null && pwd -P)" || return 1
  local enc dec
  while IFS= read -r enc; do
    [[ -n "$enc" ]] || continue
    dec="$(decode "$enc")"; dec="${dec%/}"
    [[ "$dec" == "$want" ]] && { repo_id="$enc"; return 0; }
  done < <(supacode repo list 2>/dev/null)
  return 1
}

lc() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }  # bash 3.2 (macOS) has no ${x,,}

match_owner_repo() {  # $1 = owner/repo -> sets repo_path+repo_id from a registered repo's origin
  local want enc dec url norm
  want="$(lc "$1")"
  while IFS= read -r enc; do
    [[ -n "$enc" ]] || continue
    dec="$(decode "$enc")"; dec="${dec%/}"
    url="$(git -C "$dec" remote get-url origin 2>/dev/null || true)"
    [[ "$url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?/?$ ]] || continue
    norm="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    [[ "$(lc "$norm")" == "$want" ]] && { repo_path="$dec"; repo_id="$enc"; return 0; }
  done < <(supacode repo list 2>/dev/null)
  return 1
}

if [[ -n "$repo_opt" ]]; then
  if [[ -d "$repo_opt" ]]; then
    repo_path="$(cd "$repo_opt" && pwd -P)"
    resolve_id_from_path "$repo_path" || die "Supacode doesn't know repo at $repo_path — open it first: supacode repo open '$repo_path'"
  else
    match_owner_repo "$repo_opt" || die "no registered Supacode repo whose origin is $repo_opt (see: supacode repo list)"
  fi
elif [[ -n "$owner_repo" ]] && match_owner_repo "$owner_repo"; then
  :  # matched the PR-URL's owner/repo to a local checkout
elif [[ -n "${SUPACODE_REPO_ID:-}" ]]; then
  repo_id="$SUPACODE_REPO_ID"; repo_path="$(decode "$repo_id")"; repo_path="${repo_path%/}"
else
  top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "$top" ]] || die "couldn't determine the repo — run from inside the checkout or pass --repo <path|owner/repo>"
  repo_path="$top"
  resolve_id_from_path "$repo_path" || die "Supacode doesn't know repo at $repo_path — open it first: supacode repo open '$repo_path'"
fi
[[ -n "$repo_id" && -n "$repo_path" ]] || die "could not resolve a Supacode repo for: $input"

# For a bare PR number we still need owner/repo for gh; derive from the checkout.
if [[ "$mode" == "pr" && -z "$owner_repo" ]]; then
  url="$(git -C "$repo_path" remote get-url origin 2>/dev/null || true)"
  [[ "$url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?/?$ ]] \
    && owner_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}" \
    || die "couldn't infer owner/repo for PR #$pr from $repo_path"
fi

# ---- resolve branch + base ----------------------------------------------
base="" pr_url=""
if [[ "$mode" == "pr" ]]; then
  command -v gh >/dev/null 2>&1 || die "gh CLI not found (needed to resolve PR #$pr)"
  meta="$(gh pr view "$pr" --repo "$owner_repo" \
            --json headRefName,baseRefName,isCrossRepository,url 2>/dev/null)" \
    || die "gh couldn't read PR #$pr in $owner_repo"
  branch="$(jq -r .headRefName <<<"$meta")"
  pr_url="$(jq -r .url <<<"$meta")"
  cross="$(jq -r .isCrossRepository <<<"$meta")"
  if [[ "$cross" == "true" ]]; then
    # Fork PR: the head branch isn't on origin. Fetch the PR head into a local
    # branch and build the worktree from that.
    branch="pr-$pr"
    echo "PR #$pr is from a fork — fetching pull/$pr/head into $branch" >&2
    git -C "$repo_path" fetch origin "pull/$pr/head:$branch" >&2 || die "failed to fetch pull/$pr/head"
    base="$branch"
  else
    base="origin/$branch"
  fi
else
  # Branch mode: prefer the remote branch; else an existing local branch; else
  # treat as a new branch off the repo's default base.
  git -C "$repo_path" fetch origin >&2 2>/dev/null || true
  if git -C "$repo_path" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    base="origin/$branch"
  elif git -C "$repo_path" show-ref --verify --quiet "refs/heads/$branch"; then
    base="$branch"
  else
    def="$(git -C "$repo_path" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null || true)"
    base="${def#refs/remotes/}"; base="${base:-origin/main}"
    echo "branch '$branch' not found on origin — creating it off $base" >&2
  fi
fi

if [[ -n "$dry_run" ]]; then
  echo "--- dry run (nothing created) ---"
  [[ -n "$pr_url" ]] && echo "PR:       $pr_url"
  echo "repo:     $repo_path"
  echo "repo-id:  $repo_id"
  echo "branch:   $branch   (base: $base)"
  echo "would run: supacode repo worktree-new -r '$repo_id' --branch '$branch' --base '$base' --fetch"
  exit 0
fi

# ---- create the worktree, discovering the new id by diffing the list -----
before="$(list_worktrees | sort)"
echo "+ supacode repo worktree-new -r <$repo_path> --branch $branch --base $base --fetch" >&2
supacode repo worktree-new -r "$repo_id" --branch "$branch" --base "$base" --fetch \
  || die "supacode repo worktree-new failed (a worktree for '$branch' may already exist — check: supacode worktree list)"
after="$(list_worktrees | sort)"

new_id="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | head -1)"

# ---- bring Supacode forward and focus the new worktree -------------------
supacode open >/dev/null 2>&1 || true
if [[ -n "$new_id" ]]; then
  for attempt in 1 2 3 4; do
    if supacode worktree focus -w "$new_id" >/dev/null 2>&1; then break; fi
    sleep 3   # the worktree may still be initializing (install scripts, etc.)
  done
fi

# ---- report -------------------------------------------------------------
echo "---"
[[ -n "$pr_url" ]] && echo "PR:       $pr_url"
echo "branch:   $branch   (base: $base)"
if [[ -n "$new_id" ]]; then
  echo "worktree: $(decode "$new_id")"
  echo "opened and focused in Supacode."
else
  echo "worktree created, but its id couldn't be auto-detected (it may have already existed)."
  echo "find and focus it with: supacode worktree list"
fi
