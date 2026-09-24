import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_LIST_CACHE_PATH = os.path.join(_REPO_ROOT, "gtdb_list_cache.json")
_DETAIL_CACHE_PATH = os.path.join(_REPO_ROOT, "gtdb_detail_cache.json")

_LIST_LOCK = threading.Lock()
_DETAIL_LOCK = threading.Lock()

_LIST_TTL_DAYS = 30
_DETAIL_TTL_DAYS = 30

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_GTDB_BASE = "https://gtdb.io"


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            logger.exception("gtdb_cache: failed to load %s", path)
    return {}


def _save_json(path: str, data: dict) -> None:
    # Write to a temp file in the same directory then atomically replace, so a
    # concurrent read never sees a truncated or partial JSON payload.
    tmp_path = None
    try:
        cache_dir = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=cache_dir, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        logger.exception("gtdb_cache: failed to save %s", path)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                logger.debug("gtdb_cache: failed to unlink temp file: %s", exc)


def _is_list_cache_fresh(data: dict) -> bool:
    fetched_at = data.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts < timedelta(days=_LIST_TTL_DAYS)
    except (ValueError, TypeError):
        return False


def _is_detail_entry_fresh(entry: dict) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return False
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts < timedelta(days=_DETAIL_TTL_DAYS)
    except (ValueError, TypeError):
        return False


def _scrape_list() -> list[dict]:
    url = f"{_GTDB_BASE}/gt7/all-cars/"
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    cars = []
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        link = row.select_one("a[href*='/gt7/car/']")
        if not link:
            continue
        href = link["href"]
        slug_match = re.search(r"/gt7/car/([^/]+)/?", href)
        if not slug_match:
            continue
        slug = slug_match.group(1)

        name = link.get_text(strip=True)

        # Make is the first font-light div in the first cell, before the car link
        make = ""
        first_cell = cells[0]
        make_div = first_cell.select_one("div.font-light")
        if make_div:
            make = make_div.get_text(strip=True)

        # PP is embedded in "PP 262.24" text inside rounded-full badge divs
        pp = None
        for el in row.select("div.rounded-full"):
            txt = el.get_text(strip=True)
            if txt.startswith("PP "):
                try:
                    pp = float(txt[3:].replace(",", ""))
                    break
                except ValueError:
                    continue

        # Acquisition source — font-light text-xs div in the second cell
        acquisition_source = ""
        price_cr = 0
        src_div = row.select_one("div.font-light.text-xs")
        if src_div:
            acquisition_source = src_div.get_text(strip=True)
        # Price is in "text-right grow tabular-nums text-gray-100" div (clean Cr. only text)
        price_div = row.select_one("div.tabular-nums.text-gray-100")
        if price_div:
            txt = price_div.get_text(strip=True)
            if txt.startswith("Cr."):
                price_str = re.sub(r"[^0-9]", "", txt)
                if price_str:
                    price_cr = int(price_str)

        # Tags are in shrink-0 divs in the last cell
        tags = [
            el.get_text(strip=True)
            for el in row.select("div.shrink-0")
            if el.get_text(strip=True).startswith("#")
        ]

        cars.append(
            {
                "name": name,
                "make": make,
                "slug": slug,
                "pp": pp,
                "acquisition_source": acquisition_source,
                "price_cr": price_cr,
                "tags": tags,
            }
        )

    return cars


