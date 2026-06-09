---
name: devinreview
description: >
  Open a GitHub pull request in DevinReview (Devin's AI code-review UI). Accepts a bare
  PR number (e.g. "2357"), a GitHub PR URL (e.g. https://github.com/paranext/paranext-core/pull/2357/changes),
  or an existing devin.ai/devinreview.com URL, and opens the corresponding DevinReview page in the browser.
  Use when the user says "open this PR in devinreview", "review #2357 in devin", "devinreview <url>",
  or invokes /devinreview with a PR number or link.
---

# DevinReview Skill

Open a GitHub PR in DevinReview. The script parses whatever the user gives you and opens the right URL.

## Usage

Run the bundled script with the user's input (PR number, GitHub URL, or DevinReview URL):

```bash
~/Developer/agent-skills/devinreview/open-review.sh "<input>"
```

Examples:

```bash
# Bare PR number — owner/repo inferred from the current git remote (falls back to paranext/paranext-core)
~/Developer/agent-skills/devinreview/open-review.sh 2357

# GitHub PR URL (any trailing path like /changes, /files is fine)
~/Developer/agent-skills/devinreview/open-review.sh "https://github.com/paranext/paranext-core/pull/2357/changes"

# Already a Devin/DevinReview URL — opened as-is
~/Developer/agent-skills/devinreview/open-review.sh "https://app.devin.ai/review/paranext/paranext-core/pull/2357"
```

## URL mapping

| Input                                                          | Opens                                                                |
| -------------------------------------------------------------- | -------------------------------------------------------------------- |
| `2357`                                                         | `https://app.devin.ai/review/<owner>/<repo>/pull/2357`               |
| `https://github.com/<owner>/<repo>/pull/2357/changes`          | `https://app.devin.ai/review/<owner>/<repo>/pull/2357`               |

`app.devin.ai/review/...` and `devinreview.com/.../changes` are equivalent; the script
emits the `app.devin.ai` form and prints the URL before opening it.

## Notes

- A bare number resolves `<owner>/<repo>` from the `origin` remote of the current directory. If there's no git remote, it defaults to `paranext/paranext-core`.
- The script prints the resolved URL to stdout, then opens it with `open` (macOS). Report the opened URL back to the user.
- If the input can't be parsed into a PR, the script exits non-zero with an error — relay that to the user.
