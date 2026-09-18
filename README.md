# racing-bot

A Discord bot for sim racing communities. Answers spec and schedule questions passively — no @mention required for relevant messages.

## How it works

Every message in a categorized channel is scored by a local zero-shot classifier. Messages that score above the relevance threshold are passed to the agent, which reads pinned specs, guild events, and channel history to answer. Direct @mentions bypass the classifier and go straight to the agent.

Responses are posted in a thread on the original message.

## Features

- Passive detection via local zero-shot classifier (no API call per message)
- Reads pinned specs and channel history to answer rules/spec questions
- Reads Discord scheduled events for schedule questions
- Web search fallback for game data (GT7, Forza Motorsport)
- Discord dynamic timestamps — event times render in each user's local timezone
- SKIP suppression — banter and non-questions are silently ignored

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
RELEVANCE_THRESHOLD=0.75  # optional, default 0.75
```

### Run

```bash
python bot.py
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
| `RELEVANCE_THRESHOLD` | `0.75` | Classifier confidence threshold for passive detection |
