import json
import logging
import os
import threading
import urllib.parse

from .file_utils import atomic_write_json

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image_cache.json")
_CACHE_LOCK = threading.Lock()

# In-memory copy of the on-disk cache. Loaded lazily on first access and kept in
# sync on every set_cached write, so disk is read at most once per process.
_CACHE: dict = {}
_CACHE_LOADED: bool = False

# Per-URL in-flight dedup: the first caller for a URL creates an Event and extracts;
# concurrent callers for the same URL wait on it rather than both hitting the network.
_in_flight: dict[str, threading.Event] = {}


_EXTRACT_PROMPT = (
    "Extract all text and table data from this image exactly as shown. "
    "Preserve table structure as a text table. "
    "Do not summarise or interpret — transcribe verbatim."
)


def _extract_image_text(client, url: str) -> str:
    """Run the gemma-3 vision model against an image URL and return the transcribed text."""
    response = client.chat.completions.create(
        model="google/gemma-3-27b-it",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": _EXTRACT_PROMPT},
                ],
            }
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content or ""


def _normalize_url(url: str) -> str:
    """Strip query params so Discord CDN signed URLs cache-hit across signature rotations.

    Assumption: each standings image is a unique upload, so stripping query params
    (e.g. CDN signature tokens) will never cause a stale hit for different content
    at the same path. This is an accepted tradeoff for the current use case.
    """
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _load() -> dict:
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                return json.load(f)
        except Exception:
            # Name the file explicitly so a corrupt cache is traceable rather than silently empty.
            logger.exception("image_cache: failed to load cache from %s", _CACHE_PATH)
    return {}


def _ensure_loaded() -> None:
    # Caller must hold _CACHE_LOCK.
    global _CACHE_LOADED
    if not _CACHE_LOADED:
        _CACHE.update(_load())
        _CACHE_LOADED = True


def _save() -> None:
    atomic_write_json(_CACHE_PATH, _CACHE)


def get_cached(url: str) -> str | None:
    key = _normalize_url(url)
    with _CACHE_LOCK:
        _ensure_loaded()
        return _CACHE.get(key)


def set_cached(url: str, result: str) -> None:
    key = _normalize_url(url)
    with _CACHE_LOCK:
        _ensure_loaded()
        _CACHE[key] = result
        _save()


def extract_and_cache(client, url: str) -> str:
    """Return the extracted text for an image URL, extracting at most once per URL.

    Holds the lock across the read-check-write so a second caller that arrives after the
    first finishes sees the cache hit. For a URL already mid-extraction by another caller,
    the second caller waits on the in-flight Event rather than hitting the network again.
    """
    key = _normalize_url(url)
    while True:
        with _CACHE_LOCK:
            _ensure_loaded()
            cached = _CACHE.get(key)
            if cached is not None:
                return cached
            event = _in_flight.get(key)
            if event is None:
                # We own the extraction for this URL.
                event = threading.Event()
                _in_flight[key] = event
                break
        # Another caller is extracting this URL — wait, then re-check the cache.
        event.wait()

    try:
        result = _extract_image_text(client, url)
        if result:
            with _CACHE_LOCK:
                _CACHE[key] = result
                _save()
        return result
    finally:
        with _CACHE_LOCK:
            _in_flight.pop(key, None)
            event.set()
