#!/usr/bin/env bash
#
# reboot-check.sh — Is it safe to reboot this Mac right now?
#
# Scans two sources and prints an inventory + a verdict:
#   1. Supacode worktrees        → uncommitted / unpushed git state
#   2. Ghostty + Supacode PTYs   → processes a reboot would kill,
#                                  flagging any doing a mid-write operation
#                                  (package install, git write, copy, build…)
#
# GUIDING PRINCIPLE (read this before trusting the verdict):
#   A reboot NEVER deletes on-disk data. Committed history, uncommitted
#   working-tree changes, and saved files all survive a restart — that is
#   what a disk is for. A reboot only ends RUNNING PROCESSES and UNSAVED
#   IN-MEMORY state. So this script does NOT hunt for "work at risk of
#   deletion" (there is almost none). It answers two narrower questions:
#     (a) What un-backed-up work exists, so you can push it first if you want?
#     (b) Is any process mid-write, where a hard kill could leave a
#         half-written tree that needs cleanup afterward?
#
# It CANNOT see unsaved editor buffers — always eyeball open editors yourself.
#
# Compatible with macOS system bash 3.2 (no mapfile / associative arrays).

set -uo pipefail

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Decode a percent-encoded path (Supacode worktree ids). System perl is on
# every macOS; avoids a python3 / CLT dependency.
decode() { printf '%s' "$1" | perl -pe 's/%([0-9A-Fa-f]{2})/chr hex $1/ge'; }

# Untracked files that are throwaway and never worth preserving.
NOISE_RE='(^|/)(shot\.mjs|\.DS_Store|npm-debug\.log|\.env\.local)$'

# Commands that are HAZARDOUS to kill mid-flight — a hard reboot can leave a
# half-written tree / lock / package store. Matched against full arg strings.
DANGER_RE='npm (install|ci|i$|i )|yarn( install|$| add)|pnpm|corepack|git (rebase|merge|commit|push|pull|fetch|clone|checkout|reset|gc|repack|filter)|(^| )rsync( |$)|(^| )dd( |$)|/bin/cp|/bin/mv|softwareupdate|brew (install|upgrade|update|reinstall|link)|xcodebuild|cargo (build|test|install|publish)|(^| )make( |$)|prisma (migrate|db)|docker (build|pull|push)|pip[3]? (install|download)|(^| )apt|dpkg|mysqldump|pg_dump|pg_restore'

# Long-running dev servers / watchers: safe to kill, but worth listing so the
# user knows they will stop and need restarting.
DEVSERVER_RE='vite|next dev|next-server|nodemon|storybook|webpack.*serve|webpack-dev-server|(^| )serve( |$)|http-server|watchman|--watch|vitest|ng serve|astro dev|remix (dev|vite)|turbo (dev|watch)|electron .*dev|esbuild --serv'

# Interactive agent CLIs. Their argv is a free-text PROMPT, so it must NEVER be
# fed to DANGER_RE (a prompt saying "commit" or "make" would false-positive).
# These are REPL-ish sessions holding no un-flushed disk write — safe to kill.
AGENT_RE='(^|/)(claude|codex|aider|goose|cursor-agent|copilot|ollama)( |$)'
MCP_RE='[Mm][Cc][Pp]Bridge|[Mm][Cc][Pp]-server|(^|/)mcp[_-]'

# Terminal text editors: safe to kill, EXCEPT they may hold unsaved buffers.
EDITOR_RE='(^|/)(vim|nvim|vi|emacs|emacsclient|nano|pico|hx|helix|micro|kak|joe)( |$)'

# Transient helpers spawned by this very script / shell — don't report them.
NOISE_PROC_RE='reboot-check\.sh|(^|/)(ps|awk|perl|grep|egrep|sed|wc|sort|uniq|head|tail|cat|tr|basename|dirname|env|sleep|xargs|tee)( |$)'

PS_SNAPSHOT="$(mktemp -t rebootchk.XXXXXX)"
trap 'rm -f "$PS_SNAPSHOT"' EXIT
ps -axo pid=,ppid=,command= > "$PS_SNAPSHOT"

