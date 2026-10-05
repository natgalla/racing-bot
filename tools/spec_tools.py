import logging

from smolagents import tool

from . import gtdb_cache, tuning_cache

logger = logging.getLogger(__name__)

_LBS_PER_KG = 0.453592


@tool
def find_cars_for_spec(
    target_power_bhp: int = 0,
    target_weight_lbs: int = 0,
    target_weight_kg: int = 0,
    year_min: int = 0,
    year_max: int = 0,
    drivetrain: str = "",
    make: str = "",
    tags: str = "",
) -> str:
    """Find Gran Turismo 7 cars that can be tuned to reach a power and/or weight target.

    Use this when the spec defines a power and/or weight target that cars must be tunable to reach,
    e.g. "500hp/3500lbs", "300bhp 1200kg", "at least 400hp", "cars that can hit 400hp". It checks
    each car's maximum tunable power (no engine swap) and minimum achievable weight against the target.

    Use search_cars instead for stock stat filters (PP range, group class, tag browsing) — search_cars
    does not account for tuning range.

    Args:
        target_power_bhp: Minimum tunable power in BHP the car must be able to reach. 0 means not specified.
        target_weight_lbs: Maximum achievable weight in pounds. 0 means not specified. Mutually exclusive
            with target_weight_kg; if both are provided, lbs takes precedence.
        target_weight_kg: Maximum achievable weight in kilograms. 0 means not specified.
        year_min: Earliest model year (inclusive). 0 means not specified.
        year_max: Latest model year (inclusive). 0 means not specified.
        drivetrain: Drivetrain layout to require: one of "FR", "FF", "MR", "4WD". Empty means not specified.
        make: Case-insensitive substring match on the car's make, e.g. "Nissan". Empty means not specified.
        tags: Comma-separated GTDB tag strings the car must all have, e.g. "#Road Car,#Midship".
            Empty means not specified.
    """
    weight_target_kg = 0
    if target_weight_lbs > 0:
        weight_target_kg = round(target_weight_lbs * _LBS_PER_KG)
    elif target_weight_kg > 0:
        weight_target_kg = target_weight_kg

    cars = gtdb_cache.get_list_cache()
    if not cars:
        return "Car database is unavailable right now. Try again later or use web_search."

    required_tags = [t.strip() for t in tags.split(",") if t.strip()]
    make_lower = make.strip().lower()

    survivors = []
    for car in cars:
        year = car.get("year")
        if year_min > 0:
            if year is None or year < year_min:
                continue
        if year_max > 0:
            if year is None or year > year_max:
                continue
        if make_lower and make_lower not in (car.get("make") or "").lower():
            continue
        if required_tags:
            car_tags = car.get("tags", [])
            if not all(t in car_tags for t in required_tags):
                continue
        survivors.append(car)

    matched = []
    for car in survivors:
        tuning = tuning_cache.get_tuning(car["slug"])
        if target_power_bhp > 0:
            if not tuning or tuning.get("max_power_bhp") is None:
                continue
            if tuning["max_power_bhp"] < target_power_bhp:
                continue
        if weight_target_kg > 0:
            if not tuning or tuning.get("min_weight_kg") is None:
                continue
            if tuning["min_weight_kg"] > weight_target_kg:
                continue
        if tuning is None:
            continue
        matched.append((car, tuning))

    drivetrain_fetched = bool(drivetrain.strip())
    if drivetrain_fetched:
        if len(matched) > 50:
            return (
                f"Too many cars match the power/weight/year/make/tag filters ({len(matched)} results) "
                "to also filter by drivetrain. Please narrow down with power, weight, year, make, or tags first."
            )
        dt = drivetrain.strip().upper()
        refined = []
        for car, tuning in matched:
            try:
                detail = gtdb_cache.get_detail(car["slug"])
            except Exception as exc:
                logger.warning("find_cars_for_spec: could not fetch detail for %s: %s", car["slug"], exc)
                continue
            if detail.get("drivetrain", "").upper() != dt:
                continue
            refined.append((car, tuning, detail))
        matched = refined

    if not matched:
        return (
            "No cars match that spec. Try relaxing the power or weight target, widening the year range, "
            "or removing the make, tag, or drivetrain filters."
        )

    total = len(matched)
    capped = matched[:30]
    lines = []
    for entry in capped:
        if drivetrain_fetched:
            car, tuning, detail = entry
        else:
            car, tuning = entry
            detail = None

        name = car["name"]
        car_make = car.get("make", "")
        display = f"{car_make} {name}".strip() if car_make and car_make not in name else name
        year = car.get("year")
        if year:
            display = f"{display} ({year})"

        max_power = tuning.get("max_power_bhp")
        min_weight_kg = tuning.get("min_weight_kg")
        stock_weight_kg = tuning.get("stock_weight_kg")
        stock_power = tuning.get("stock_power_bhp")

        max_str = f"{max_power} BHP" if max_power is not None else "N/A BHP"
        if min_weight_kg is not None:
            min_lbs = round(min_weight_kg / _LBS_PER_KG)
            min_str = f"{min_weight_kg:,} kg ({min_lbs:,} lbs)"
        else:
            min_str = "N/A"

        parts = [display, f"Max: {max_str} / Min: {min_str}"]

        stock_bits = []
        if stock_power is not None:
            stock_bits.append(f"{stock_power} BHP")
        if stock_weight_kg is not None:
            stock_bits.append(f"{stock_weight_kg:,} kg")
        if stock_bits:
            parts.append("Stock: " + " / ".join(stock_bits))

        if drivetrain_fetched and detail is not None:
            drv = detail.get("drivetrain", "")
            if drv:
                parts.append(drv)

        lines.append(" | ".join(parts))

    result = "\n".join(lines)
    if total > 30:
        result += f"\n(showing 30 of {total} — add filters to narrow down)"
    return result
