import json
import logging

from rapidfuzz import fuzz, process
from smolagents import tool

from . import gtdb_cache

logger = logging.getLogger(__name__)


def _format_detail(detail: dict) -> str:
    name = detail.get("name", detail.get("slug", "Unknown"))
    make = detail.get("make", "")
    display_name = f"{make} {name}".strip() if make and make not in name else name

    pp = detail.get("pp")
    group = detail.get("group", "N/A")
    drivetrain = detail.get("drivetrain", "N/A")
    aspiration = detail.get("aspiration", "N/A")
    power = detail.get("power", "N/A")
    torque = detail.get("torque", "N/A")

    weight_kg = detail.get("weight_kg")
    weight_str = f"{weight_kg:,} kg" if weight_kg else "N/A"

    displacement = detail.get("displacement_cc", "N/A")

    tags = detail.get("tags", [])
    tags_str = ", ".join(tags) if tags else "N/A"

    source = detail.get("acquisition_source", "")
    price_cr = detail.get("price_cr", 0)
    note = detail.get("acquisition_note", "")

    if price_cr:
        acquisition_str = f"{source} — Cr. {price_cr:,}"
    elif source:
        acquisition_str = source
    else:
        acquisition_str = "N/A"

    lines = [
        display_name,
        f"PP: {pp} | Group: {group} | Drivetrain: {drivetrain} | Aspiration: {aspiration}",
        f"Power: {power} | Torque: {torque}",
        f"Weight: {weight_str} | Displacement: {displacement}",
        f"Tags: {tags_str}",
        f"Acquisition: {acquisition_str}",
    ]
    if note:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def _parse_power_bhp(power_str: str) -> int | None:
    """Extract the BHP figure from a power string like '203 BHP / 6000 rpm'."""
    import re
    m = re.search(r"(\d+)\s*BHP", power_str, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


@tool
def get_car_specs(car_name: str) -> str:
    """Return full specs and acquisition info for a Gran Turismo 7 car by name. Call this whenever a user asks about a specific car's stats, performance points, drivetrain, power, weight, group class, or how to acquire it in GT7. Prefers this over web_search for GT7 car data.

    Args:
        car_name: The name of the car to look up, e.g. "180SX Type X '96" or "Nissan 180SX".
            Fuzzy matching is applied so partial names and minor typos are tolerated.
    """
    cars = gtdb_cache.get_list_cache()
    if not cars:
        return "Car database is unavailable right now. Try again later or use web_search."

    names = [c["name"] for c in cars]

    # Pass 1 — token_set_ratio handles word-order mismatches (e.g. "GR Supra RZ" vs "GR Supra RZ '20")
    result = process.extractOne(car_name, names, scorer=fuzz.token_set_ratio, score_cutoff=60)
    if result:
        matched_name, score, idx = result
        car = cars[idx]
        try:
            detail = gtdb_cache.get_detail(car["slug"])
            return _format_detail(detail)
        except Exception as exc:
            logger.error("get_car_specs: detail fetch failed for %s: %s", car["slug"], exc)
            return f"Found a match ({matched_name}) but could not load full specs. Try again later."

    # Pass 2 — substring scan, return all matches sorted by PP descending
    lower_query = car_name.lower()
    substring_matches = [c for c in cars if lower_query in c["name"].lower()]
    if substring_matches:
        if len(substring_matches) == 1:
            car = substring_matches[0]
            try:
                detail = gtdb_cache.get_detail(car["slug"])
                return _format_detail(detail)
            except Exception as exc:
                logger.error("get_car_specs: detail fetch failed for %s: %s", car["slug"], exc)
                return f"Found a match ({car['name']}) but could not load full specs. Try again later."
        # Multiple substring matches — list them for the user to narrow down
        sorted_matches = sorted(substring_matches, key=lambda c: c.get("pp") or 0, reverse=True)
        listing = "\n".join(
            f"  {c['name']} (PP: {c['pp']})" for c in sorted_matches[:10]
        )
        return f"Multiple cars match '{car_name}'. Please be more specific:\n{listing}"

    # Pass 3 — match against make field alone
    make_matches = [c for c in cars if lower_query in (c.get("make") or "").lower()]
    if make_matches:
        sorted_matches = sorted(make_matches, key=lambda c: c.get("pp") or 0, reverse=True)
        listing = "\n".join(
            f"  {c['name']} (PP: {c['pp']})" for c in sorted_matches[:10]
        )
        return f"No exact car found for '{car_name}', but these cars match that make:\n{listing}"

    # No match — show closest guesses via fuzzy
    guesses = process.extract(car_name, names, scorer=fuzz.WRatio, limit=3)
    if guesses:
        guess_list = ", ".join(f"'{g[0]}'" for g in guesses)
        return f"No car found matching '{car_name}'. Did you mean one of: {guess_list}?"
    return f"No car found matching '{car_name}'. Use search_cars with filters to browse available cars."


@tool
def search_cars(filters: str) -> str:
    """Search Gran Turismo 7 cars by performance and spec filters. Call this when a user wants to find cars within a PP range, by drivetrain layout, weight, power, group class, or tag category. Returns a list of matching cars with key stats.

    Args:
        filters: A JSON string containing one or more filter keys. All keys are optional.
            Supported keys:
              pp_min (float) — minimum Performance Points, e.g. 450.0
              pp_max (float) — maximum Performance Points, e.g. 500.0
              weight_max (int, kg) — maximum car weight in kilograms, e.g. 1200
              power_min (int, BHP) — minimum power output in BHP, e.g. 300
              drivetrain (str) — layout code: "FR", "MR", "FF", or "4WD"
              tags (list of str) — one or more tag strings the car must have, e.g. ["#Road Car"]
              group (str) — race group: "Gr.1", "Gr.2", "Gr.3", "Gr.4", "Gr.B", "Gr.N", or "Gr.X".
                IMPORTANT: group, drivetrain, weight_max, and power_min are detail-level filters and
                require fetching individual car pages. They only work when the list-level filters
                (pp_min, pp_max, tags) first narrow the results to 50 cars or fewer. Always pair
                group or drivetrain with a tight pp range (span of 50 PP or less). For group queries,
                also add tags=["#Racing Car"] to filter at the list level first.
                Example for Gr.4 cars: pp_min=620, pp_max=670, tags=["#Racing Car"], group="Gr.4".

            Example: '{"pp_min": 450, "pp_max": 500, "drivetrain": "FR", "tags": ["#Road Car"]}'
    """
    try:
        f = json.loads(filters)
    except json.JSONDecodeError as exc:
        return f"Invalid filters JSON: {exc}. Pass a valid JSON string, e.g. '{{\"pp_min\": 450, \"pp_max\": 500}}'."

    cars = gtdb_cache.get_list_cache()
    if not cars:
        return "Car database is unavailable right now. Try again later or use web_search."

    pp_min = f.get("pp_min")
    pp_max = f.get("pp_max")
    required_tags = f.get("tags", [])
    detail_filters = {
        k: f[k] for k in ("weight_max", "power_min", "drivetrain", "group") if k in f
    }

    # Apply list-level filters first — no network needed
    survivors = []
    for car in cars:
        pp = car.get("pp")
        if pp_min is not None and (pp is None or pp < pp_min):
            continue
        if pp_max is not None and (pp is None or pp > pp_max):
            continue
        if required_tags:
            car_tags = car.get("tags", [])
            if not all(t in car_tags for t in required_tags):
                continue
        survivors.append(car)

    if not survivors:
        return "No cars match those filters. Try widening the PP range or removing some filters."

    # Guard against fetching detail for too many cars
    if detail_filters and len(survivors) > 50:
        return (
            f"Too many cars match the list-level filters ({len(survivors)} results). "
            "Please narrow down with tighter pp_min/pp_max or tags before adding weight_max, power_min, drivetrain, or group filters."
        )

    if detail_filters:
        refined = []
        for car in survivors:
            try:
                detail = gtdb_cache.get_detail(car["slug"])
            except Exception as exc:
                logger.warning("search_cars: could not fetch detail for %s: %s", car["slug"], exc)
                continue

            if "weight_max" in detail_filters:
                w = detail.get("weight_kg")
                if w is None or w > detail_filters["weight_max"]:
                    continue

            if "power_min" in detail_filters:
                power_str = detail.get("power", "")
                bhp = _parse_power_bhp(power_str)
                if bhp is None or bhp < detail_filters["power_min"]:
                    continue

            if "drivetrain" in detail_filters:
                if detail.get("drivetrain", "").upper() != detail_filters["drivetrain"].upper():
                    continue

            if "group" in detail_filters:
                if detail.get("group", "") != detail_filters["group"]:
                    continue

            refined.append((car, detail))

        if not refined:
            return "No cars match all those filters. Try relaxing weight_max, power_min, drivetrain, or group."

        total = len(refined)
        capped = refined[:30]
        lines = []
        for car, detail in capped:
            name = detail.get("name") or car["name"]
            make = detail.get("make") or car.get("make", "")
            display = f"{make} {name}".strip() if make and make not in name else name
            pp = car.get("pp", "N/A")
            drv = detail.get("drivetrain", "N/A")
            w = detail.get("weight_kg")
            weight_str = f"{w:,} kg" if w else "N/A"
            tags = ", ".join(car.get("tags", [])) or "N/A"
            lines.append(f"{display} | PP: {pp} | Drivetrain: {drv} | Weight: {weight_str} | Tags: {tags}")

        result = "\n".join(lines)
        if total > 30:
            result += f"\n(showing 30 of {total} — add filters to narrow down)"
        return result

    # List-level results only
    total = len(survivors)
    capped = survivors[:30]
    lines = []
    for car in capped:
        name = car["name"]
        make = car.get("make", "")
        display = f"{make} {name}".strip() if make and make not in name else name
        pp = car.get("pp", "N/A")
        tags = ", ".join(car.get("tags", [])) or "N/A"
        lines.append(f"{display} | PP: {pp} | Tags: {tags}")

    result = "\n".join(lines)
    if total > 30:
        result += f"\n(showing 30 of {total} — add filters to narrow down)"
    return result
