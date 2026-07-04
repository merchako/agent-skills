---
name: discord-search
description: Search and retrieve messages from Discord servers mirrored into a local SQLite archive by the `discrawl` CLI. Use this whenever the user wants to find, search, look up, recall, or quote anything from a Discord server — e.g. "search the paratext discord for what people said about USFM validation", "did anyone in the server mention the startup crash", "find that discord thread about the logo redesign", "what has tjcouch posted about markers", "pull the link someone shared in #general last month" — and also when they want to set up Discord search on their machine ("set up discord search", "index my discord"). Works two ways — a read-only bot mirror, or a tokenless "wiretap" import of the user's own Discord desktop-app cache — so trigger even if no bot exists. Read-only: it never posts to Discord. (NOT for converting a pasted Discord copy into Markdown — that's the separate discord-to-markdown skill.)
---

# Discord Search (via discrawl)

Find things in a Discord server by querying a **local SQLite mirror** built by the
[`discrawl`](https://github.com/openclaw/discrawl) CLI. Discord gives bots no search
endpoint and clients no export, so discrawl mirrors messages to disk and you search
that copy. Everything here is **read-only** — you retrieve and quote; you never post.

The mirror can be fed from two sources, and which one applies changes the rules:

| Mode | Source | Who has it | Coverage |
| ---- | ------ | ---------- | -------- |
| **Bot mode** | `sync --source discord` — a read-only bot pages channel history via the API | Machines with a `DISCORD_BOT_TOKEN` (env or keychain) | Full history of every channel the bot was granted |
| **Wiretap mode** | `sync --source wiretap` — parses the user's own Discord **desktop-app cache** | Anyone with the Discord app; no token, no bot, no server permissions | Only what the app has cached — roughly, channels the user has viewed |

Check which mode you're in: `discrawl doctor` — if it reports the discord token as
missing, you're in wiretap mode (that's normal, not an error; search/SQL work fine).

Three ways to find things, in the order you'll usually reach for them:

1. **`discrawl --json search`** — full-text keyword search (the default).
2. **`discrawl sql`** — arbitrary read-only SQL when keywords aren't enough (counts,
   time ranges, group-by author, `LIKE`, joins).
3. **`discrawl messages`** — pull a slice of a channel to read surrounding context
   once search lands a hit.

## First, confirm there's a mirror to search

The archive is a local file; searching only works if something has been synced.

```bash
discrawl status        # guilds + message counts already on disk
discrawl doctor        # config + DB/FTS wiring (use if status looks empty)
```

If you see `config ... no such file`, it hasn't been set up on this machine yet —
jump to **Setup** at the bottom.

## Refreshing the mirror (the rules that matter)

**Bot mode** — always scope refreshes to the bot's API view:

```bash
discrawl sync --source discord          # incremental refresh, bot-visible channels only
discrawl sync --source discord --full   # full historical backfill (slower; run once per server)
```

Never run bare `sync` in bot mode: it defaults to `--source both`, which _also_
silently imports the local desktop-app cache (DMs and every other cached server).

**Wiretap mode** — the cache import is the whole point, but disclose its scope the
first time you run it for a user:

```bash
discrawl sync --source wiretap          # incremental; fast; re-run any time for freshness
```

- **It imports everything the app cached — DMs and all servers included.**
  `--guild` does NOT scope the wiretap import (known limitation) — it all lands in
  the local DB. It never leaves the machine, but the user should know it's there.
  Scope _searches_ with `--guild <id>` to keep results to one server.
- **Coverage = channels the user has viewed.** If a search misses something the user
  knows exists, have them open and scroll that channel in the Discord app, then
  re-run the wiretap sync — the newly cached messages become searchable.

## Searching (FTS, the default)

