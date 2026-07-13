---
name: reboot-check
description: >
  Check whether it is safe to reboot / restart / shut down this Mac without
  losing work. Scans Supacode worktrees for uncommitted and unpushed git state
  and inspects Ghostty + Supacode terminal process trees for anything a reboot
  would kill — flagging mid-write operations (package installs, git writes,
  file copies, builds) that shouldn't be interrupted. Use whenever the user asks
  "is it safe to reboot", "can I restart my computer", "will I lose work if I
  reboot", "anything running I should worry about before restarting", "check
  before I shut down", or invokes /reboot-check. Also use before advising a
  restart to fix slowness or apply an update.
---

# Reboot safety check

Answers one question: **"If I reboot right now, will I lose work?"**

## The one fact this skill is built around

A reboot **never deletes on-disk data.** Committed history, uncommitted
working-tree changes, and saved files all survive a restart — that is what a
disk is for. A reboot only ends **running processes** and **unsaved in-memory
state.**

So this skill does **not** look for "files at risk of deletion" (there are
almost none). It surfaces the two things that actually matter before a restart:

1. **Un-backed-up work** — uncommitted / unpushed git state, so the user can
   push it first if they want it off the disk. (It survives the reboot either
   way; this is about backup, not loss.)
2. **Mid-write processes** — a package install, `git` write, `rsync`/`cp`,
   build, or system update in flight. These aren't "lost" by a reboot, but a
   hard kill mid-write can leave a half-written tree / lock / package store
   that needs cleanup. This is the only genuine "wait" case.

## How to run it

Run the bundled script and relay its report + verdict:

```bash
~/Developer/agent-skills/reboot-check/scripts/reboot-check.sh
```

It prints three sections and a verdict:

- **Supacode worktrees** — per-worktree branch, uncommitted count, unpushed
  count. All of this survives a reboot.
- **Terminal processes** — what a reboot will stop, bucketed:
  - _mid-write_ (⚠ hazard — the only reason to wait),
  - _text editors_ (⚠ may hold unsaved buffers),
  - _dev servers / watchers_ (safe to kill, will need restarting),
  - _agent / MCP sessions_ (counted; interactive, safe to kill),
  - _other_ (review).
- **Verdict** — `✅ SAFE TO REBOOT` or `⚠️ WAIT`, plus the un-backed-up
  inventory and the unsaved-editor caveat.

## Interpreting the result for the user

- **`✅ SAFE TO REBOOT`** → tell them to go ahead. Nothing on disk is lost;
  only the listed processes stop (dev servers restart with a command, agent
  sessions reopen). If the un-backed-up list is non-empty, mention it's their
  choice to push first — not required for a safe reboot.
- **`⚠️ WAIT`** → name the mid-write process and advise letting it finish or
  stopping it cleanly, then re-running the check.
- **Editors open** → remind them to save; the script can see terminal editors
  (vim/nvim/nano/…) but **cannot** see GUI editors (VS Code, Zed) — always tell
  them to eyeball open editor windows.

## Notes & limits

- macOS system **bash is 3.2** — the script is written to that (no `mapfile`).
- Supacode worktree ids are percent-encoded paths; the script decodes them with
  system `perl` (always present on macOS).
- **Ghostty has no session/list API.** The script inspects Ghostty's process
  tree instead — it can see running foreground commands but not idle tabs.
- Mid-write detection matches only the **leading program + subcommand** (first
  3 tokens), never trailing args — so an agent CLI whose prompt text contains
  words like "commit" or "install" is not mistaken for a real git/npm write.
- `supacode` must be on `PATH` for the worktree scan; if it isn't, that section
  is skipped and only the process scan runs.
