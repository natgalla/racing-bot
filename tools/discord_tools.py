import logging
import os
import requests
from datetime import datetime
from smolagents import tool
from .attachments import DISCORD_API, _bot_auth_headers, is_image
from .image_cache import extract_and_cache

logger = logging.getLogger(__name__)

# All requests.get calls in this module are synchronous and blocking. They must always be
# dispatched via run_in_executor — they share the thread pool with the classifier and image
# extraction, so slow Discord API responses can reduce effective semaphore throughput.


def _image_lines(obj: dict) -> list[str]:
    return [
        f"[Image attachment: {att['url']}]"
        for att in obj.get("attachments", [])
        if is_image(att)
    ]


@tool
def get_channel_pins(channel_id: str, max_pins: int = 5) -> str:
    """Fetch pinned messages from a Discord channel. Use this first for spec questions — the current race spec is typically pinned.

    Each pin is preceded by a [Pinned: YYYY-MM-DD] header showing when it was pinned. Use this date
    as the after_date argument to get_recent_messages so only relevant post-pin chatter is fetched.

    Returns up to max_pins most recent pins (default 5). Increase if the relevant spec may be in an older pin.

    Args:
        channel_id: The Discord channel ID to fetch pins from.
        max_pins: Maximum number of pins to return (default 5, newest first).
    """
    resp = requests.get(f"{DISCORD_API}/channels/{channel_id}/pins", headers=_bot_auth_headers(), timeout=20)
    if resp.status_code != 200:
        logger.error("get_channel_pins failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Error fetching pins: {resp.status_code} {resp.text}")
    pins = resp.json()
    pins = pins[:max_pins]
    if not pins:
        return "No pinned messages found in this channel."
    sections = []
    for p in pins:
        has_pinned_at = bool(p.get("pinned_at"))
        raw_date = p.get("pinned_at") or p.get("timestamp", "")
        try:
            pin_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pin_date = "unknown"
        if not has_pinned_at:
            # Discord occasionally omits pinned_at; the date then reflects the message's
            # creation time, not when it was pinned — flag it so the agent treats it as uncertain.
            logger.warning("get_channel_pins: pinned_at missing for pin, using message timestamp (approx date %s)", pin_date)
            pin_header = f"[Pinned (approx): {pin_date}]"
        else:
            pin_header = f"[Pinned: {pin_date}]"
        content = p.get("content", "")
        image_lines = _image_lines(p)
        parts = [content] if content else []
        # Exactly two images signals the spec handicap package (detunes + up-tunes), a deliberate posting convention.
        if len(image_lines) == 2:
            parts = ["[Spec handicap package: detunes + up-tunes]"] + parts
        parts += image_lines
        body = "\n".join(filter(None, parts))
        sections.append(f"{pin_header}\n{body}")
    return "\n\n---\n\n".join(sections)


@tool
def get_image_text(image_url: str) -> str:
    """Extract text and table data from an image URL. Use this when get_channel_pins returns [Image attachment: <url>] lines — call it to read handicap tables or other image-based content from pinned messages.

    Args:
        image_url: The URL of the image to extract text from.
    """
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        logger.error("get_image_text: huggingface_hub not available: %s", exc)
        return "Image reading is unavailable — huggingface_hub package not installed."
    try:
        client = InferenceClient(token=os.environ.get("HF_TOKEN"))
        return extract_and_cache(client, image_url)
    except Exception as exc:
        logger.exception("get_image_text failed")
        return f"Failed to read image content: {exc}"


@tool
def get_recent_messages(channel_id: str, limit: int = 20, after_date: str = "") -> str:
    """Fetch recent messages from a Discord channel. Use this if pinned messages don't have enough context, or if the spec may have been updated in a recent post.

    Output is capped at 6000 characters. For handicap standings searches, use a tight after_date window and limit=20 to stay within this cap.

    For handicap standings searches, identify the most recent Wednesday on or before today.
    Look back up to 10 days from that Wednesday (covers race day plus a 3-day late-post buffer).
    Find the most recent message containing "#standings" and an [Image attachment: <url>].
    If nothing found in 10 days, widen to 14 days.

    Args:
        channel_id: The Discord channel ID to fetch messages from.
        limit: Number of recent messages to fetch (default 20, max 100).
        after_date: Optional ISO date string (e.g. "2026-08-27"). When provided, only messages
            from that date onward are returned (date comparison only — messages on that same day
            are included). Use the [Pinned: YYYY-MM-DD] date from get_channel_pins so that
            pre-event chatter from prior sessions does not pollute the context.
    """
    limit = min(max(limit, 1), 100)
    resp = requests.get(
        f"{DISCORD_API}/channels/{channel_id}/messages",
        headers=_bot_auth_headers(),
        params={"limit": limit},
        timeout=20,
    )
    if resp.status_code != 200:
        logger.error("get_recent_messages failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Error fetching messages: {resp.status_code} {resp.text}")
    messages = resp.json()
    if not messages:
        return "No recent messages found in this channel."
    filter_date = None
    if after_date:
        try:
            filter_date = datetime.fromisoformat(after_date).date()
        except ValueError:
            pass
    lines = []
    username_map = {}
    for m in messages:
        ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
        if filter_date is not None and ts.date() < filter_date:
            continue
        real_username = m["author"]["username"]
        if real_username not in username_map:
            username_map[real_username] = f"User{len(username_map) + 1}"
        author = username_map[real_username]
        image_lines = _image_lines(m)
        parts = list(filter(None, [m["content"]] + image_lines))
        lines.append(f"[{ts.strftime('%H:%M')}] {author}: {' '.join(parts)}")
    result = "\n".join(lines) if lines else "No messages found after the specified date."
    CAP = 6000
    if len(result) > CAP:
        result = result[:CAP] + f"\n[... truncated — {len(lines)} lines total. Use a tighter after_date or smaller limit to see more recent messages.]"
    return result


@tool
def get_guild_events(guild_id: str, series_name: str = "") -> str:
    """Fetch upcoming scheduled Discord events for this server. Use this for schedule/timing questions.

    Args:
        guild_id: The Discord guild (server) ID to fetch events from.
        series_name: Optional case-insensitive substring to filter events by name. Pass the series name from the pinned spec without date qualifiers (e.g. 'Friday Night Lights' not 'Friday Night Lights SEP/4th').
    """
    if not guild_id:
        logger.info("get_guild_events: no guild_id provided, returning no events")
        return "No scheduled events found for this server."
    resp = requests.get(
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events", headers=_bot_auth_headers(), timeout=20
    )
    if resp.status_code != 200:
        logger.error("get_guild_events failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError(f"Error fetching events: {resp.status_code} {resp.text}")
    events = resp.json()
    if series_name:
        events = [e for e in events if series_name.lower() in e.get("name", "").lower()]
    if not events:
        if series_name:
            return f"No scheduled events found matching '{series_name}'."
        return "No scheduled events found for this server."
    lines = []
    for e in events:
        raw_time = e.get("scheduled_start_time", "")
        if raw_time:
            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            unix = int(dt.timestamp())
            start_time = f"<t:{unix}:F>"
        else:
            start_time = "TBD"
        status_map = {1: "SCHEDULED", 2: "ACTIVE", 3: "COMPLETED", 4: "CANCELLED"}
        status = status_map.get(e.get("status"), str(e.get("status", "UNKNOWN")))
        name = e.get("name", "Unnamed Event")
        description = e.get("description") or "No description"
        lines.append(f"{name} — {start_time} ({status}): {description}")
    return "\n".join(lines)
