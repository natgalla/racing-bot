#!/usr/bin/env python3
"""Pre-warm image_cache.json by fetching all image attachments from handicap channel pins.

Run via cron before race nights so read_image_content returns instantly during agent runs:

    0 17 * * 3 cd /home/pi/racing-bot && python3 warm_cache.py >> /home/pi/warm_cache.log 2>&1
"""
import logging
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _headers():
    return {"Authorization": f"Bot {os.environ['DISCORD_TOKEN']}"}


def _is_image(att: dict) -> bool:
    if (att.get("content_type") or "").startswith("image/"):
        return True
    url_path = (att.get("url") or "").split("?")[0].lower()
    return any(url_path.endswith(ext) for ext in _IMAGE_EXTENSIONS)


def fetch_pin_image_urls(channel_id: str) -> list[str]:
    resp = requests.get(f"{DISCORD_API}/channels/{channel_id}/pins", headers=_headers(), timeout=15)
    resp.raise_for_status()
    pins = resp.json()
    urls = []
    for pin in pins:
        for att in pin.get("attachments", []):
            if _is_image(att) and att.get("url"):
                urls.append(att["url"])
    return urls


def warm(channel_id: str) -> None:
    from tools.image_cache import get_cached, set_cached
    from huggingface_hub import InferenceClient

    logger.info("fetching pins from channel %s", channel_id)
    urls = fetch_pin_image_urls(channel_id)
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
            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-VL-7B-Instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": url}},
                            {
                                "type": "text",
                                "text": "Extract all text and table data from this image exactly as shown. Preserve table structure as a text table. Do not summarise or interpret — transcribe verbatim.",
                            },
                        ],
                    }
                ],
                max_tokens=1500,
            )
            result = response.choices[0].message.content or ""
            if result:
                set_cached(url, result)
                logger.info("cached %d chars for %s", len(result), url)
            else:
                logger.warning("empty result for %s", url)
        except Exception as exc:
            logger.error("failed to warm %s: %s", url, exc)


if __name__ == "__main__":
    channel_id = os.environ.get("HANDICAP_CHANNEL_ID", "").strip()
    if not channel_id:
        logger.error("HANDICAP_CHANNEL_ID not set in .env")
        sys.exit(1)
    warm(channel_id)
    logger.info("done")
