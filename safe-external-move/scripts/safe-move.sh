#!/bin/zsh
# safe-move.sh — copy-verify-delete migration of one or more folders to an
# external (or any secondary) volume, resilient to the drive disconnecting
# mid-run and safe to re-run after any interruption.
#
# Usage:
#   safe-move.sh [--log LOGFILE] SRC1 DST1 [SRC2 DST2 ...]
#
# Each SRC/DST pair is handled fully (copy, verify, delete) before moving to
# the next pair. DST is the exact destination folder path — the caller decides
# naming (e.g. matching an existing "<Label> <YYYYMMDD>" convention on the
# destination volume).
#
# Guarantees:
#   - Copy uses `rsync -a --partial`, so an interrupted copy resumes instead
#     of restarting from zero.
#   - Nothing is deleted from SRC until a checksum-based dry-run diff
#     (`rsync -avnc --delete`) shows zero real differences — i.e. every byte
#     has been verified to match on both sides.
#   - If DST's volume disappears (drive unplugged) at any point, the script
#     pauses and polls every 30s rather than aborting; it self-resumes once
#     the volume is reconnected.
#   - Every phase is logged with a timestamp. A pair already marked DELETED
#     in the log is skipped on re-run, so killing and re-launching this
#     script is always safe.

set -uo pipefail
emulate -L zsh

LOG=""
typeset -a ARGS
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --log)
      LOG="$2"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [ $(( ${#ARGS[@]} % 2 )) -ne 0 ] || [ ${#ARGS[@]} -eq 0 ]; then
  print -u2 "Usage: $0 [--log LOGFILE] SRC1 DST1 [SRC2 DST2 ...]"
  exit 2
fi

if [ -z "$LOG" ]; then
  LOG="./safe-move-$(date '+%Y%m%d-%H%M%S').log.md"
fi

typeset -a SRCS DSTS
n=${#ARGS[@]}
i=1
while [ $i -le $n ]; do
  SRCS+=("${ARGS[$i]}")
  DSTS+=("${ARGS[$((i+1))]}")
  i=$((i+2))
done

log() { print -- "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG" }

# Deepest existing ancestor of a path — used to detect the destination
# volume/mount disappearing (e.g. drive unplugged) even for a DST that
# doesn't exist yet.
existing_ancestor() {
  local p="$1"
  while [ ! -d "$p" ] && [ "$p" != "/" ]; do
    p="$(dirname "$p")"
  done
  print -- "$p"
}

log ""
log "########## SAFE-MOVE RUN START ##########"

for idx in {1..${#SRCS[@]}}; do
  src="${SRCS[$idx]}"
  dst="${DSTS[$idx]}"
  dest_anchor="$(existing_ancestor "$(dirname "$dst")")"

  if grep -qF "DELETED: '$src' -> '$dst'" "$LOG" 2>/dev/null; then
    log "SKIP (already completed): '$src' -> '$dst'"
    continue
  fi

  if [ ! -d "$src" ]; then
    log "SKIP (source does not exist, presumably already migrated): '$src'"
    continue
  fi

  log "=== Item $idx: '$src' -> '$dst' ==="

  while [ ! -d "$dest_anchor" ]; do
    log "WAITING: '$dest_anchor' not reachable (drive disconnected?). Rechecking in 30s..."
    sleep 30
  done

  presz_h=$(du -sh "$src" 2>/dev/null | cut -f1)
  presz_k=$(du -sk "$src" 2>/dev/null | cut -f1)
  precnt=$(find "$src" -type f 2>/dev/null | wc -l | tr -d ' ')
  log "Pre-copy manifest: size=$presz_h files=$precnt"

  avail_k=$(df -k "$dest_anchor" 2>/dev/null | tail -1 | awk '{print $4}')
  if [ -n "$avail_k" ] && [ -n "$presz_k" ] && [ "$presz_k" -gt "$avail_k" ]; then
    log "ABORT: not enough free space at '$dest_anchor' (need ~${presz_k}KB, have ${avail_k}KB). Leaving source intact."
    continue
  fi

  mkdir -p "$dst"

  attempt=1
  while true; do
    log "rsync copy attempt $attempt..."
    rsync -a --partial "$src"/ "$dst"/ >> "$LOG" 2>&1
    rc=$?
    if [ $rc -eq 0 ]; then
      log "rsync copy finished cleanly (attempt $attempt)."
      break
    fi
    log "rsync exited with code $rc (attempt $attempt)."
    while [ ! -d "$dest_anchor" ]; do
      log "WAITING: destination disconnected mid-copy. Rechecking in 30s..."
      sleep 30
    done
    attempt=$((attempt+1))
    if [ $attempt -gt 50 ]; then
      log "ABORT: too many failed rsync attempts for '$src'. Leaving source intact. Manual review needed."
      break 2
    fi
    sleep 15
  done

  log "Verifying with checksum dry-run comparison (reads every byte on both sides)..."
  diffout=$(rsync -avnc --delete "$src"/ "$dst"/ 2>&1)
  realdiff=$(print -- "$diffout" | grep -vE '^(sending incremental file list|sent .* bytes|total size is|$)')

  if [ -z "$realdiff" ]; then
    postcnt=$(find "$dst" -type f 2>/dev/null | wc -l | tr -d ' ')
    log "VERIFIED: byte-for-byte match. dest files=$postcnt (src had $precnt)."
    rm -rf "$src"
    log "DELETED: '$src' -> '$dst' (source removed, copy verified at destination)"
  else
    log "VERIFICATION FAILED for '$src'. Differences found:"
    log "$realdiff"
    log "NOT deleting source. Manual review required."
  fi
done

log "########## SAFE-MOVE RUN END ##########"
