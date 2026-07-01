# discord-to-markdown

Turn a **Discord message copy** into clean Markdown — deterministically, with no LLM in the loop.
Built for repeatedly pasting Discord threads into LLMs and Obsidian.

## The problem

Copy messages in Discord and your clipboard gets two flavors:

- **plain text** — your typed bullet/number lists lose their markers, links vanish.
- **HTML** — preserves structure, but wraps the whole thread in `<ol data-list-id="chat-messages">`
  with each message as `<li>`. Generic HTML→Markdown converters render that as one big numbered
  list, **clobbering the genuine lists the poster typed**.

## What this does

`discord2md.py` parses the HTML flavor, treats the message list as author groups (not list items),
and renders only the *inner* content lists — so the output reads like what people actually typed:

```markdown
# [Sp 83] Saroj drafts a chapter

**Sebastian UBS** · [2026-06-03 03:06](https://discord.com/channels/…/…/…)

If I have questions to the PRD: should I

- A) post in here
- B) write a comment in the [google doc](https://docs.google.com/…) or
- C) write to the owner (Ian)?

My questions are:

1. Was it decided we go with a lot of little editors vs a big editor. *Why am I asking this?*
   - We have not tested that this actually makes it easier for the user.
   - PT10 already has a big editor, but not little editors yet
```

Handles: author grouping (continuations flow under one header, `---` between groups), real
bullet/number lists with nesting, **bold/italic/strike/inline-code/code-blocks/blockquotes/headers**,
masked links, `@mentions` and `#channel` mentions as plain text, unicode + custom emoji, system
messages, OP/BOT badges, link-preview embeds, and image attachments (remove / sidecar / webp / inline).

## Requirements

- macOS (reads the clipboard via `osascript` / `pbpaste`)
- Python 3.9+ (stdlib only — no `pip install`)
- `cwebp` (optional, for `--images webp`; falls back to `sips`, then keeps the original)

## Usage

```bash
# Default: clipboard HTML -> Markdown back to clipboard AND stdout
python3 discord2md.py

python3 discord2md.py --to stdout            # just print (for piping)
python3 discord2md.py --out thread.md        # write a file
python3 discord2md.py --obsidian             # write an Obsidian note; images -> webp, ![[...]]
python3 discord2md.py --images webp          # download + convert images
python3 discord2md.py --system --embeds      # keep title-changes and link previews
python3 discord2md.py --html-file copy.html  # convert a saved HTML flavor (testing)
```

### Message links

Discord links need a guild id the clipboard doesn't include. Teach it once per channel
(right-click a message in Discord → **Copy Message Link**):

```bash
python3 discord2md.py --learn "https://discord.com/channels/<guild>/<channel>/<message>"
```

After that, every paste from that channel gets clickable timestamps.

## Configuration

Personal settings live in `~/.config/discord2md/config.json` (see `SKILL.md` for the schema).
The script ships with no personal data, so it's safe to share; your config (guild map, vault paths)
stays local.

## Notes

- **Images + Claude**: Markdown image refs don't feed Claude's vision — attach the downloaded
  files. `webp`/`sidecar` exist to produce those files (and render in Obsidian).
- **Inline image URLs expire** (~24h); prefer `webp`/`sidecar` for anything durable.
- No HTML flavor on the clipboard (e.g. from clipboard-history managers, which store text only)
  → degrades to a best-effort plain-text parse and warns.
- **Replies**: Discord doesn't copy the replied-to reference, so a reply's "replying to X"
  context can't be recovered — only the reply's own text. Copy the referenced message too if needed.
- **`---`**: used as the between-group separator; a literal `---` typed in a message renders as a
  rule as well (both are dividers, but indistinguishable in the output).