# echo the pids of all descendants of $1 (recursive), using the snapshot.
descendants() {
  local parent="$1" kid
  for kid in $(awk -v p="$parent" '$2==p {print $1}' "$PS_SNAPSHOT"); do
    echo "$kid"
    descendants "$kid"
  done
}

# full command string for a pid, from the snapshot
cmd_of() { awk -v p="$1" '$1==p {sub(/^[ ]*[0-9]+[ ]+[0-9]+[ ]+/,""); print; exit}' "$PS_SNAPSHOT"; }

# ---------------------------------------------------------------------------
# 1. Supacode worktrees — durable git state
# ---------------------------------------------------------------------------
echo "════════════════════════════════════════════════════════════════"
echo " REBOOT SAFETY REPORT"
echo "════════════════════════════════════════════════════════════════"
echo
echo "## Supacode worktrees — git state (all of this SURVIVES a reboot)"
echo

DIRTY_LIST=""
UNPUSHED_LIST=""

if command -v supacode >/dev/null 2>&1; then
  printf "  %-46s %-38s %6s %9s\n" "WORKTREE" "BRANCH" "DIRTY" "UNPUSHED"
  printf "  %-46s %-38s %6s %9s\n" "--------" "------" "-----" "--------"
  while IFS= read -r enc; do
    [ -z "$enc" ] && continue
    p="$(decode "$enc")"
    git -C "$p" rev-parse --is-inside-work-tree >/dev/null 2>&1 || continue

    br="$(git -C "$p" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    [ "$br" = "HEAD" ] && br="(detached)"

    dirty="$(git -C "$p" status --porcelain 2>/dev/null | grep -Ev "$NOISE_RE" | grep -c . | tr -d ' ')"

    if [ -n "$(git -C "$p" remote 2>/dev/null)" ]; then
      unpushed="$(git -C "$p" rev-list --count HEAD --not --remotes 2>/dev/null || echo 0)"
    else
      unpushed="no-remote"
    fi

    name="$(basename "$p")"
    printf "  %-46s %-38s %6s %9s\n" "${name:0:46}" "${br:0:38}" "$dirty" "$unpushed"

    [ "$dirty" != "0" ] && DIRTY_LIST="$DIRTY_LIST$name ($dirty)\n"
    case "$unpushed" in
      0|no-remote) ;;
      *) UNPUSHED_LIST="$UNPUSHED_LIST$name ($unpushed)\n" ;;
    esac
  done < <(supacode worktree list 2>/dev/null | sort -u)
else
  echo "  supacode CLI not on PATH — skipping worktree scan."
fi

# ---------------------------------------------------------------------------
# 2. Terminal processes — what a reboot will KILL
# ---------------------------------------------------------------------------
echo
echo "## Terminal processes — these STOP on reboot"
echo

# root app pids (Ghostty, Supacode). match on command, drop grep itself.
ROOTS="$(grep -Ei 'ghostty|supacode' "$PS_SNAPSHOT" \
          | grep -Eiv "$NOISE_PROC_RE" \
          | awk '{print $1}')"

if grep -Eqi 'ghostty' "$PS_SNAPSHOT"; then GHOSTTY_UP="yes"; else GHOSTTY_UP="no"; fi

HAZARD_LIST=""
DEVSERVER_LIST=""
EDITOR_LIST=""
OTHER_LIST=""
AGENT_COUNT=0
MCP_COUNT=0
SEEN=" "

