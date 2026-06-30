#!/usr/bin/env python3
"""discord2md — convert a Discord rich-text clipboard copy into clean Markdown.

Deterministic, zero-dependency (Python stdlib only). The whole point is to avoid
an LLM round-trip: Discord puts an HTML flavor on the clipboard that preserves the
real structure (author groups, the user's own bullet/number lists, links, emoji,
attachments). A naive HTML->Markdown converter turns Discord's *message list* (an
<ol>) into a numbered list, clobbering the genuine lists the poster typed. This
tool treats the message list specially and only renders the inner content lists.

Input  (first match wins):
  --html-file F   read HTML from a file
  stdin           if stdin is not a TTY, read HTML from it
  clipboard       else pull the public.html flavor via `osascript` (macOS)
                  (falls back to the plain-text flavor with a warning)

Output: clipboard + stdout by default; --out FILE and --obsidian add destinations.

See SKILL.md for the agent-facing workflow and config.json schema.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from urllib.parse import urlparse

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - py<3.9
    ZoneInfo = None

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/discord2md/config.json")
DEFAULT_TZ = "America/Chicago"
DEFAULT_LINK_BASE = "discord.com"  # use "ptb.discord.com" to open in Discord PTB
INDENT = "  "  # per nesting level for lists
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

VOID = {"br", "img", "hr", "meta", "input", "wbr", "source", "col"}


# --------------------------------------------------------------------------- #
# Minimal HTML DOM
# --------------------------------------------------------------------------- #
class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs=None):
        self.tag = tag  # None => text node
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = None
        self.text = None


class DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        n.parent = self.cur
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, attrs)
        n.parent = self.cur
        self.cur.children.append(n)

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root and node.parent is not None:
            self.cur = node.parent

    def handle_data(self, data):
        n = Node(None)
        n.text = data
        n.parent = self.cur
        self.cur.children.append(n)


def parse_html(html_text):
    b = DOMBuilder()
    b.feed(html_text)
    return b.root


def cls(node):
    return node.attrs.get("class", "") if node.tag else ""


def has_cls(node, token):
    return token in cls(node)


def descendants(node):
    for c in node.children:
        yield c
        if c.tag:
            yield from descendants(c)


def find_all(node, pred):
    return [c for c in descendants(node) if pred(c)]


def find_first(node, pred):
    for c in descendants(node):
        if pred(c):
            return c
    return None


def text_of(node):
    if node.tag is None:
        return node.text or ""
    return "".join(text_of(c) for c in node.children)


def clean(s):
    return (s or "").translate(ZERO_WIDTH)


# --------------------------------------------------------------------------- #
# Inline rendering (Discord content -> Markdown)
# --------------------------------------------------------------------------- #
INLINE_WRAP = {
    "strong": "**", "b": "**",
    "em": "*", "i": "*",
    "s": "~~", "del": "~~", "strike": "~~",
}


def is_block_code(node):
    """True for a <code> that is a fenced block (lives inside <pre>)."""
    p = node.parent
    while p is not None and p.tag is not None:
        if p.tag == "pre":
            return True
        p = p.parent
    return False


def render_inline(n, emoji="unicode"):
    if n.tag is None:
        return clean(n.text)
    t = n.tag
    c = cls(n)

    if t in ("ul", "ol"):
        return ""  # lists are block-level; render_list owns them
    if t == "br":
        return "\n"
    if t == "img":
        if "emoji" in c:
            if emoji == "shortcode":
                name = n.attrs.get("data-name", "").strip(":")
                return f":{name}:" if name else (n.attrs.get("alt") or "")
            return n.attrs.get("alt") or ""  # unicode char Discord put in alt
        return ""  # real attachments handled at message level, not inline
    if "channelMention" in c:
        return clean(text_of(n)).strip()
    if "mention" in c:
        s = clean(text_of(n)).strip()
        return s if s.startswith("@") else "@" + s
    if "spoiler" in c:
        return "||" + "".join(render_inline(x, emoji) for x in n.children) + "||"
    if t in INLINE_WRAP:
        w = INLINE_WRAP[t]
        inner = "".join(render_inline(x, emoji) for x in n.children)
        return f"{w}{inner}{w}" if inner.strip() else inner
    if t == "u":
        inner = "".join(render_inline(x, emoji) for x in n.children)
        return f"<u>{inner}</u>" if inner.strip() else inner
    if t == "code" and not is_block_code(n):
        return "`" + clean(text_of(n)) + "`"
    if t == "a":
        href = (n.attrs.get("href") or "").strip()
        txt = "".join(render_inline(x, emoji) for x in n.children).strip()
        if not href:
            return txt
        if not txt or txt == href:
            return href
        return f"[{txt}]({href})"
    return "".join(render_inline(x, emoji) for x in n.children)


# --------------------------------------------------------------------------- #
# Block rendering
# --------------------------------------------------------------------------- #
def _top_nested_lists(li):
    """ul/ol descendants of <li> that are not themselves inside another list.

    Discord often wraps the nested list inside a <span> within the <li>, so we
    cannot rely on direct children — we scan descendants and keep the top-most.
    """
    out = []
    for d in descendants(li):
        if d.tag in ("ul", "ol"):
            p, top = d.parent, True
            while p is not None and p is not li:
                if p.tag in ("ul", "ol"):
                    top = False
                    break
                p = p.parent
            if top:
                out.append(d)
    return out


def render_list(node, ordered, indent, emoji):
    lines = []
    i = int(node.attrs.get("start", 1)) if ordered else 1
    for li in [c for c in node.children if c.tag == "li"]:
        marker = f"{i}." if ordered else "-"
        text = render_inline(li, emoji).strip()  # nested lists return "" here
        body = text.split("\n") if text else [""]
        lines.append(f"{indent}{marker} {body[0]}".rstrip())
        cont = indent + " " * (len(marker) + 1)  # align under the marker
        for bl in body[1:]:
            lines.append((cont + bl).rstrip())
        for sl in _top_nested_lists(li):
            lines.append(render_list(sl, sl.tag == "ol", cont, emoji))
        i += 1
    return "\n".join(lines)


def render_blockquote(node, emoji):
    inner = render_content(node, emoji)
    return "\n".join(("> " + ln).rstrip() for ln in inner.split("\n"))


def render_pre(node, emoji):
    lang = ""
    for d in descendants(node):
        m = re.search(r"language-(\w+)", cls(d))
        if m:
            lang = m.group(1)
            break
    code = find_first(node, lambda n: n.tag == "code") or node
    body = clean(text_of(code)).rstrip("\n")
    return f"```{lang}\n{body}\n```"


def render_content(node, emoji="unicode"):
    """Render a content container, separating block elements with blank lines."""
    parts, buf = [], []

    def flush():
        if buf:
            parts.append("".join(buf))
            buf.clear()

    for c in node.children:
        if c.tag in ("ul", "ol"):
            flush()
            parts.append(render_list(c, c.tag == "ol", "", emoji))
        elif c.tag == "blockquote":
            flush()
            parts.append(render_blockquote(c, emoji))
        elif c.tag == "pre" or (c.tag == "div" and "codeBlock" in cls(c)):
            flush()
            parts.append(render_pre(c, emoji))
        elif c.tag in ("h1", "h2", "h3"):
            flush()
            lvl = int(c.tag[1])
            inner = "".join(render_inline(x, emoji) for x in c.children).strip()
            parts.append("#" * lvl + " " + inner)
        else:
            buf.append(render_inline(c, emoji))
    flush()

    out = "\n\n".join(p.strip("\n") for p in parts if p.strip())
    # collapse 3+ blank lines that Discord's stray spans can introduce
    return re.sub(r"\n{3,}", "\n\n", out).strip()


# --------------------------------------------------------------------------- #
# Attachments / images
# --------------------------------------------------------------------------- #
def message_attachment_urls(mdiv):
    """Uploaded image attachments (not link-preview embeds)."""
    urls = []
    for a in find_all(mdiv, lambda n: n.tag == "a" and "originalLink" in cls(n)):
        href = a.attrs.get("href", "")
        if href:
            urls.append(href)
    if not urls:  # fallback: lazy <img> that is not inside an embed
        for img in find_all(mdiv, lambda n: n.tag == "img" and "lazyImg" in cls(n)):
            if find_first_ancestor(img, lambda p: "embed" in cls(p)):
                continue
            src = img.attrs.get("src", "")
            if src:
                urls.append(src)
    return urls


def find_first_ancestor(node, pred):
    p = node.parent
    while p is not None:
        if p.tag and pred(p):
            return p
        p = p.parent
    return None


def filename_from_url(url):
    name = os.path.basename(urlparse(url).path) or "image"
    return name


def download(url, dest):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "discord2md"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())


def to_webp(src, dest):
    """Convert via cwebp (preferred) or sips. Returns True on success."""
    for cmd in (["cwebp", "-quiet", src, "-o", dest],
                ["sips", "-s", "format", "webp", src, "--out", dest]):
        try:
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0 and os.path.exists(dest):
                return True
        except FileNotFoundError:
            continue
    return False


def render_image(url, mode, assets_dir, link_style, warn):
    fname = filename_from_url(url)
    if mode == "remove":
        return f"[image: {fname}]"
    if mode == "inline":
        return f"![{fname}]({url})"  # NOTE: Discord URLs expire ~24h
    # sidecar / webp -> download to disk
    os.makedirs(assets_dir, exist_ok=True)
    base = os.path.join(assets_dir, fname)
    try:
        download(url, base)
    except Exception as e:  # noqa: BLE001 - degrade gracefully
        warn(f"image download failed ({fname}): {e}")
        return f"[image: {fname} (download failed)]"
    out_name = fname
    if mode == "webp":
        webp = os.path.splitext(base)[0] + ".webp"
        if to_webp(base, webp):
            if webp != base and os.path.exists(base):
                os.remove(base)
            out_name = os.path.basename(webp)
        else:
            warn(f"webp conversion unavailable; kept {fname}")
    if link_style == "wikilink":
        return f"![[{out_name}]]"
    rel = os.path.relpath(os.path.join(assets_dir, out_name), os.getcwd())
    return f"![{out_name}]({rel})"


# --------------------------------------------------------------------------- #
# Message extraction
# --------------------------------------------------------------------------- #
MSG_ID_RE = re.compile(r"chat-messages-(\d+)-(\d+)")


def thread_title(root):
    ol = find_first(root, lambda n: n.tag == "ol" and "chat-messages" in n.attrs.get("data-list-id", ""))
    if not ol:
        ol = find_first(root, lambda n: n.tag == "ol" and n.attrs.get("aria-label"))
    if ol:
        label = ol.attrs.get("aria-label", "")
        m = re.match(r"Messages in (.+)$", label)
        if m:
            return clean(m.group(1)).strip()
    return None


def parse_message(li, guild_map, link_base, emoji, img_mode, assets_dir, link_style, warn):
    mdiv = find_first(li, lambda n: n.tag == "div" and "message_" in cls(n) and n.attrs.get("role") == "article")
    if mdiv is None:
        mdiv = li
    is_system = "isSystemMessage" in cls(mdiv)

    uname = find_first(mdiv, lambda n: n.tag == "span" and "username" in cls(n))
    author = clean(text_of(uname)).strip() if uname else ""
    h3 = find_first(mdiv, lambda n: n.tag == "h3" and "header" in cls(n))
    has_header = bool(h3) and not is_system

    tnode = find_first(mdiv, lambda n: n.tag == "time" and n.attrs.get("datetime"))
    ts_iso = tnode.attrs.get("datetime") if tnode else None

    channel_id = msg_id = None
    m = MSG_ID_RE.search(li.attrs.get("id", ""))
    if m:
        channel_id, msg_id = m.group(1), m.group(2)

    content_div = find_first(mdiv, lambda n: n.tag == "div" and "messageContent" in cls(n))

    if is_system:
        return {"system": True, "text": clean(text_of(mdiv)).strip(),
                "ts_iso": ts_iso, "channel_id": channel_id, "msg_id": msg_id}

    body_parts = []
    if content_div is not None:
        c = render_content(content_div, emoji)
        if c:
            body_parts.append(c)
    for url in message_attachment_urls(mdiv):
        body_parts.append(render_image(url, img_mode, assets_dir, link_style, warn))

    link = None
    if channel_id and msg_id:
        guild = guild_map.get(channel_id)
        if guild:
            link = f"https://{link_base}/channels/{guild}/{channel_id}/{msg_id}"

    return {
        "system": False, "has_header": has_header, "author": author,
        "ts_iso": ts_iso, "link": link, "channel_id": channel_id, "msg_id": msg_id,
        "body": "\n\n".join(p for p in body_parts if p.strip()),
    }


# --------------------------------------------------------------------------- #
# Timestamp
# --------------------------------------------------------------------------- #
def fmt_ts(ts_iso, tz):
    if not ts_iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except ValueError:
        return ts_iso
    if ZoneInfo and tz:
        try:
            dt = dt.astimezone(ZoneInfo(tz))
        except Exception:  # noqa: BLE001
            pass
    return dt.strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------------------- #
# Guild auto-learning
# --------------------------------------------------------------------------- #
CHANNEL_LINK_RE = re.compile(r"discord(?:app)?\.com/channels/(\d+)/(\d+)(?:/(\d+))?")


def harvest_guilds(html_text, guild_map):
    """Learn channel->guild from any real discord.com/channels/ URLs in content."""
    learned = {}
    for gid, cid, _ in CHANNEL_LINK_RE.findall(html_text):
        if cid not in guild_map:
            learned[cid] = gid
    guild_map.update(learned)
    return learned


# --------------------------------------------------------------------------- #
# Clipboard / input
# --------------------------------------------------------------------------- #
def clipboard_html():
    try:
        out = subprocess.run(
            ["osascript", "-e", "the clipboard as «class HTML»"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"[0-9A-Fa-f]{8,}", out)
    if not m:
        return None
    try:
        return bytes.fromhex(m.group(0)).decode("utf-8", "replace")
    except ValueError:
        return None


def read_stdin_if_ready():
    """Read stdin only when data is actually available.

    A bare TTY has no piped input. A non-TTY stdin that is an open pipe with no
    data and no EOF (some launchers, cron, Raycast) would block forever on
    read(); select() lets us skip it and fall through to the clipboard.
    """
    if sys.stdin.isatty():
        return None
    try:
        import select
        ready, _, _ = select.select([sys.stdin], [], [], 0.2)
        if not ready:
            return None
        data = sys.stdin.read()
        return data if data.strip() else None
    except Exception:  # noqa: BLE001 - select unsupported, etc.
        return None


def clipboard_text():
    try:
        return subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return ""


def set_clipboard(text):
    try:
        p = subprocess.run(["pbcopy"], input=text, text=True)
        return p.returncode == 0
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# Plain-text fallback (degraded: lists & links are not recoverable)
# --------------------------------------------------------------------------- #
HEADER_RE = re.compile(r"^(.+?) — (.*\d{1,2}:\d{2})\s*$")


def convert_plaintext(text, warn):
    warn("no HTML clipboard flavor found — using plain text; lists, links, and "
         "structure cannot be fully recovered. Copy again from Discord if possible.")
    out, first = [], True
    for line in text.splitlines():
        m = HEADER_RE.match(line.strip())
        if m:
            if not first:
                out.append("\n---\n")
            first = False
            out.append(f"**{m.group(1).strip()}** · {m.group(2).strip()}\n")
        elif line.strip() == "Image":
            out.append("[image]")
        else:
            out.append(line)
    return "\n".join(out).strip()


# --------------------------------------------------------------------------- #
# Main conversion
# --------------------------------------------------------------------------- #
def convert_html(html_text, opts, warn):
    root = parse_html(html_text)
    messages = find_all(root, lambda n: n.tag == "li" and "messageListItem" in cls(n))
    if not messages:
        return None  # signal caller to try plain-text fallback

    if opts["learn_links"]:
        harvest_guilds(html_text, opts["guild_map"])

    blocks = []
    if opts["title"]:
        t = thread_title(root)
        if t:
            blocks.append(f"# {t}")

    groups = []  # list of {"author","ts_iso","link","parts":[...]}
    cur = None
    for li in messages:
        info = parse_message(li, opts["guild_map"], opts["link_base"], opts["emoji"],
                             opts["images"], opts["assets_dir"], opts["link_style"], warn)
        if info["system"]:
            if opts["system"] and info["text"]:
                groups.append({"system": True, "text": info["text"]})
                cur = None
            continue
        if info["has_header"] or cur is None:
            cur = {"system": False, "author": info["author"], "ts_iso": info["ts_iso"],
                   "link": info["link"], "parts": []}
            groups.append(cur)
        if info["body"].strip():
            cur["parts"].append(info["body"])

    rendered = []
    for g in groups:
        if g.get("system"):
            rendered.append(f"*{g['text']}*")
            continue
        if not g["parts"]:
            continue
        ts = fmt_ts(g["ts_iso"], opts["tz"])
        if g["link"] and ts:
            head = f"**{g['author']}** · [{ts}]({g['link']})"
        elif ts:
            head = f"**{g['author']}** · {ts}"
        else:
            head = f"**{g['author']}**"
        rendered.append(head + "\n\n" + "\n\n".join(g["parts"]))

    body = "\n\n---\n\n".join(rendered)
    if blocks:
        body = blocks[0] + "\n\n" + body
    return body.strip() + "\n"


def load_config(path):
    p = path or DEFAULT_CONFIG_PATH
    if os.path.exists(p):
        try:
            return json.load(open(p)), p
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"discord2md: warning: bad config {p}: {e}\n")
    return {}, p


def save_config(cfg, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(cfg, open(path, "w"), indent=2, ensure_ascii=False)


def build_parser():
    ap = argparse.ArgumentParser(prog="discord2md", description="Convert a Discord clipboard copy to Markdown.")
    ap.add_argument("--html-file", help="read HTML from a file instead of the clipboard")
    ap.add_argument("--to", default="clip,stdout", help="comma list: clip,stdout,file (default: clip,stdout)")
    ap.add_argument("--out", help="write Markdown to FILE (implies file)")
    ap.add_argument("--obsidian", action="store_true", help="write a note to config.output_note_dir; default images=webp, wikilinks")
    ap.add_argument("--images", choices=["remove", "sidecar", "webp", "inline"], help="image handling (default: config or remove)")
    ap.add_argument("--assets-dir", help="where sidecar/webp files go")
    ap.add_argument("--link-style", choices=["wikilink", "md"], help="image ref style")
    ap.add_argument("--emoji", choices=["unicode", "shortcode"], default="unicode")
    ap.add_argument("--tz", help=f"timezone (default: config or {DEFAULT_TZ})")
    ap.add_argument("--link-base", help=f"channels host (default: config or {DEFAULT_LINK_BASE})")
    ap.add_argument("--system", action="store_true", help="keep system messages (title changes) as muted lines")
    ap.add_argument("--embeds", action="store_true", help="keep link-preview embeds")
    ap.add_argument("--no-title", action="store_true", help="omit the thread title H1")
    ap.add_argument("--no-links", action="store_true", help="do not harvest guild ids from content links")
    ap.add_argument("--learn", metavar="URL", help="record a channel->guild mapping from a Discord message link, then exit")
    ap.add_argument("--config", help=f"config path (default: {DEFAULT_CONFIG_PATH})")
    ap.add_argument("-q", "--quiet", action="store_true", help="suppress stderr notes")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg, cfg_path = load_config(args.config)
    guild_map = dict(cfg.get("channel_guild_map", {}))

    def warn(msg):
        if not args.quiet:
            sys.stderr.write(f"discord2md: {msg}\n")

    if args.learn:
        m = CHANNEL_LINK_RE.search(args.learn)
        if not m:
            sys.stderr.write("discord2md: --learn needs a discord.com/channels/<guild>/<channel>/<msg> URL\n")
            return 2
        gid, cid = m.group(1), m.group(2)
        guild_map[cid] = gid
        cfg["channel_guild_map"] = guild_map
        save_config(cfg, cfg_path)
        warn(f"learned channel {cid} -> guild {gid} (saved to {cfg_path})")
        return 0

    images = args.images or cfg.get("default_image_mode", "remove")
    link_style = args.link_style or cfg.get("default_link_style")
    if args.obsidian:
        images = args.images or cfg.get("obsidian_image_mode", "webp")
        link_style = link_style or "wikilink"
        assets_dir = args.assets_dir or cfg.get("attachments_dir") or os.path.join(os.getcwd(), "Attachments")
    else:
        assets_dir = args.assets_dir or cfg.get("assets_dir") or os.path.join(os.getcwd(), "discord2md-assets")
    link_style = link_style or "md"

    opts = {
        "guild_map": guild_map,
        "link_base": args.link_base or cfg.get("link_base", DEFAULT_LINK_BASE),
        "tz": args.tz or cfg.get("timezone", DEFAULT_TZ),
        "images": images,
        "assets_dir": assets_dir,
        "link_style": link_style,
        "emoji": args.emoji,
        "system": args.system,
        "embeds": args.embeds,
        "title": not args.no_title,
        "learn_links": not args.no_links,
    }

    # Resolve input. Explicit input (file/stdin) is used as given; otherwise we
    # self-fetch the clipboard's HTML flavor, falling back to its plain text.
    raw = None
    if args.html_file:
        raw = open(args.html_file, encoding="utf-8").read()
    else:
        raw = read_stdin_if_ready()

    md = None
    if raw is not None:
        if "<" in raw:
            md = convert_html(raw, opts, warn)
        if md is None:
            md = convert_plaintext(raw, warn)
    else:
        clip = clipboard_html()
        if clip:
            md = convert_html(clip, opts, warn)
        if md is None:
            md = convert_plaintext(clipboard_text(), warn)

    if not md or not md.strip():
        warn("nothing to convert — the clipboard had no Discord message content")
        return 1

    # Persist any newly learned guild ids
    if opts["learn_links"] and guild_map != cfg.get("channel_guild_map", {}):
        cfg["channel_guild_map"] = guild_map
        try:
            save_config(cfg, cfg_path)
        except Exception:  # noqa: BLE001
            pass

    targets = set(filter(None, args.to.split(",")))
    if args.out:
        targets.add("file")
    if args.obsidian:
        targets.add("obsidian")

    if "stdout" in targets:
        sys.stdout.write(md)
    if "clip" in targets:
        if set_clipboard(md):
            warn("copied Markdown to clipboard")
    if "file" in targets and args.out:
        open(args.out, "w", encoding="utf-8").write(md)
        warn(f"wrote {args.out}")
    if "obsidian" in targets:
        out_dir = cfg.get("output_note_dir") or os.getcwd()
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        first_line = md.splitlines()[0] if md else ""
        title = first_line.lstrip("# ").strip() or "thread"
        safe = re.sub(r"[^\w .—-]+", "", title)[:60].strip()
        path = os.path.join(out_dir, f"{date} Discord — {safe}.md")
        open(path, "w", encoding="utf-8").write(md)
        warn(f"wrote Obsidian note {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
