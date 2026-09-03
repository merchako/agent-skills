---
name: safe-external-move
description: >
  Safely move (not copy) large folders from local disk to an external drive,
  NAS, or any secondary volume to free up local storage — copies first,
  verifies every byte matches via checksum, and only then deletes the local
  original. Use whenever the user wants to "move X to my external drive",
  "offload folders to free up space", "clean up my disk by moving stuff
  off", "archive this to the WD/external HD and delete it locally", or is
  low on local disk space and wants candidates relocated rather than deleted.
  Also use if a previous move to an external drive was interrupted, killed,
  or the drive disconnected mid-copy — the underlying script is idempotent
  and resumable, so re-running it is always safe and it will pick up exactly
  where it left off without re-copying or re-deleting anything it already
  finished.
---

# Safe external move

Moving a large folder to an external drive is dangerous if done with a plain
`mv` or `cp` + `rm`: if the drive disconnects mid-copy, or you delete before
confirming the copy is actually intact, you can lose data permanently.
External drives (especially spinning HDDs over USB) are exactly the kind of
thing that disconnects mid-transfer for hundreds of gigabytes of transfer
time. This skill's job is to make "move" as safe as "copy" by never deleting
anything until it has been proven to match, byte-for-byte, at the
destination.

## Why this needs a script, not ad-hoc commands

A single `rsync` invocation copies but doesn't verify. A `diff -rq` verifies
but is slow and doesn't handle resuming after a drive drops out mid-run. The
bundled script (`scripts/safe-move.sh`) chains the right primitives together:

1. **Copy** with `rsync -a --partial` — resumable; if interrupted, re-running
   picks up from where it stopped instead of starting over.
2. **Verify** with `rsync -avnc --delete` (checksum, dry-run) — reads every
   byte on both sides and reports real differences, if any.
3. **Delete the source** only when verification comes back clean.
4. **Log everything** with timestamps to a markdown log, and **skip any pair
   already marked DELETED** in that log — so the whole run is idempotent. If
   the process gets killed (by the user, the OS, or a disconnected drive),
   just run it again with the same arguments.
5. **Pause and poll** (every 30s) instead of aborting if the destination
   volume disappears mid-copy or mid-verify — it self-resumes once the drive
   is reconnected, so you don't have to babysit it or restart it in a race
   against however long the transfer takes.

This is the same approach used to migrate ~370GB across three folders in a
prior session — copy, checksum-verify, then delete, with the process
surviving one interruption partway through cleanly on rerun.

## How to run it

1. **Identify the destination volume and check it's actually mounted.**
   `ls /Volumes` to see what's connected. If the user names a drive by brand
   ("my WD drive", "the external SSD") and multiple volumes show up, a single
   external disk can appear as several APFS volumes (e.g. a leftover bootable
   clone alongside a general-storage volume) — inspect with `diskutil list`
   and `ls` inside each candidate before assuming which one is the right
   destination. Don't guess if it's ambiguous; ask or look at existing folder
   naming conventions on the drive to infer the right one.

2. **Decide destination folder names.** If the destination already has a
   naming convention (e.g. existing folders like `Whatever 20210611`), match
   it. Otherwise a reasonable default is `<Source Folder Name>` as-is, or
   `<Label> <YYYYMMDD>` if you're relabeling or splitting up a source folder.

3. **Check free space before starting.** `du -sh` each source and `df -h` the
   destination volume — don't launch a multi-hundred-GB copy against a drive
   that doesn't have room. (The script also checks this per-pair right before
   each copy starts, but a heads-up up front avoids surprises.)

4. **Run the script**, one SRC/DST pair per folder, all in one invocation so
   they run sequentially:

   ```bash
   ~/Developer/agent-skills/safe-external-move/scripts/safe-move.sh \
     --log /path/to/some/scratch/dir/safe-move.log.md \
     "/Users/name/Desktop/Some Folder" "/Volumes/Storage/Some Folder" \
     "/Users/name/Documents/Another Folder" "/Volumes/Storage/Another Folder 20260902"
   ```

   Put the `--log` file somewhere durable for the session (a scratchpad
   directory is fine) — it's both the audit trail and the resume checkpoint.

5. **Run it in the background** if the transfer is large enough to take more
   than a minute or two — this is an I/O-bound, long-running job, and there's
   no reason to block on it. Check back on the log file's tail for progress,
   and report the final per-item outcome (verified+deleted vs. failed
   verification) once it completes.

6. **If it gets interrupted or killed for any reason**, don't panic and don't
   assume data was lost — check the log first. Because nothing is deleted
   until a clean verification, an interruption almost always just means the
   source is still fully intact locally. Re-run the exact same command; it
   will skip anything already fully migrated and resume the rest.

## After it finishes

Read the log and report, per folder: pre-copy size/file count, verification
result, and whether the source was deleted. If any item failed verification,
say so explicitly and leave it for manual review — the script already does,
by design (it never deletes on a failed or ambiguous verification).