def _scrape_detail(slug: str) -> dict:
    url = f"{_GTDB_BASE}/gt7/car/{slug}/"
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    entry: dict = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "slug": slug,
    }

    # Make is in a text-xl font-light div above the h1
    make_el = soup.select_one("div.text-xl.font-light")
    if make_el:
        entry["make"] = make_el.get_text(strip=True)

    h1 = soup.select_one("h1")
    if h1:
        entry["name"] = h1.get_text(strip=True)

    # PP and group are in a single rounded-full badge: "Gr.N / PP 465.26"
    for badge in soup.select("div.rounded-full"):
        txt = badge.get_text(strip=True)
        if "PP " in txt:
            pp_match = re.search(r"PP\s+([\d.]+)", txt)
            if pp_match:
                try:
                    entry["pp"] = float(pp_match.group(1))
                except ValueError:
                    pass
            group_match = re.match(r"(Gr\.\w+)", txt)
            if group_match:
                entry["group"] = group_match.group(1)
            break

    # Specs from the dl inside the shadow rounded-lg card
    dl = soup.select_one("div.shadow.rounded-lg dl")
    if dl:
        for row_div in dl.select("div.sm\\:grid"):
            dt = row_div.select_one("dt")
            dd = row_div.select_one("dd")
            if not dt or not dd:
                continue
            label = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)
            if "displacement" in label:
                entry["displacement_cc"] = value
            elif "drivetrain" in label:
                entry["drivetrain"] = value
            elif "power" in label:
                entry["power"] = value
            elif "torque" in label:
                entry["torque"] = value
            elif "weight" in label:
                weight_str = re.sub(r"[^0-9]", "", value.split("k")[0] if "k" in value.lower() else value)
                if weight_str:
                    entry["weight_kg"] = int(weight_str)
            elif "aspiration" in label:
                entry["aspiration"] = value
            elif "length" in label:
                entry["length"] = value
            elif "width" in label:
                entry["width"] = value
            elif "height" in label:
                entry["height"] = value

    # Tags are font-light text-sm divs starting with #
    entry["tags"] = [
        el.get_text(strip=True)
        for el in soup.select("div.font-light.text-sm")
        if el.get_text(strip=True).startswith("#")
    ]

    # Specs that say "NaN" are missing data on gtdb — treat as absent
    for k in ("displacement_cc", "power", "torque", "aspiration"):
        if "NaN" in entry.get(k, ""):
            del entry[k]

    # Acquisition note is the font-light paragraph under the "How to acquire" heading
    entry["acquisition_source"] = ""
    entry["price_cr"] = 0
    entry["acquisition_note"] = ""

    acq_note_el = None
    for el in soup.select("div.max-w-lg.mx-auto.py-4.font-light"):
        heading = el.find_previous(class_="text-lg")
        if heading and "acquire" in heading.get_text(strip=True).lower():
            acq_note_el = el
            break

    if acq_note_el:
        acq_text = acq_note_el.get_text(strip=True)
        entry["acquisition_note"] = acq_text
        for src in ("Used Cars", "Brand Central", "Legend Cars", "Hagerty"):
            if src in acq_text:
                entry["acquisition_source"] = src
                break
        price_match = re.search(r"Cr\.\s*([\d,]+)", acq_text)
        if price_match:
            entry["price_cr"] = int(price_match.group(1).replace(",", ""))

    if not entry["acquisition_source"]:
        page_text = soup.get_text()
        if re.search(r"prize|gift|menu book reward|not purchasable", page_text, re.IGNORECASE):
            entry["acquisition_note"] = "Prize/Gift car (not purchasable)"

    return entry


def get_list_cache() -> list[dict]:
    with _LIST_LOCK:
        data = _load_json(_LIST_CACHE_PATH)
        if _is_list_cache_fresh(data):
            return data.get("cars", [])
        cars = _scrape_list()
        _save_json(
            _LIST_CACHE_PATH,
            {
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cars": cars,
            },
        )
        return cars


def get_detail(slug: str) -> dict:
    with _DETAIL_LOCK:
        data = _load_json(_DETAIL_CACHE_PATH)
        entry = data.get(slug)
        if entry and _is_detail_entry_fresh(entry):
            return entry
        entry = _scrape_detail(slug)
        data[slug] = entry
        _save_json(_DETAIL_CACHE_PATH, data)
        return entry


def force_refresh_list() -> None:
    with _LIST_LOCK:
        cars = _scrape_list()
        _save_json(
            _LIST_CACHE_PATH,
            {
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "cars": cars,
            },
        )
