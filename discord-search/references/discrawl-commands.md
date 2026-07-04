# discrawl — extended command reference

Read this when a request goes beyond the core search / SQL / message-slice workflow in
`SKILL.md`. All commands below are **read-only** or local-archive maintenance; none
post to Discord. Add `--json` to most for machine-readable output. Scope to a guild
with `--guild <id>` (otherwise the configured default guild, or all guilds for search).

## Contents

- [Activity & analytics](#activity--analytics)
- [People & mentions](#people--mentions)
- [Attachments](#attachments)
- [Channels & status](#channels--status)
- [Live tail & freshness](#live-tail--freshness)
- [Read-only sharing (no bot token)](#read-only-sharing-no-bot-token)

## Activity & analytics

```bash
discrawl digest --since 7d                 # per-channel activity summary for a window
discrawl digest --channel general --since 30d
discrawl --json digest --since 7d --top-n 5

discrawl analytics quiet --since 30d       # channels with no messages in the window
discrawl analytics trends --weeks 8        # weekly message counts per channel
discrawl analytics trends --weeks 12 --channel general
```

`--since` accepts Go durations (`72h`, `30m`) and `Nd` shorthand (`7d`, `30d`).

## People & mentions

```bash
discrawl members list
discrawl members search "design engineer"      # matches names + archived profile fields
discrawl members show --messages 25 <user-id-or-name>

discrawl mentions --channel maintainers --days 7
discrawl mentions --target <user-id> --type user --limit 50
discrawl --json mentions --type role --days 1
```

Member/profile data is strictly what the bot archived (names, roles, join time, and any
bio/website/social fields Discord exposed). discrawl can't invent fields it never saw.

## Attachments

```bash
discrawl attachments --channel general --days 7          # list attachment metadata
discrawl attachments --filename crash --type image --all
discrawl attachments fetch --channel general --days 7    # download media into local cache
```

Media bytes live under the cache dir, not SQLite; the DB stores filename, hash, path,
size, and fetch status. Discord CDN URLs expire, so some fetches 404 — that's a dead
remote object, not a local failure.

## Channels & status

```bash
discrawl channels list
discrawl channels show <channel-id>
discrawl status                    # archive totals, last sync/tail times
discrawl coverage --json           # how much of the archive is actually usable, per channel
discrawl diagnostics --json        # DB path, integrity, WAL, sync-lock owner (no network)
discrawl failures --limit 50       # unresolved sync/import/media/embedding failures
```

## Live tail & freshness

```bash
discrawl tail --guild <id>         # live Gateway updates + periodic repair (long-running)
discrawl sync --source discord     # one-shot incremental refresh (see the sync rule in SKILL.md)
```

Prefer a one-shot `sync --source discord` before a search when you just need freshness.
`tail` is for keeping a mirror continuously current and holds the process open.

## Read-only sharing (no bot token)

A team can publish the archive as a private Git snapshot; readers subscribe with **no
Discord credentials** and search locally:

```bash
discrawl subscribe https://github.com/example/discord-archive.git
discrawl search "launch checklist"
discrawl messages --channel <id> --hours 24
```

Subscribers run in a token-free mode (`sync`/`tail` are disabled — they need live
Discord access). This is the natural path for giving teammates read-only search over a
shared, centrally-maintained mirror without each of them running a bot.