for root in $ROOTS; do
  for pid in $(descendants "$root"); do
    case "$SEEN" in *" $pid "*) continue ;; esac
    SEEN="$SEEN$pid "
    c="$(cmd_of "$pid")"
    [ -z "$c" ] && continue
    # skip shells, the app binaries themselves, and our own helper noise
    echo "$c" | grep -Eqi "$NOISE_PROC_RE" && continue
    echo "$c" | grep -Eqi '(^|/)(-?zsh|-?bash|-?fish|-?sh|-?dash|login)( |$)' && continue
    echo "$c" | grep -Eqi 'ghostty|Supacode|Electron|Helper \(' && continue

    # Agent CLIs & MCP helpers FIRST — before DANGER_RE ever sees their argv,
    # because their args are free-text prompts that would false-positive.
    if echo "$c" | grep -Eqi "$AGENT_RE"; then AGENT_COUNT=$((AGENT_COUNT+1)); continue; fi
    if echo "$c" | grep -Eqi "$MCP_RE";   then MCP_COUNT=$((MCP_COUNT+1));     continue; fi
    if echo "$c" | grep -Eqi "$EDITOR_RE"; then EDITOR_LIST="$EDITOR_LIST  [$pid] ${c:0:100}\n"; continue; fi
    if echo "$c" | grep -Eqi "$DEVSERVER_RE"; then DEVSERVER_LIST="$DEVSERVER_LIST  [$pid] ${c:0:100}\n"; continue; fi

    # DANGER check runs against only the first 3 tokens (program + subcommand),
    # never trailing free-text args.
    head3="$(echo "$c" | awk '{print $1, $2, $3}')"
    if echo "$head3" | grep -Eqi "$DANGER_RE"; then
      HAZARD_LIST="$HAZARD_LIST  [$pid] $c\n"
    else
      OTHER_LIST="$OTHER_LIST  [$pid] ${c:0:100}\n"
    fi
  done
done

if [ "$GHOSTTY_UP" = "yes" ]; then
  echo "  Ghostty: running (no session API — inspected its process tree)"
else
  echo "  Ghostty: not running (or no inspectable process)"
fi
if [ "$AGENT_COUNT" -gt 0 ] || [ "$MCP_COUNT" -gt 0 ]; then
  echo "  Agent sessions: $AGENT_COUNT Claude/agent CLI + $MCP_COUNT MCP helper(s) — interactive, safe to kill."
fi
echo

if [ -n "$HAZARD_LIST" ]; then
  echo "  ⚠️  MID-WRITE processes (killing these can leave a half-written state):"
  printf "$HAZARD_LIST"
  echo
fi
if [ -n "$EDITOR_LIST" ]; then
  echo "  ⚠️  Text editors open (may hold UNSAVED buffers — save before reboot):"
  printf "$EDITOR_LIST"
  echo
fi
if [ -n "$DEVSERVER_LIST" ]; then
  echo "  Dev servers / watchers (safe to kill — will need restarting):"
  printf "$DEVSERVER_LIST"
  echo
fi
if [ -n "$OTHER_LIST" ]; then
  echo "  Other foreground processes (review — usually safe):"
  printf "$OTHER_LIST"
  echo
fi
if [ -z "$HAZARD_LIST$EDITOR_LIST$DEVSERVER_LIST$OTHER_LIST" ]; then
  echo "  No active foreground work found in terminals — only idle shells."
  echo
fi

# ---------------------------------------------------------------------------
# 3. Verdict
# ---------------------------------------------------------------------------
echo "════════════════════════════════════════════════════════════════"
echo " VERDICT"
echo "════════════════════════════════════════════════════════════════"
if [ -n "$HAZARD_LIST" ]; then
  echo " ⚠️  WAIT — a mid-write process is running (see above). Let it finish"
  echo "     or stop it cleanly before rebooting, then re-run this check."
else
  echo " ✅ SAFE TO REBOOT — no mid-write process running."
  echo "    Nothing on disk is lost by a restart; only the processes above stop."
fi
echo
if [ -n "$DIRTY_LIST" ] || [ -n "$UNPUSHED_LIST" ]; then
  echo " Not backed up to a remote (survives reboot, but push first if you"
  echo " want it off this disk):"
  [ -n "$DIRTY_LIST" ]    && { echo "   uncommitted:"; printf "$DIRTY_LIST" | sed 's/^/     /'; }
  [ -n "$UNPUSHED_LIST" ] && { echo "   unpushed commits:"; printf "$UNPUSHED_LIST" | sed 's/^/     /'; }
  echo
fi
echo " Can't inspect: unsaved buffers in GUI editors (VS Code, Zed, etc.).
 Glance at any open editor windows before rebooting."
