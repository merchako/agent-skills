#!/usr/bin/env bash
# Open a GitHub PR in DevinReview.
# Accepts: a bare PR number, a GitHub PR URL, or an existing devin.ai/devinreview.com URL.
set -euo pipefail

DEFAULT_REPO="paranext/paranext-core"

input="${1:-}"
if [[ -z "$input" ]]; then
  echo "usage: open-review.sh <pr-number | github-pr-url | devinreview-url>" >&2
  exit 1
fi

open_url() {
  local url="$1"
  echo "$url"
  if command -v open >/dev/null 2>&1; then
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url"
  else
    echo "(no opener found — copy the URL above)" >&2
  fi
}

# Already a Devin / DevinReview URL: open as-is.
if [[ "$input" == *"devin.ai"* || "$input" == *"devinreview.com"* ]]; then
  open_url "$input"
  exit 0
fi

owner_repo=""
pr=""

if [[ "$input" =~ github\.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
  # Full GitHub PR URL.
  owner_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  pr="${BASH_REMATCH[3]}"
elif [[ "$input" =~ ^[0-9]+$ ]]; then
  # Bare PR number — infer owner/repo from the current git remote.
  pr="$input"
  remote="$(git remote get-url origin 2>/dev/null || true)"
  if [[ "$remote" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    owner_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  else
    owner_repo="$DEFAULT_REPO"
  fi
else
  echo "error: could not parse a PR from: $input" >&2
  exit 1
fi

open_url "https://app.devin.ai/review/${owner_repo}/pull/${pr}"
