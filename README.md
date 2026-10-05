# racing-bot

A Discord bot for sim racing communities. Answers spec and schedule questions passively — no @mention required for relevant messages.

## How it works

Every message in a categorized channel is scored by the Jev/TypeSafe classifier (`classifier_jev.py`). Messages that score at or above the relevance threshold (default 0.50) are passed to the agent, which reads pinned specs, guild events, and channel history to answer. Direct @mentions bypass the classifier and go straight to the agent.

Responses are posted in a thread on the original message.

Direct messages to the bot are also supported. DMs skip the classifier and category checks and run with the full toolset, including handicap calculations.

## Features

- Passive detection via the Jev/TypeSafe classifier (threshold 0.50)
- Reads pinned specs and channel history to answer rules/spec questions
- Reads Discord scheduled events for schedule questions
- Web search fallback for game data (GT7, Forza Motorsport)
- Discord dynamic timestamps — event times render in each user's local timezone
- SKIP suppression — banter and non-questions are silently ignored
- DM support — ask the bot directly in a direct message
- Handicap channel (`le-club-des-petits-gâteaux`) — series schedule, points formula, and image-extracted adjustment tables drive deterministic weight/power calculations
- Owner approval flow — when `OWNER_ID` is set, passive responses are DMed to the owner for a reaction (✅ to post, ❌ to discard) before going public
- Spec eligibility search — find cars that can be tuned to a power/weight target
- Brake balance guidance — starting-point brake balance by drivetrain layout
- Reply-to-mention — @mentioning the bot in a reply to another message uses the replied message as the question

## Setup

### Requirements

- Python 3.11+
- A Discord bot token with `message_content` intent enabled
- A HuggingFace account (free tier works for the classifier; 72B model requires Pro or Inference API access)

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
DISCORD_TOKEN=your_bot_token_here
HF_TOKEN=your_huggingface_token_here
TYPESAFE_API_KEY=your_typesafe_api_key_here
RELEVANCE_THRESHOLD=0.50  # optional, default 0.50
```

### Run

```bash
python bot.py
```

## Deploy

The bot runs on a Raspberry Pi at `gateaubot.local`. To deploy changes:

1. Push from local:
   ```bash
   git push
   ```
2. Pull on the Pi:
   ```bash
   ssh pi@gateaubot.local "cd ~/racing-bot && git pull"
   ```
3. Restart the bot:
   ```bash
   ssh pi@gateaubot.local "sudo systemctl restart racing-bot"
   ```

## Testing locally

A mock mode lets you test without a Discord token:

```bash
python test_local.py --mock "What's the spec for this week?"
python test_local.py --mock "When is the next race?"

# Classifier only (no agent invoked)
python test_local.py --classify "what tires do we run?"
```

## Bot permissions

Required Discord intents:
- `message_content`

Required channel permissions:
- Read Messages
- Send Messages
- Create Public Threads

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | required | Discord bot token |
| `HF_TOKEN` | required | HuggingFace token for the Qwen 72B agent model and image text extraction |
| `TYPESAFE_API_KEY` | required | API key for the Jev/TypeSafe relevance classifier |
| `OWNER_ID` | optional | Discord user ID for the passive-response approval flow (unset = post directly) |
| `HANDICAP_CHANNEL_ID` | optional | Channel ID used as the handicap context source for DMs and `warm_cache.py` |
| `RELEVANCE_THRESHOLD` | `0.50` | Classifier confidence threshold for passive detection |

## Evaluating DM responses

`eval.sh` pulls recent DM responses from the Pi's `bot.log` for review. Questions are not logged (privacy); only the bot's responses are shown.

```bash
./eval.sh            # recent DM responses
./eval.sh --tail 20  # only the last N exchanges
```
