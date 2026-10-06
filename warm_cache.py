#!/usr/bin/env python3
"""Pre-warm image_cache.json by fetching all image attachments from handicap channel pins.

Run via cron before race nights so get_image_text returns instantly during agent runs:

    0 17 * * 3 cd /home/pi/racing-bot && python3 warm_cache.py >> /home/pi/warm_cache.log 2>&1
"""
import logging
import os
import requests
from dotenv import load_dotenv

from tools.attachments import DISCORD_API, _bot_auth_headers, is_image

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger(__name__)


def fetch_pin_image_urls(channel_id: str, max_pins: int = 5) -> list[str]:
    resp = requests.get(f"{DISCORD_API}/channels/{channel_id}/pins", headers=_bot_auth_headers(), timeout=15)
    resp.raise_for_status()
    pins = resp.json()[:max_pins]
    urls = []
    for pin in pins:
        for att in pin.get("attachments", []):
            if is_image(att) and att.get("url"):
                urls.append(att["url"])
    return urls


def warm(channel_id: str) -> None:
    from tools.image_cache import extract_and_cache, get_cached
    from huggingface_hub import InferenceClient

    logger.info("fetching pins from channel %s (max 5)", channel_id)
    urls = fetch_pin_image_urls(channel_id, max_pins=5)
    if not urls:
        logger.info("no image attachments found in pins")
        return

    logger.info("found %d image(s) in pins", len(urls))
    client = InferenceClient(token=os.environ.get("HF_TOKEN"))

    for url in urls:
        if get_cached(url) is not None:
            logger.info("cache hit — skipping %s", url)
            continue
        logger.info("warming %s", url)
        try:
            result = extract_and_cache(client, url)
            if result:
                logger.info("cached %d chars for %s", len(result), url)
            else:
                logger.warning("empty result for %s", url)
        except Exception as exc:
            logger.error("failed to warm %s: %s", url, exc)


HANDICAP_CHANNEL_ID = "1113237975262834769"


def warm_pins() -> None:
    from tools.discord_tools import get_channel_pins
    from tools.pin_cache import get_cached_pins

    if get_cached_pins(HANDICAP_CHANNEL_ID) is not None:
        logger.info("pin cache hit — skipping %s", HANDICAP_CHANNEL_ID)
        return
    logger.info("warming pin cache for %s", HANDICAP_CHANNEL_ID)
    try:
        result = get_channel_pins(HANDICAP_CHANNEL_ID)
        logger.info("cached %d chars of pins for %s", len(result), HANDICAP_CHANNEL_ID)
    except Exception as exc:
        logger.error("failed to warm pins for %s: %s", HANDICAP_CHANNEL_ID, exc)


if __name__ == "__main__":
    warm(HANDICAP_CHANNEL_ID)
    warm_pins()
    logger.info("done")
