---
name: jira-ticket
description: >
  Draft and create a new Jira work item for the Paratext (PT) project from context — a task note, Discord thread, conversation, or description.
  Searches for existing tickets first, drafts the work item with standard sections, saves a draft to Obsidian, presents it for review, creates it in Jira, and links related issues.
  Use when the user says "write a Jira ticket", "create a work item", "add this to Jira", or provides context and asks for a ticket.
---

# Jira Ticket Skill

Draft, review, and create a Jira work item for the Paratext PT project.

## CLI setup

All Jira commands require `JIRA_INSECURE=true` — without it, TLS cert verification fails with `x509: OSStatus -26276`.

```bash
JIRA_INSECURE=true jira issue <command> ...
```

---

## Steps

### 1. Search for existing tickets

Before drafting anything, check if a ticket already exists:

```bash
JIRA_INSECURE=true jira issue list --jql "project = PT AND text ~ \"<keyword>\"" --plain 2>&1 | head -40
```

Scan results for anything that covers the same problem. If a strong match exists, surface it to the user and ask whether to proceed with a new ticket or update the existing one.

---

### 2. Gather context

Read all relevant sources the user has provided: task notes, Discord threads, linked vault notes, GitHub issues. Understand:
- **What** the problem or request is
- **Why** it matters and what decision has been made (if any)
- **Who** was involved in the decision
- **What** the expected vs. actual behavior is (for bugs)
- **What** "done" looks like
- **Where** the relevant code lives — grep or search for the files and line numbers so you can include direct GitHub links in the Background section

When the ticket touches existing code, always locate it before drafting. Get the info you need for stable links:

```bash
git rev-parse HEAD                  # commit SHA to pin links (branch refs drift)
git remote get-url origin           # repo URL (convert git@ to https:// form)
grep -n "symbol or pattern" path/to/file.ts
```

GitHub permalink format:
```
https://github.com/<org>/<repo>/blob/<sha>/<path/to/file.ts>#L<line>
# Range:
https://github.com/<org>/<repo>/blob/<sha>/<path/to/file.ts>#L<start>-L<end>
```

---

### 3. Determine ticket type and sections

| Type | Required sections |
|------|-------------------|
| Bug | User Story, Background, How to Reproduce, Acceptance Criteria, Testing |
| Combined (Task / Dev Task / UX Task) | User Story, Background, Decision (if applicable), Acceptance Criteria, Testing |
| Any | Add open questions / callouts where decisions need product owner sign-off |

---

### 4. Draft the work item

Write the draft using Markdown. Key formatting rules:

- Top-level sections use `###` headings; subsections within a section may use `####`
- Numbered lists: use `1.` `2.` `3.` — **never** `#` (renders as headings in Jira)
- Bold: `**text**` — not `*text*` (that's italic)
- Links: `[text](url)` — **not** Jira wiki `[text|url]` (doubles the URL)
- Warning/callout: `> ⚠️ **Label** — text` (blockquote with emoji — this is the safest approach via CLI; Jira's native panel/callout blocks are ADF and cannot be set through the CLI's `--body` Markdown flag)
- `{warning}` and other Jira wiki macros do **not** work via CLI

**Standard section order:**

```
### User Story
As a <user>, I want <goal> so that <reason>.

---

### Background
Context, history, what decision was made and by whom (link to Discord/source).
If it's a phased plan, number the steps with 1. 2. 3.
When the ticket references specific code, include direct GitHub permalink(s) pinned to a commit SHA:
  [file.ts lines N–M](https://github.com/org/repo/blob/<sha>/path/file.ts#LN-LM) — one-line description

#### <Open question subheading, if needed>
> ⚠️ **Needs clarification from product owner** — describe the trade-off or ambiguity.

---

### How to Reproduce   ← bugs only
Steps to reproduce.

**Expected behavior:** ...
**Actual behavior:** ...

---

### Implementation Ideas
(usually left empty — fill in if known)

---

### Acceptance Criteria
- The ... is ...
- No ... remains in ...

---

### Testing
1. Step to verify fix
2. Step to verify no regressions
```

---

### 5. Ask clarifying questions before saving

Before saving the draft or creating the ticket, ask the user:

1. **UX Review field** — what should it be set to? Default: `Needs UX Review`
2. **Task note** — if the user is working out of a task note, offer to update it with the Jira ticket key and URL once created

---

### 6. Save draft to Obsidian

Save the draft as a standalone note in the vault. Use a descriptive name like `<Short Title> · Jira Draft.md`.

Frontmatter tags to always include:
- `jira` — it's a Jira work item
- `genAI` — it was AI-generated
- Any relevant project tag (e.g. `p10`)

Set `status: draft` in frontmatter at this point. Only change to `status: archived` and add the `archived` tag once the ticket has been created in Jira and the workflow is complete.

---

### 7. Present for review

Show the draft to the user and ask:
> "Does this look right? What would you like to change before I create it in Jira?"

Iterate until accepted.

---

### 8. Create the ticket in Jira

Create with a stub first (the full body heredoc can fail silently in `--no-input` mode):

```bash
JIRA_INSECURE=true jira issue create --no-input \
  --type <Bug|Task|"Dev Task"|"UX Task"> \
  --project PT \
  --summary "<Summary text>" \
  --body "Stub — updating with full description." 2>&1
```

Note the ticket key (e.g. `PT-XXXX`) from the output URL.

Then immediately update with the full body:

```bash
JIRA_INSECURE=true jira issue edit PT-XXXX --no-input --body "$(cat <<'JIRA'
### User Story
...
JIRA
)" 2>&1
```

---

### 9. Link related issues

Use the `jira issue link` command to link related tickets — do **not** put them in the description body.

```bash
JIRA_INSECURE=true jira issue link PT-XXXX PT-YYYY "Relates" 2>&1
```

Available link types: `Blocks`, `Cloners`, `Duplicate`, `Relates`, `Discovery - Connected`

If the link type is wrong, the CLI returns the full list of valid types.

---

### 10. Finalize the Obsidian draft note

- Add the Jira ticket key and URL to the frontmatter or top of the draft note
- Change `status` to `archived` and add the `archived` tag
- If the user is working out of a task note, update it with the ticket key and URL

---

### 11. Report back

Tell the user:
- The Jira ticket key and URL
- Any open questions or callouts in the ticket that still need product owner sign-off
- Offer to draft a Discord reply notifying relevant participants (if applicable)