```bash
discrawl --json search "usfm validation"          # JSON records — use when you'll parse/quote
discrawl search "usfm validation"                  # human-readable
discrawl search --guild 892072317436448768 "focus group"   # one server only
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
- To link a hit: `https://discord.com/channels/<guild_id>/<channel_id>/<message_id>`
  (DM hits use `@me` as the guild segment).

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
  has_attachments` (`guild_id` is `@me` for DMs)
- **`channels`**, **`members`**, `message_attachments`, `mention_events`; full-text
  index lives in `message_fts`.

```bash
discrawl sql "select name from sqlite_master where type='table' order by 1"
discrawl sql "select name, type from pragma_table_info('messages')"
```

Author names live in `members`, not `messages` — join `messages.author_id` on
`members.user_id` (or just read `author_name` from `--json search` output, which
resolves it for you). Wiretap imports may leave some authors unresolved — fall back
to the raw `author_id`.

## Reading context around a hit

```bash
discrawl messages --channel 1265780732350038059 --last 20         # newest 20, printed oldest→newest
discrawl messages --channel 1265780732350038059 --since 2026-03-01T00:00:00Z
discrawl --json messages --channel 1265780732350038059 --days 7
```

Good for reconstructing a conversation once search points you at a message/time.

## Setup (only if `doctor`/`status` show it isn't configured)

Install first (macOS/Linux): `brew install openclaw/tap/discrawl`

### Path A — no bot token (wiretap mode; the common case)

`discrawl init` **requires a valid bot token** (it validates against the Discord API),
so tokenless users write the config directly. This block auto-detects whether the
user runs the normal Discord app or Discord PTB (whichever cache is bigger wins);
adjust `default_guild_id` to the user's primary server:

```bash
DISCORD_DIR="$HOME/Library/Application Support/discord"
PTB_KB=$(du -sk "$HOME/Library/Application Support/discordptb/Cache" 2>/dev/null | cut -f1)
STABLE_KB=$(du -sk "$HOME/Library/Application Support/discord/Cache" 2>/dev/null | cut -f1)
[ "${PTB_KB:-0}" -gt "${STABLE_KB:-0}" ] && DISCORD_DIR="$HOME/Library/Application Support/discordptb"

mkdir -p "$HOME/Library/Application Support/discrawl"
cat > "$HOME/Library/Application Support/discrawl/config.toml" <<EOF
version = 1
default_guild_id = '<primary-server-id>'
guild_ids = ['<primary-server-id>']
db_path = '$HOME/Library/Application Support/discrawl/discrawl.db'
cache_dir = '$HOME/Library/Caches/discrawl'
log_dir = '$HOME/Library/Application Support/discrawl/logs'

[discord]
token_source = 'env'
token_env = 'DISCORD_BOT_TOKEN'

[desktop]
path = '$DISCORD_DIR'
max_file_bytes = 67108864
full_cache = false

[sync]
source = 'wiretap'

[search]
default_mode = 'fts'
EOF

discrawl sync --source wiretap   # first import (disclose the DM/all-servers sweep)
discrawl status                  # confirm messages landed
```

Before the first import, tell the user: this sweeps everything their Discord app has
cached — DMs and all servers — into a local-only SQLite file. Nothing is uploaded.

### Path B — bot token (full-history mode)

Needs a Discord **bot** token (never a user token — automating a user account
violates Discord ToS). The bot must be invited to the target server with
**View Channels** + **Read Message History**, and have **Message Content Intent**
enabled in the Discord developer portal.

```bash
# Option A: environment variable
export DISCORD_BOT_TOKEN="..."
# Option B: macOS keychain (discrawl reads it automatically)
security add-generic-password -U -s discrawl -a discord_bot_token -w   # prompts hidden

discrawl init --guild <server-id>     # writes config, pins the default guild
discrawl doctor                       # verify auth + DB
discrawl sync --source discord --full # first backfill (bot-only; see the sync rules above)
```

## Troubleshooting

- **`config ... no such file`** → not set up: Path A (no token) or Path B (token) above.
- **`discrawl init` exits with a token error / HTTP 401** → init always validates the
  token. Tokenless users skip init entirely and write the config by hand (Path A).
- **Wiretap import reports 0 messages** → almost always the wrong `[desktop] path` —
  the user runs the other client flavor (`discord` vs `discordptb`). Compare cache
  sizes as in Path A and repoint.
- **Search misses a message the user knows exists (wiretap mode)** → the app never
  cached it. Open + scroll that channel in Discord, then re-run
  `discrawl sync --source wiretap`.
- **`channel X is ambiguous`** → use the numeric channel ID from `discrawl channels list`.
- **Empty results** → broaden/drop query terms, try `discrawl sql "... like '%term%'"`,
  or refresh the mirror (mode-appropriate sync) if the message is recent.
- **`403 ... Missing Access` on archived threads during bot sync** → the bot lacks
  thread permissions; top-level channel messages still sync fine.
- **No write/post commands exist here by design** — this workflow is read-only. If the
  user wants to _send_ a message, that's out of scope for this skill.

## Going deeper

discrawl has more read commands (per-channel `digest`, `analytics`, `members`,
`mentions`, `attachments`, live `tail`, Git-backed sharing via
`subscribe` — token-free read-only team mirrors). See
[`references/discrawl-commands.md`](references/discrawl-commands.md) when a request
goes beyond search/SQL/message-slices.
