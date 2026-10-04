#!/usr/bin/env bash
# Pull bot.log from the Pi and print DM exchanges (question + response pairs).
# Usage: ./eval.sh [--tail N]   (default: last 50 exchanges)

set -euo pipefail

PI="pi@gateaubot.local"
REMOTE_LOG="~/racing-bot/bot.log"
TAIL_N=50

while [[ $# -gt 0 ]]; do
  case $1 in
    --tail) TAIL_N="$2"; shift 2 ;;
    *) echo "Usage: $0 [--tail N]" >&2; exit 1 ;;
  esac
done

ssh "$PI" "cat $REMOTE_LOG" \
  | grep "dm=True" \
  | grep -E "agent invoked|response=sent|response=SKIP" \
  | tail -n "$(( TAIL_N * 3 ))" \
  | awk '
    /agent invoked dm=True/ {
      invoked = substr($1, 1, 19)
      next
    }
    /response=sent dm=True/ {
      content = $0
      sub(/.*content=/, "", content)
      print "──────────────────────────────"
      print "Time:     " invoked
      print "Response: " content
      next
    }
    /response=SKIP dm=True/ {
      print "──────────────────────────────"
      print "Time:     " invoked
      print "Response: [SKIP]"
      next
    }
  '
