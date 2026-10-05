# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Discord bot for sim racing communities. It passively monitors channels and answers spec, schedule, and handicap questions without requiring an @mention. A local zero-shot classifier gates all messages before they reach the LLM agent.

## Running and Testing

```bash
# Start the bot (requires .env with DISCORD_TOKEN, HF_TOKEN, TYPESAFE_API_KEY)
python bot.py

# Run agent against a mock question (no Discord token needed)
python test_local.py --mock "What car should I run this week?"

# Run with a specific channel name or author
python test_local.py --mock "question" --channel-name le-club-des-petits-gâteaux --author-username drivername

# Run an interactive multi-turn DM session
python test_local.py --mock "question" --dm

# Classify a message only (returns relevance score)
python test_local.py --classify "some message text"

# Refresh the GT7 car list cache from gtdb.io
python test_local.py --refresh-gtdb
```

No test framework, no linter configured. `test_local.py` is the only testing harness.

## Deployment

The bot runs on a Raspberry Pi at `gateaubot.local`. SSH access is via key auth (`pi@gateaubot.local`). The bot process and log (`bot.log`) live at `~/racing-bot/` on the Pi.

To deploy changes:

```bash
# 1. Push from local
git push

# 2. Pull on the Pi
ssh pi@gateaubot.local "cd ~/racing-bot && git pull"

# 3. Restart the bot
ssh pi@gateaubot.local "sudo systemctl restart racing-bot"
```

User messages are intentionally not logged (privacy).

### Evaluating DM responses

```bash
# Pull and display recent DM responses from the Pi log
./eval.sh

# Show only the last N exchanges
./eval.sh --tail 20
```

`eval.sh` SSHes to the Pi, filters `bot.log` for DM exchanges, and prints each response with its timestamp. Questions are not shown (not logged).

## Architecture

### Request pipeline

```
Discord message
  → bot.py (event handler)
    → classifier_jev.py (Jev/TypeSafe classifier, threshold 0.50)
      → agent.py (Qwen 72B via HuggingFace InferenceClient)
        → tools/* (Discord API, GT7 DB, web search, handicap calc)
          → threaded Discord reply (or SKIP)
```

### Key files

| File | Role |
|---|---|
| `bot.py` | Discord client, message routing, thread posting |
| `agent.py` | ToolCallingAgent config, system prompt, SKIP gate logic |
| `classifier_jev.py` | Jev/TypeSafe classifier; returns float confidence score (threshold 0.50, overridable via `RELEVANCE_THRESHOLD` env var) |
| `tools/discord_tools.py` | Pins, recent messages, guild events, user profiles |
| `tools/gtdb_tools.py` | GT7 car spec lookup and fuzzy search via gtdb.io scraping |
| `tools/gtdb_cache.py` | File-backed cache with 30-day TTL for GT7 car list and detail pages |
| `tools/handicap_tools.py` | Unit conversion (lbs↔kg, hp↔PS) with percentage math |
| `tools/search_tools.py` | DuckDuckGo web search |
| `tools/tuning_tools.py` | Handling symptom → tuning parameter recommendations |
| `tools/sources_tools.py` | Returns data source attribution for the bot |
| `tools/image_cache.py` | Image URL → extracted text via LLM vision model, file-backed cache |
| `eval.sh` | Pull and display recent DM responses from the Pi log |

### SKIP gate

The agent returns the literal string `"SKIP"` when a message is not a genuine question (banter, race incident reports, etc.). `bot.py` silences the response in that case. This is the primary quality control for passive mode.

### Handicap channel

Messages in `le-club-des-petits-gâteaux` get additional system-prompt context: series schedule, points formula, and image extraction for adjustment tables. Driver name matching and handicap calculations flow through `handicap_tools.py` for deterministic math.

### Caching

Both `gtdb_cache.py` and `image_cache.py` write JSON to local files. Cache files should not be committed. The GT7 car list has a 30-day TTL; detail pages are cached indefinitely until manually cleared.

## Environment

Copy `.env.example` to `.env`. Required vars: `DISCORD_TOKEN`, `HF_TOKEN`, `TYPESAFE_API_KEY`.

The bot listens only in channels under the "Gran Turismo 7" Discord category unless the channel name matches a configured override.
