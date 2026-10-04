#!/usr/bin/env bash
# Pull bot.log from the Pi and print all agent responses (DMs and channel messages).
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
  | grep -E "agent invoked|response=sent|response=SKIP" \
  | tail -n "$(( TAIL_N * 3 ))" \
  | awk '
    /agent invoked/ {
      invoked = substr($1, 1, 19)
      if ($0 ~ /dm=True/) {
        source = "DM"
      } else {
        source = $0
        sub(/.*channel=/, "", source)
        source = "channel=" source
      }
      next
    }
    /response=sent/ {
      content = $0
      sub(/.*content=/, "", content)
      print "──────────────────────────────"
      print "Time:     " invoked
      print "Source:   " source
      print "Response: " content
      next
    }
    /response=SKIP/ {
      print "──────────────────────────────"
      print "Time:     " invoked
      print "Source:   " source
      print "Response: [SKIP]"
      next
    }
  '
