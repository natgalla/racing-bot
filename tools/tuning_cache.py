import csv
import io
import json
import logging
import os
import threading
from datetime import datetime, timezone, timedelta

import requests
from rapidfuzz import fuzz, process

from . import gtdb_cache
from .file_utils import atomic_write_json, load_json

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_CACHE_PATH = os.path.join(_REPO_ROOT, "gtplanet_tuning_cache.json")

_LOCK = threading.Lock()

_CACHE_TTL_DAYS = 30

_MATCH_THRESHOLD = 85

_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1XI_NeWovuYThKGf9nsqomwpUy_MCiheevohBmErvdHE/gviz/tq?tqx=out:csv&sheet=0"
)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_NAME_COL = "GT7 Max Tuning Database\nBy HRC Rolls (hyperspeed980)"
_MAX_POWER_COL = "Max. Horsepower (no special parts)"
_MIN_WEIGHT_COL = "Min. Weight"
_STOCK_WEIGHT_COL = "Stock Weight (kg)"
_STOCK_POWER_COL = "Stock Horsepower"


def _load_json(path: str) -> dict:
    return load_json(path, logger)


def _save_json(path: str, data: dict) -> None:
    atomic_write_json(path, data)


def _is_cache_fresh(data: dict) -> bool:
    fetched_at = data.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts < timedelta(days=_CACHE_TTL_DAYS)
    except (ValueError, TypeError):
        return False


def _parse_int(value: str) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    digits = cleaned.replace(",", "").replace(" ", "")
    try:
        return int(float(digits))
    except ValueError:
        return None


def _fetch_sheet_rows() -> list[dict]:
    resp = requests.get(_SHEET_URL, headers={"User-Agent": _USER_AGENT}, timeout=20)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def _build_cache() -> dict:
    rows = _fetch_sheet_rows()
    cars = gtdb_cache.get_list_cache()

    slug_by_choice = {}
    for car in cars:
        make = car.get("make", "")
        name = car.get("name", "")
        combined = f"{make} {name}".strip()
        if combined:
            slug_by_choice[combined] = car["slug"]
    choice_list = list(slug_by_choice.keys())

    by_slug = {}
    for row in rows:
        sheet_name = (row.get(_NAME_COL) or "").strip()
        if not sheet_name:
            continue
        match = process.extractOne(
            sheet_name,
            choice_list,
            scorer=fuzz.token_set_ratio,
            score_cutoff=_MATCH_THRESHOLD,
        )
        if not match:
            continue
        slug = slug_by_choice.get(match[0])
        if not slug or slug in by_slug:
            continue
        by_slug[slug] = {
            "max_power_bhp": _parse_int(row.get(_MAX_POWER_COL)),
            "min_weight_kg": _parse_int(row.get(_MIN_WEIGHT_COL)),
            "stock_weight_kg": _parse_int(row.get(_STOCK_WEIGHT_COL)),
            "stock_power_bhp": _parse_int(row.get(_STOCK_POWER_COL)),
        }

    data = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "by_slug": by_slug,
    }
    _save_json(_CACHE_PATH, data)
    logger.info("tuning_cache: built (%d cars matched)", len(by_slug))
    return data


def get_all_tuning() -> dict:
    """Return the full by_slug tuning dict, loading the cache once."""
    with _LOCK:
        data = _load_json(_CACHE_PATH)
        if not _is_cache_fresh(data):
            try:
                data = _build_cache()
            except Exception:
                logger.exception("tuning_cache: failed to build cache; using stale data")
        return data.get("by_slug", {})


def get_tuning(slug: str) -> dict | None:
    with _LOCK:
        data = _load_json(_CACHE_PATH)
        if not _is_cache_fresh(data):
            try:
                data = _build_cache()
            except Exception:
                logger.exception("tuning_cache: failed to build cache; using stale data")
        return data.get("by_slug", {}).get(slug)
