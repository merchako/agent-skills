---
name: sync-skills
description: >
  Sync globally installed skills into the current project's local .claude/skills/ folder, making them available project-specifically.
  Use this skill whenever the user says "sync skills", "copy global skills to project", "add my global skills locally", "install skills locally", "bring in global skills", "pull global skills into this project", or wants to make their globally installed agent skills available in a specific project directory.
  Also trigger for "what global skills do I have", "list my global skills", or "which skills are available globally" when the user is in a project context and likely wants to sync.
---

# sync-skills

This skill syncs globally installed skills into a project's local `.claude/skills/` folder by symlinking from `~/.agents/skills/` (where global skills live) into `./.claude/skills/`.

## When to use this

When the user wants to:
- Make their full global skill set available within a specific project
- Mirror their global skills to a new project they're setting up
- See which skills are globally installed vs locally available

## How it works

Global skills installed with `npx skills add -g` are stored at `~/.agents/skills/<name>/` and symlinked into `~/.claude/skills/`. This skill creates matching symlinks from those same source dirs into `./.claude/skills/`, making them project-local without duplicating files.

---

## Step 1: Show the user what will be synced

Run this to get a preview of global skills:

```bash
ls ~/.agents/skills/
```

Also check what's already local to avoid duplicating:

```bash
ls ./.claude/skills/ 2>/dev/null || echo "(no local skills yet)"
```

Show the user a summary:
- How many global skills exist
- How many are already in the local project (will be skipped)
- How many are new and will be synced

Ask: "Sync all X global skills to this project? (new ones only, skipping duplicates)"

Unless the user already said yes or used a flag like `-y`, get confirmation before proceeding.

---

## Step 2: Create the local skills directory (if needed)

```bash
mkdir -p .claude/skills
```

---

## Step 3: Sync global skills into the project

For each skill in `~/.agents/skills/` that doesn't already exist in `.claude/skills/`, create a symlink:

```bash
for skill_dir in ~/.agents/skills/*/; do
  skill_name=$(basename "$skill_dir")
  target=".claude/skills/$skill_name"
  if [ ! -e "$target" ]; then
    ln -s "$skill_dir" "$target"
    echo "✓ Synced: $skill_name"
  else
    echo "  Skipped (already exists): $skill_name"
  fi
done
```

If the user passes `--copy` or prefers copies over symlinks (e.g., they want to customize locally without affecting the global version), use `cp -r` instead:

```bash
cp -r "$skill_dir" "$target"
```

---

## Step 4: Verify and report

Run:

```bash
ls .claude/skills/
```

Report:
- Total skills now in `.claude/skills/`
- How many were newly synced vs already present
- Reminder: "Reload Claude Code (or your agent) to activate newly synced skills."

---

## Checking modified skills back into source

Skills installed globally live at `~/.agents/skills/<name>/`. Edits made there are **not** automatically reflected in the source repo. Use this workflow to commit changes back.

### Step 1: Find the source repo

Check the three possible locations (in order of likelihood):

```bash
ls ~/Developer/agent-skills-private/<name>/ 2>/dev/null
ls ~/Developer/agent-skills/<name>/ 2>/dev/null
ls ~/Developer/second-brain-skills/<name>/ 2>/dev/null
```

Use whichever exists. If none do, the skill was never checked in — create the directory in the appropriate repo (private for personal/vault skills, `agent-skills` for general, `second-brain-skills` for Obsidian-specific).

### Step 2: Diff to sanity-check

```bash
diff ~/.agents/skills/<name>/ ~/Developer/<repo>/<name>/
```

Review what's new or changed before copying.

### Step 3: Copy changed files

```bash
cp ~/.agents/skills/<name>/<file> ~/Developer/<repo>/<name>/<file>
```

Copy specific files rather than the whole directory to avoid overwriting unrelated source-only files.

### Step 4: Commit and push

```bash
git -C ~/Developer/<repo> add <name>/<file>
git -C ~/Developer/<repo> commit -m "vault: describe what changed"
git -C ~/Developer/<repo> push
```

---

## Alternative: Sync from source repos (re-download approach)

If the user wants to re-fetch from GitHub rather than symlink local copies — for instance to pin a version or install into a project without global installs — use the `npx skills` CLI approach instead:

```bash
# Preview global skills registered with the CLI
npx skills list -g

# Re-add them locally (from GitHub source)
# Extract repo owners from skill metadata or ask the user which repos to pull from
npx skills add <owner/repo> -y
```

This is slower (requires network) but gives clean project-local copies fetched directly from source.

---

## Tips

- Symlinks mean updates to the global skill automatically apply to all synced projects — usually the desired behavior.
- Use `--copy` if you want an independent local copy you can customize per-project.
- To remove a synced skill from the project without affecting the global install: `rm .claude/skills/<name>`
- To list what's currently local: `npx skills list` (without `-g`)
