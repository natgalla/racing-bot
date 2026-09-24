from smolagents import tool


@tool
def calculate_handicap_settings(
    base_weight_lbs: float,
    base_power_hp: float,
    weight_change_pct: float,
    power_change_pct: float,
) -> str:
    """Calculate final BOP settings after applying handicap adjustments. Always call this instead of doing the math yourself. Look up the driver's +/- total from the standings image in the adjustment table extracted from the handicap package pins to get the weight_change_pct and power_change_pct values.

    Args:
        base_weight_lbs: The car's canonical base weight in lbs from the race spec.
        base_power_hp: The car's canonical base power in hp from the race spec.
        weight_change_pct: Weight adjustment as a signed percentage. Positive = add weight (downgrade), negative = remove weight (upgrade). E.g. 4.0 for +4%, -4.0 for -4%.
        power_change_pct: Power adjustment as a signed percentage. Positive = add power (upgrade), negative = reduce power (downgrade). E.g. -2.0 for -2%, 2.0 for +2%.
    """
    final_weight_lbs = round(base_weight_lbs * (1 + weight_change_pct / 100))
    final_weight_kg = round(final_weight_lbs / 2.205)
    final_power_hp = round(base_power_hp * (1 + power_change_pct / 100))
    final_power_ps = round(final_power_hp * 1.01387)
    return (
        f"Weight: {final_weight_lbs} lbs ({final_weight_kg} kg) | "
        f"Power: {final_power_hp} hp ({final_power_ps} PS)"
    )
