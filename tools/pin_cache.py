import logging
import os
import threading
from datetime import datetime, timezone, timedelta

from .file_utils import atomic_write_json, load_json

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_CACHE_PATH = os.path.join(_REPO_ROOT, "pin_cache.json")

_LOCK = threading.Lock()

_CACHE_TTL_HOURS = 8


def _is_entry_fresh(entry: dict) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ts < timedelta(hours=_CACHE_TTL_HOURS)
    except (ValueError, TypeError):
        return False


def get_cached_pins(channel_id: str) -> str | None:
    with _LOCK:
        data = load_json(_CACHE_PATH, logger)
        entry = data.get(channel_id)
        if entry and _is_entry_fresh(entry):
            return entry.get("content")
        return None


def set_cached_pins(channel_id: str, content: str) -> None:
    with _LOCK:
        data = load_json(_CACHE_PATH, logger)
        data[channel_id] = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }
        atomic_write_json(_CACHE_PATH, data)
