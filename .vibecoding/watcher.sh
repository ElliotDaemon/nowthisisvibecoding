#!/bin/bash
# Watches for new user input via polling the input.json on GitHub
# Usage: bash .vibecoding/watcher.sh

REPO_DIR="/home/user/nowthisisvibecoding"
INPUT_FILE="$REPO_DIR/.vibecoding/input.json"
LAST_TS_FILE="/tmp/vibecoding_last_ts"

echo "0" > "$LAST_TS_FILE"

echo "[vibecoding watcher] Polling for user messages..."

while true; do
  # Pull latest changes
  cd "$REPO_DIR"
  git fetch origin claude/interactive-web-interface-rB0iQ --quiet 2>/dev/null
  git merge origin/claude/interactive-web-interface-rB0iQ --quiet 2>/dev/null

  if [ -f "$INPUT_FILE" ]; then
    CURRENT_TS=$(python3 -c "import json; print(json.load(open('$INPUT_FILE')).get('ts', 0))" 2>/dev/null || echo "0")
    LAST_TS=$(cat "$LAST_TS_FILE")

    if [ "$CURRENT_TS" != "$LAST_TS" ] && [ "$CURRENT_TS" != "0" ]; then
      echo "$CURRENT_TS" > "$LAST_TS_FILE"
      echo ""
      echo "=========================================="
      echo "[NEW MESSAGE] $(date)"
      echo "=========================================="
      python3 -c "
import json
data = json.load(open('$INPUT_FILE'))
for m in data.get('messages', []):
    processed = data.get('lastProcessed')
    if not processed or m.get('ts', 0) > processed:
        print(f\"USER: {m['content']}\")
"
      echo "=========================================="
      echo ""
    fi
  fi

  sleep 4
done
