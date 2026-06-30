#!/bin/bash
# Raycast Script Command: convert the Discord copy on the clipboard to Markdown,
# in place. Copy messages in Discord, run this, then paste the clean Markdown.
#
# Install: copy this file into a Raycast Script Commands directory
# (Raycast → Extensions → Script Commands → add directory), or symlink it there:
#   ln -s ~/.claude/skills/discord-to-markdown/raycast-discord-to-md.sh \
#         ~/path/to/raycast-scripts/
#
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Discord → Markdown
# @raycast.mode silent
#
# Optional parameters:
# @raycast.icon 📋
# @raycast.packageName Discord
# @raycast.description Convert the Discord messages on the clipboard to clean Markdown (in place).
# @raycast.author Alex Mercado

SCRIPT="$HOME/.claude/skills/discord-to-markdown/discord2md.py"
[ -f "$SCRIPT" ] || SCRIPT="$HOME/Developer/agent-skills/discord-to-markdown/discord2md.py"

if python3 "$SCRIPT" --to clip --quiet; then
  echo "Converted Discord copy to Markdown ✓"
else
  echo "No Discord content on the clipboard"
fi
