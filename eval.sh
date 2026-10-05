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
  | grep -E "agent invoked|response=sent|response=SKIP|reaction emoji=" \
  | awk -v tail_n="$TAIL_N" '
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
      mid = $0; sub(/.*message_id=/, "", mid); sub(/ .*/, "", mid)
      content = $0; sub(/.*content=/, "", content)
      responses[mid] = content
      times[mid] = invoked
      sources[mid] = source
      order[++count] = mid
      next
    }
    /response=SKIP/ {
      mid = "skip_" NR
      responses[mid] = "[SKIP]"
      times[mid] = invoked
      sources[mid] = source
      order[++count] = mid
      next
    }
    /reaction emoji=/ {
      mid = $0; sub(/.*message_id=/, "", mid); sub(/ .*/, "", mid)
      emoji = $0; sub(/.*reaction emoji=/, "", emoji); sub(/ .*/, "", emoji)
      if (mid in responses) {
        reactions[mid] = (reactions[mid] == "") ? emoji : reactions[mid] " " emoji
      }
      next
    }
    END {
      start = (count > tail_n) ? count - tail_n + 1 : 1
      for (i = start; i <= count; i++) {
        mid = order[i]
        print "──────────────────────────────"
        print "Time:     " times[mid]
        print "Source:   " sources[mid]
        print "Response: " responses[mid]
        if (mid in reactions) print "Reactions: " reactions[mid]
      }
    }
  '
