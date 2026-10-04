"""Shared helpers for Discord attachment handling and API auth headers."""
import os

DISCORD_API = "https://discord.com/api/v10"

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _bot_auth_headers() -> dict:
    # Raises KeyError if DISCORD_TOKEN is unset — callers run after load_dotenv(), so a missing
    # token is a config error that should surface loudly rather than send unauthenticated requests.
    return {"Authorization": f"Bot {os.environ['DISCORD_TOKEN']}"}


def is_image(att: dict) -> bool:
    if (att.get("content_type") or "").startswith("image/"):
        return True
    url_path = (att.get("url") or "").split("?")[0].lower()
    return any(url_path.endswith(ext) for ext in _IMAGE_EXTENSIONS)
