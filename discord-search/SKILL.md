---
name: discord-search
description: Search and retrieve messages from Discord servers that have been mirrored into a local SQLite archive by the `discrawl` CLI. Use this whenever the user wants to find, search, look up, recall, or quote anything from a Discord server they've indexed — e.g. "search the paratext discord for what people said about USFM validation", "did anyone in the server mention the startup crash", "find that discord thread about the logo redesign", "what has tjcouch posted about markers", "pull the link someone shared in #general last month", or catching up on a past discussion. Trigger even when the user doesn't say "discrawl" — "search Discord", "find in the server", or asking what was said in a Discord channel is the cue. Read-only: it searches an existing local mirror and never posts to Discord. (This is NOT for converting a pasted Discord copy into Markdown — that's the separate discord-to-markdown skill.)
---

# Discord Search (via discrawl)

Find things in a Discord server by querying a **local SQLite mirror** that the
[`discrawl`](https://github.com/openclaw/discrawl) CLI keeps in sync via a read-only
bot. Discord gives bots no search endpoint, so discrawl mirrors history to disk and
you search that copy. Everything here is **read-only** — you retrieve and quote; you
never post.

Three ways to find things, in the order you'll usually reach for them:

1. **`discrawl --json search`** — full-text keyword search (the default).
2. **`discrawl sql`** — arbitrary read-only SQL when keywords aren't enough (counts,
   time ranges, group-by author, `LIKE`, joins).
3. **`discrawl messages`** — pull a slice of a channel to read surrounding context
   once search lands a hit.

## First, confirm there's a mirror to search

The archive is a local file; searching only works if the server has been synced.

```bash
discrawl status        # guilds + message counts already on disk
discrawl doctor        # config + bot auth + DB/FTS wiring (use if status looks empty)
```

If you see `config ... no such file`, it hasn't been set up on this machine yet —
jump to **Setup** at the bottom.

## The one rule that really matters: scope every sync to the bot

You'll `sync` to refresh the mirror before searching for recent things. Be careful:
`discrawl sync` **defaults to `--source both`, which also imports this Mac's local
Discord _desktop app cache_** — i.e. the user's DMs and every other server cached on
the machine. That is almost never what's wanted and quietly pulls private data into
the archive. So always scope refreshes to the bot's API view:

```bash
discrawl sync --source discord          # incremental refresh, bot-visible channels only
discrawl sync --source discord --full   # full historical backfill (slower; run once per server)
```

Only use bare `sync`, `--source both`, or `--source wiretap` if the user **explicitly**
asks to import their local desktop/DM cache. When in doubt, `--source discord`.

## Searching (FTS, the default)

```bash
discrawl --json search "usfm validation"          # JSON records — use when you'll parse/quote
discrawl search "usfm validation"                  # human-readable
discrawl search --channel 1265780732350038059 "logo"   # scope to one channel (use the ID)
discrawl search --author tjcouch_sil --limit 50 "markers"
discrawl --json search --mode hybrid "startup crash"    # FTS + semantic, if embeddings are configured
```

`--json` returns records shaped like:

```json
{ "message_id": "...", "channel_name": "general", "author_name": "tjcouch_sil",
  "content": "Feel free to invite other UX people ...", "created_at": "2024-07-30T16:14:43.421Z" }
```

Notes that save you a round-trip:

- **Use channel IDs, not names.** Names collide — a text `#general` and a voice
  `General` both match `general`, and discrawl will refuse an ambiguous name. Get IDs
  from `discrawl channels list`.
- FTS matches **tokens**, and query words are treated as literal terms (not `AND`/`OR`
  operators). If a search comes back empty, broaden or drop terms, or switch to SQL
  `LIKE` (below).
- `--limit` (newest first), `--author`, `--guild`, `--include-empty` (include messages
  whose only content is an attachment/embed/reply) are all available.

## When keywords aren't enough: SQL

`discrawl sql` runs **read-only** SQL over the archive — the escape hatch for anything
FTS can't express (how many, by whom, when, substring matches, joins).

```bash
discrawl sql "select count(*) as msgs, min(created_at) first, max(created_at) last from messages"
discrawl sql "select author_id, count(*) n from messages group by author_id order by n desc limit 10"
discrawl sql "select created_at, content from messages where content like '%invite%' order by created_at desc limit 20"
```

Core schema (discover more with the pragma queries below):

- **`messages`**: `id, guild_id, channel_id, author_id, message_type, created_at,
  edited_at, deleted_at, content, normalized_content, reply_to_message_id, pinned,
  has_attachments`
- **`channels`**, **`members`**, `message_attachments`, `mention_events`; full-text
  index lives in `message_fts`.

```bash
discrawl sql "select name from sqlite_master where type='table' order by 1"
discrawl sql "select name, type from pragma_table_info('messages')"
```

Author names live in `members`, not `messages` — join on `author_id` (or just read
`author_name` from `--json search` output, which resolves it for you).

## Reading context around a hit

```bash
discrawl messages --channel 1265780732350038059 --last 20         # newest 20, printed oldest→newest
discrawl messages --channel 1265780732350038059 --since 2026-03-01T00:00:00Z
discrawl --json messages --channel 1265780732350038059 --days 7
```

Good for reconstructing a conversation once search points you at a message/time.

## Setup (only if `doctor`/`status` show it isn't configured)

Prerequisites:

- discrawl installed: `brew install openclaw/tap/discrawl`
- A Discord **bot** token (never a user token — automating a user account violates
  Discord ToS). The bot must be invited to the target server with **View Channels** +
  **Read Message History**, and have **Message Content Intent** enabled in the Discord
  developer portal.

Provide the token (pick one), then initialize:

```bash
# Option A: environment variable
export DISCORD_BOT_TOKEN="..."
# Option B: macOS keychain (discrawl reads it automatically)
security add-generic-password -U -s discrawl -a discord_bot_token -w   # prompts hidden

discrawl init --guild <server-id>     # writes config, pins the default guild
discrawl doctor                       # verify auth + DB
discrawl sync --source discord --full # first backfill (bot-only; see the sync rule above)
```

## Troubleshooting

- **`config ... no such file`** → not initialized: `discrawl init --guild <id>`.
- **`channel X is ambiguous`** → use the numeric channel ID from `discrawl channels list`.
- **Empty results** → broaden/drop query terms, try `discrawl sql "... like '%term%'"`,
  or refresh with `discrawl sync --source discord` if the message is recent.
- **`403 ... Missing Access` on archived threads during sync** → the bot lacks thread
  permissions; top-level channel messages still sync fine.
- **No write/post commands exist here by design** — this workflow is read-only. If the
  user wants to *send* a message, that's out of scope for this skill.

## Going deeper

discrawl has more read commands (per-channel `digest`, `analytics`, `members`,
`mentions`, `attachments`, live `tail`, Git-backed sharing). See
[`references/discrawl-commands.md`](references/discrawl-commands.md) when a request
goes beyond search/SQL/message-slices.
