---
name: standup
description: Generate a Paratext team standup update from the vault. Reads today's daily note, recent vault activity, and upcoming tasks to produce a formatted snippet ready to paste into the team standup doc. Focuses on Paratext/P10 work; includes personal items only if they significantly affect availability.
---

# Standup Skill

Generate a standup update for Alex's Paratext product team. Output a snippet ready to paste into the ongoing standup doc.

**Standup doc:** https://docs.google.com/document/d/1Jxeq1Vz4kHSJ6r2cTeqk6jjNIAzc1cWkgG1giuPNUqU/edit?tab=t.0

---

## Steps

### 1. Gather data in parallel

Run all of these simultaneously:

**Today's daily note:**
```bash
obsidian vault=Vault daily:read 2>&1 | grep -v "representedObject\|Loading updated\|out of date\|installer\|Loaded main\|Ignored\|Checking\|Success\|Latest version\|App is up\|Obsidian\["
```

**Recent vault changes (since yesterday):**
```bash
cd "/Users/merc/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault" && git log --since="yesterday" --name-only --pretty=format:"--- %ad %s" --date=short | grep -v "^---" | grep -v "^$" | grep -v "^Daily/" | grep -v "^\\.claude/" | sort -u
```

**Open and in-progress P10/UX tasks:**
```bash
grep -rl "^status: open\|^status: doing" "/Users/merc/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault/TaskNotes/Tasks/" | xargs grep -l "p10\|ux\|paratext\|PT-\|storybook\|shadcn" 2>/dev/null
```

**Upcoming scheduled tasks (next 7 days) with p10/ux tags:**
```bash
grep -rl "^scheduled: $(date +%Y-%m)" "/Users/merc/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault/TaskNotes/Tasks/" 2>/dev/null
```

Read the content of any relevant task notes and work session notes surfaced above.

---

### 2. Categorize items

**Include:**
- Anything tagged `#p10`, `#ux`, `#paratext`, or referencing `PT-` Jira tickets, Paratext GitHub PRs, Figma files, or Marvin research
- UX reviews, design principle work, UXR planning/sessions, Storybook work
- Meetings about the Paratext product (with team members like Katherine, Ian, Levi, Jesse, Sebastian, Roopa, etc.)
- Personal items **only if** they significantly reduce availability (e.g., travel, sick day, all-day commitment)

**Exclude:**
- Personal tasks (relocation, home, health, family) unless they block availability
- Non-Paratext projects
- Claude/Obsidian tooling experiments

---

### 3. Assign emoji status to each item

Use this legend exactly:

| Emoji | Meaning |
|-------|---------|
| ☑️ | Happened or completed |
| 🚴 | Ongoing |
| 🚵 | Ongoing but difficult / up a hill |
| 🔜 | Coming up |
| ⛔ | Blocked |
| 🔥 | This is fine (used humorously for managed chaos) |
| 🤒 | Sick / health-related unavailability |
| 🆕 | New item |
| 📣 | Announcement |
| 🏝️ | Time off / unavailable |

---

### 4. Surface discussion questions

While reviewing the notes, look for:
- Open questions Alex has posed (e.g., "should we...?", "ask around", "ask Ian/Katherine/team")
- Decisions that seem unresolved or need group input
- Tensions or trade-offs between approaches that would benefit from team discussion
- Anything flagged with "ask", "check with", "TBD", or "?" directed at the team

Format each as a bullet starting with `Alex Mercado:` followed by the question, written as a direct question to the group. Keep them concise. Omit this section entirely if there are no meaningful discussion questions.

---

### 5. Format the output

**Update block** (bulleted markdown):
```
Alex Mercado
* ☑️ [Item description]
* ☑️ [Item description]
  * [sub-item or detail]
  * [PT-XXXX](url) [PR #XXXX](url) [Discord](url)
* 🚴 [Ongoing work item]
* 🔜 [Upcoming item]
```

**Discussion block** (bulleted markdown, only if questions exist):
```
* Alex Mercado: [Question for the group?]
* Alex Mercado: [Another question?]
```

Rules for the update block:
- Start with `Alex Mercado` (no heading, no date — it'll be pasted under a date heading)
- Use `*` bullets throughout
- **Include Markdown links** for any Jira tickets (`PT-XXXX`), GitHub PRs, Figma boards, Discord threads, or Marvin sessions — format as `[PT-XXXX](url)`, `[PR #XXXX](url)`, `[Figma](url)`, `[Discord](url)`, `[Marvin](url)`
- Group related items together; put ☑️ first, then 🚴/🚵, then 🔜
- Keep descriptions concise — short phrases, not sentences
- Omit empty sections rather than padding

---

### 6. Output and clipboard

1. Print the update block as a code block.
2. Print the discussion block as a separate code block (skip if empty).
3. Pipe the full combined text (both blocks, update block first, then discussion block) to the clipboard:
```bash
printf '%s' "<full text>" | pbcopy
```
4. Confirm: "Copied to clipboard."
5. Briefly note anything you weren't sure how to categorize and ask if the user wants to adjust before pasting.
