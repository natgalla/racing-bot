import json
import logging
import os
import tempfile
import threading
import urllib.parse

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image_cache.json")
_CACHE_LOCK = threading.Lock()


def _normalize_url(url: str) -> str:
    """Strip query params so Discord CDN signed URLs cache-hit across signature rotations.

    Assumption: each standings image is a unique upload, so stripping query params
    (e.g. CDN signature tokens) will never cause a stale hit for different content
    at the same path. This is an accepted tradeoff for the current use case.
    """
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _load() -> dict:
    # Simple unconditional disk read -- the file is tiny so per-operation reads are acceptable.
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                return json.load(f)
        except Exception as exc:
            logger.exception("image_cache: failed to load cache")
    return {}


def _save(cache: dict) -> None:
    # Write to a temp file in the same directory then atomically replace, so a
    # concurrent read never sees a truncated or partial JSON payload.
    tmp_path = None
    try:
        cache_dir = os.path.dirname(_CACHE_PATH)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=cache_dir, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_path = tmp.name
            json.dump(cache, tmp, indent=2)
        os.replace(tmp_path, _CACHE_PATH)
    except Exception as exc:
        logger.exception("image_cache: failed to save cache")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                logger.debug("image_cache: failed to unlink temp file: %s", exc)


def get_cached(url: str) -> str | None:
    key = _normalize_url(url)
    with _CACHE_LOCK:
        return _load().get(key)


def set_cached(url: str, result: str) -> None:
    key = _normalize_url(url)
    with _CACHE_LOCK:
        cache = _load()
        cache[key] = result
        _save(cache)
