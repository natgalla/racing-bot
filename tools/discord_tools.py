from smolagents import tool
import os
import requests
from datetime import datetime

DISCORD_API = "https://discord.com/api/v10"


def _headers():
    return {"Authorization": f"Bot {os.environ['DISCORD_TOKEN']}"}


@tool
def get_channel_pins(channel_id: str) -> str:
    """Fetch pinned messages from a Discord channel. Use this first for spec questions — the current race spec is typically pinned.

    Args:
        channel_id: The Discord channel ID to fetch pins from.
    """
    resp = requests.get(f"{DISCORD_API}/channels/{channel_id}/pins", headers=_headers())
    if resp.status_code != 200:
        return f"Error fetching pins: {resp.status_code} {resp.text}"
    pins = resp.json()
    if not pins:
        return "No pinned messages found in this channel."
    return "\n\n---\n\n".join(p["content"] for p in pins)


@tool
def get_recent_messages(channel_id: str, limit: int = 20) -> str:
    """Fetch recent messages from a Discord channel. Use this if pinned messages don't have enough context, or if the spec may have been updated in a recent post.

    Args:
        channel_id: The Discord channel ID to fetch messages from.
        limit: Number of recent messages to fetch (default 20, max 100).
    """
    resp = requests.get(
        f"{DISCORD_API}/channels/{channel_id}/messages",
        headers=_headers(),
        params={"limit": limit},
    )
    if resp.status_code != 200:
        return f"Error fetching messages: {resp.status_code} {resp.text}"
    messages = resp.json()
    if not messages:
        return "No recent messages found in this channel."
    lines = []
    for m in messages:
        ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
        author = m["author"]["username"]
        lines.append(f"[{ts.strftime('%H:%M')}] {author}: {m['content']}")
    return "\n".join(lines)


@tool
def get_guild_events(guild_id: str) -> str:
    """Fetch upcoming scheduled Discord events for this server. Use this for schedule/timing questions.

    Args:
        guild_id: The Discord guild (server) ID to fetch events from.
    """
    resp = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events", headers=_headers()
    )
    if resp.status_code != 200:
        return f"Error fetching events: {resp.status_code} {resp.text}"
    events = resp.json()
    if not events:
        return "No scheduled events found for this server."
    lines = []
    for e in events:
        raw_time = e.get("scheduled_start_time", "")
        if raw_time:
            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            start_time = dt.strftime("%A, %B %d at %I:%M %p UTC")
        else:
            start_time = "TBD"
        status_map = {1: "SCHEDULED", 2: "ACTIVE", 3: "COMPLETED", 4: "CANCELLED"}
        status = status_map.get(e.get("status"), str(e.get("status", "UNKNOWN")))
        name = e.get("name", "Unnamed Event")
        description = e.get("description") or "No description"
        lines.append(f"{name} — {start_time} ({status}): {description}")
    return "\n".join(lines)
