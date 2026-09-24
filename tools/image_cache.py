import json
import logging
import os
import threading
import urllib.parse

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image_cache.json")
_CACHE_LOCK = threading.Lock()


def _normalize_url(url: str) -> str:
    """Strip query params so Discord CDN signed URLs cache-hit across signature rotations."""
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _load() -> dict:
    # Simple unconditional disk read — the file is tiny so per-operation reads are acceptable.
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("image_cache: failed to load cache: %s", exc)
    return {}


def _save(cache: dict) -> None:
    try:
        with open(_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as exc:
        logger.warning("image_cache: failed to save cache: %s", exc)


def get_cached(url: str) -> str | None:
    key = _normalize_url(url)
    return _load().get(key)


def set_cached(url: str, result: str) -> None:
    key = _normalize_url(url)
    with _CACHE_LOCK:
        cache = _load()
        cache[key] = result
        _save(cache)
