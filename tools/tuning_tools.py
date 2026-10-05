from smolagents import tool

PARAM_LABELS = {
    "compressionFront": "front compression damping",
    "compressionRear": "rear compression damping",
    "expansionFront": "front expansion damping",
    "expansionRear": "rear expansion damping",
    "natFreqFront": "front spring rate",
    "natFreqRear": "rear spring rate",
    "antiRollFront": "front anti-roll bar",
    "antiRollRear": "rear anti-roll bar",
    "camberFront": "front camber",
    "camberRear": "rear camber",
    "toeFront": "front toe",
    "toeRear": "rear toe",
    "bodyHeightFront": "front ride height",
    "bodyHeightRear": "rear ride height",
    "lsdInitFront": "front LSD initial torque",
    "lsdAccelFront": "front LSD accel",
    "lsdDecelFront": "front LSD decel",
    "lsdInitRear": "rear LSD initial torque",
    "lsdAccelRear": "rear LSD accel",
    "lsdDecelRear": "rear LSD decel",
    "torqueDistribution": "AWD torque distribution (front %)",
    "brakeBalance": "brake balance",
}

# Each rule: (symptom, phase, parameter, direction, speed, throttle, elevation, drivetrain)
# None in optional fields means "applies to all"
RULES = [
    # ── Understeer, Entry ──
    ("understeer", "entry", "compressionFront", "decrease", None, None, None, None),
    ("understeer", "entry", "toeFront", "decrease", None, None, None, None),
    ("understeer", "entry", "lsdDecelFront", "decrease", None, "braking", None, None),
    ("understeer", "entry", "bodyHeightFront", "decrease", "high", None, None, None),
    ("understeer", "entry", "bodyHeightRear", "increase", "high", None, None, None),

    # ── Understeer, Mid ──
    ("understeer", "mid", "antiRollFront", "decrease", None, None, None, None),
    ("understeer", "mid", "antiRollRear", "increase", None, None, None, None),
    ("understeer", "mid", "natFreqFront", "decrease", None, None, None, None),
    ("understeer", "mid", "natFreqRear", "increase", None, None, None, None),
    ("understeer", "mid", "camberFront", "increase", None, None, None, None),
    ("understeer", "mid", "bodyHeightFront", "decrease", "high", None, None, None),
    ("understeer", "mid", "bodyHeightRear", "increase", "high", None, None, None),
    ("understeer", "mid", "torqueDistribution", "decrease", None, None, None, None),
    ("understeer", "mid", "lsdInitRear", "decrease", None, None, None, None),
    ("understeer", "mid", "lsdInitFront", "decrease", None, None, None, "FF"),

    # ── Understeer, Exit ──
    ("understeer", "exit", "natFreqFront", "decrease", None, None, None, None),
    ("understeer", "exit", "natFreqRear", "increase", None, None, None, None),
    ("understeer", "exit", "lsdAccelRear", "decrease", None, "on-throttle", None, None),
    ("understeer", "exit", "antiRollFront", "decrease", None, "on-throttle", None, None),
    ("understeer", "exit", "antiRollRear", "increase", None, "on-throttle", None, None),
    ("understeer", "exit", "torqueDistribution", "decrease", None, "on-throttle", None, None),
    ("understeer", "exit", "lsdAccelFront", "decrease", None, "on-throttle", None, "FF"),
    ("understeer", "exit", "expansionFront", "increase", None, None, None, None),

    # ── Understeer, Elevation ──
    ("understeer", "entry", "bodyHeightFront", "decrease", None, None, "up", None),
    ("understeer", "mid", "camberFront", "increase", None, None, "up", None),
    ("understeer", "exit", "antiRollRear", "increase", None, None, "up", None),

    # ── Oversteer, Entry ──
    ("oversteer", "entry", "antiRollFront", "increase", None, None, None, None),
    ("oversteer", "entry", "antiRollRear", "decrease", None, None, None, None),
    ("oversteer", "entry", "toeRear", "increase", None, None, None, None),
    ("oversteer", "entry", "lsdDecelRear", "increase", None, "braking", None, None),
    ("oversteer", "entry", "expansionRear", "increase", None, "braking", None, None),
    ("oversteer", "entry", "lsdDecelFront", "increase", None, "braking", None, "FF"),
    ("oversteer", "entry", "bodyHeightRear", "decrease", None, None, "down", None),
    ("oversteer", "entry", "lsdInitRear", "increase", None, None, None, None),

    # ── Oversteer, Mid ──
    ("oversteer", "mid", "antiRollFront", "increase", None, None, None, None),
    ("oversteer", "mid", "antiRollRear", "decrease", None, None, None, None),
    ("oversteer", "mid", "natFreqFront", "increase", None, None, None, None),
    ("oversteer", "mid", "natFreqRear", "decrease", None, None, None, None),
    ("oversteer", "mid", "camberRear", "increase", None, None, None, None),
    ("oversteer", "mid", "bodyHeightFront", "increase", "high", None, None, None),
    ("oversteer", "mid", "bodyHeightRear", "decrease", "high", None, None, None),
    ("oversteer", "mid", "torqueDistribution", "increase", None, None, None, None),
    ("oversteer", "mid", "compressionFront", "increase", None, None, "down", None),
    ("oversteer", "mid", "lsdInitRear", "increase", None, None, None, None),
    ("oversteer", "mid", "lsdInitFront", "increase", None, None, None, "FF"),

    # ── Oversteer, Exit ──
    ("oversteer", "exit", "natFreqFront", "increase", None, None, None, None),
    ("oversteer", "exit", "natFreqRear", "decrease", None, None, None, None),
    ("oversteer", "exit", "toeRear", "increase", None, None, None, None),
    ("oversteer", "exit", "lsdAccelRear", "decrease", None, "on-throttle", None, None),
    ("oversteer", "exit", "bodyHeightFront", "increase", "high", None, None, None),
    ("oversteer", "exit", "bodyHeightRear", "decrease", "high", None, None, None),
    ("oversteer", "exit", "torqueDistribution", "increase", None, "on-throttle", None, None),
    ("oversteer", "exit", "toeRear", "increase", None, None, None, "MR"),
    ("oversteer", "exit", "lsdAccelFront", "decrease", None, "on-throttle", None, "FF"),
    ("oversteer", "exit", "lsdAccelRear", "increase", None, None, "up", None),
    ("oversteer", "exit", "expansionRear", "increase", None, None, "down", None),
    ("oversteer", "exit", "expansionFront", "decrease", None, None, None, None),

    # ── Snap Oversteer, Entry ──
    ("snap-oversteer", "entry", "expansionRear", "increase", None, None, None, None),
    ("snap-oversteer", "entry", "compressionFront", "decrease", None, None, None, None),
    ("snap-oversteer", "entry", "toeRear", "increase", None, None, None, None),
    ("snap-oversteer", "entry", "lsdDecelRear", "increase", None, "braking", None, None),
    ("snap-oversteer", "entry", "lsdDecelRear", "increase", None, "off-throttle", None, None),
    ("snap-oversteer", "entry", "compressionFront", "decrease", None, None, "down", None),
    ("snap-oversteer", "entry", "compressionRear", "increase", None, None, None, "MR"),
    ("snap-oversteer", "entry", "lsdDecelFront", "increase", None, "off-throttle", None, "FF"),
    ("snap-oversteer", "entry", "lsdDecelFront", "increase", None, "braking", None, "FF"),
    ("snap-oversteer", "entry", "lsdInitRear", "increase", None, None, None, None),
    ("snap-oversteer", "entry", "compressionRear", "increase", None, None, None, "RR"),

    # ── Snap Oversteer, Mid ──
    ("snap-oversteer", "mid", "expansionRear", "increase", None, None, None, None),
    ("snap-oversteer", "mid", "toeRear", "increase", None, None, None, None),
    ("snap-oversteer", "mid", "natFreqFront", "increase", None, None, None, None),
    ("snap-oversteer", "mid", "natFreqRear", "decrease", None, None, None, None),
    ("snap-oversteer", "mid", "camberRear", "increase", None, None, None, None),
    ("snap-oversteer", "mid", "natFreqRear", "decrease", None, None, None, "MR"),
    ("snap-oversteer", "mid", "bodyHeightRear", "decrease", None, None, "down", None),

    # ── Snap Oversteer, Exit ──
    ("snap-oversteer", "exit", "expansionRear", "increase", None, None, None, None),
    ("snap-oversteer", "exit", "toeRear", "increase", None, None, None, None),
    ("snap-oversteer", "exit", "lsdAccelRear", "decrease", None, "on-throttle", None, None),
    ("snap-oversteer", "exit", "torqueDistribution", "increase", None, "on-throttle", None, None),
    ("snap-oversteer", "exit", "lsdAccelRear", "decrease", None, "on-throttle", None, "RR"),

    # ── Instability, Entry ──
    ("instability", "entry", "toeRear", "increase", None, None, None, None),
    ("instability", "entry", "compressionRear", "increase", None, None, None, None),
    ("instability", "entry", "lsdDecelRear", "increase", None, "braking", None, None),
    ("instability", "entry", "expansionRear", "increase", None, None, "down", None),
    ("instability", "entry", "lsdInitRear", "increase", None, None, None, None),

    # ── Instability, Mid ──
    ("instability", "mid", "toeRear", "increase", None, None, None, None),
    ("instability", "mid", "antiRollFront", "decrease", None, None, None, None),
    ("instability", "mid", "antiRollRear", "increase", None, None, None, None),
    ("instability", "mid", "bodyHeightFront", "increase", "high", None, None, None),
    ("instability", "mid", "bodyHeightRear", "decrease", "high", None, None, None),
    ("instability", "mid", "expansionRear", "increase", "high", None, None, None),
    ("instability", "mid", "bodyHeightRear", "decrease", None, None, "down", None),

    # ── Instability, Exit ──
    ("instability", "exit", "toeRear", "increase", None, None, None, None),
    ("instability", "exit", "expansionRear", "increase", None, None, None, None),
    ("instability", "exit", "lsdAccelRear", "increase", None, "on-throttle", None, None),
    ("instability", "exit", "lsdAccelFront", "increase", None, "on-throttle", None, "FF"),
    ("instability", "exit", "torqueDistribution", "increase", None, "on-throttle", None, None),
    ("instability", "exit", "lsdInitRear", "increase", None, None, None, None),

    # ── Brake Balance, Entry (braking) ──
    # Drivetrain-specific rules that duplicate the general None rule have been removed:
    # the general rule already covers FF/RR/MR/FR/4WD. Only keep the general rules.
    ("understeer", "entry", "brakeBalance", "increase", None, "braking", None, None),
    ("oversteer", "entry", "brakeBalance", "decrease", None, "braking", None, None),
    ("snap-oversteer", "entry", "brakeBalance", "decrease", None, "braking", None, None),
    ("instability", "entry", "brakeBalance", "decrease", None, "braking", None, None),
]


def _excluded_params(drivetrain: str) -> set:
    excluded = set()
    if drivetrain != "4WD":
        excluded.add("torqueDistribution")
    if drivetrain in ("FR", "MR", "RR"):
        excluded.update({"lsdAccelFront", "lsdDecelFront", "lsdInitFront"})
    if drivetrain == "FF":
        excluded.update({"lsdAccelRear", "lsdDecelRear", "lsdInitRear"})
    return excluded


def _score(rule, speed, throttle, elevation, drivetrain):
    _, _, _, _, r_speed, r_throttle, r_elevation, r_drivetrain = rule
    s = 0
    if r_speed and r_speed == speed:
        s += 1
    if r_throttle and r_throttle == throttle:
        s += 1
    if r_elevation and r_elevation == elevation:
        s += 1
    if r_drivetrain and r_drivetrain == drivetrain:
        s += 1
    return s


def _get_recommendations(symptom, phase, drivetrain, throttle, corner_speed, elevation):
    excluded = _excluded_params(drivetrain or "")

    def matches(rule):
        r_symptom, r_phase, r_param, _, r_speed, r_throttle, r_elevation, r_drivetrain = rule
        if r_symptom != symptom:
            return False
        if phase and r_phase != phase:
            return False
        if r_param in excluded:
            return False
        if r_speed and r_speed != corner_speed:
            return False
        if r_throttle and r_throttle != throttle:
            return False
        if r_elevation and r_elevation != elevation:
            return False
        if r_drivetrain and r_drivetrain != drivetrain:
            return False
        return True

    if phase:
        best = {}
        for rule in RULES:
            if not matches(rule):
                continue
            _, _, param, direction, *_ = rule
            s = _score(rule, corner_speed, throttle, elevation, drivetrain)
            existing = best.get(param)
            if existing is None or s > existing[1]:
                best[param] = (direction, s)
        return sorted(best.items(), key=lambda x: (-x[1][1], x[0]))
    else:
        # Any phase: keep only parameters with consistent direction across all phases
        seen = {}
        for rule in RULES:
            if not matches(rule):
                continue
            _, _, param, direction, *_ = rule
            s = _score(rule, corner_speed, throttle, elevation, drivetrain)
            if param not in seen:
                seen[param] = {"direction": direction, "score": s, "conflict": False}
            elif seen[param]["direction"] != direction:
                seen[param]["conflict"] = True
            elif s > seen[param]["score"]:
                seen[param]["score"] = s
        return [
            (param, (entry["direction"], entry["score"]))
            for param, entry in sorted(seen.items(), key=lambda x: (-x[1]["score"], x[0]))
            if not entry["conflict"]
        ]


@tool
def get_tuning_recommendations(
    symptom: str,
    drivetrain: str,
    phase: str = "",
    throttle: str = "",
    corner_speed: str = "",
    elevation: str = "",
) -> str:
    """Return ranked GT7 suspension tuning recommendations for a described handling symptom.
    Always call this when a driver describes a handling problem — do not guess parameter adjustments.

    Args:
        symptom: The handling problem. One of: understeer, oversteer, snap-oversteer, instability.
        drivetrain: The car's drivetrain layout. One of: FR, FF, MR, RR, 4WD.
        phase: Corner phase where the symptom occurs. One of: entry, mid, exit. Leave blank if it occurs throughout.
        throttle: Throttle state when the symptom occurs. One of: on-throttle, off-throttle, braking. Leave blank if unknown.
        corner_speed: Corner speed category. One of: low, medium, high. Leave blank if unknown.
        elevation: Track gradient at the problem corner. One of: up, down, neutral. Leave blank if unknown.
    """
    symptom = symptom.lower().strip()
    drivetrain = drivetrain.upper().strip()
    phase = phase.lower().strip() or None
    throttle = throttle.lower().strip() or None
    corner_speed = corner_speed.lower().strip() or None
    elevation = elevation.lower().strip() or None

    valid_symptoms = {"understeer", "oversteer", "snap-oversteer", "instability"}
    valid_drivetrains = {"FR", "FF", "MR", "RR", "4WD"}
    if symptom not in valid_symptoms:
        return f"Unknown symptom '{symptom}'. Use one of: {', '.join(sorted(valid_symptoms))}."
    if drivetrain not in valid_drivetrains:
        return f"Unknown drivetrain '{drivetrain}'. Use one of: {', '.join(sorted(valid_drivetrains))}."

    results = _get_recommendations(symptom, phase, drivetrain, throttle, corner_speed, elevation)

    if not results:
        return "No specific recommendations found for that combination. Try broadening the inputs (remove phase, throttle, or elevation)."

    scores = [score for _, (_, score) in results]
    all_same_score = len(set(scores)) == 1

    def fmt(param, direction):
        label = PARAM_LABELS.get(param, param)
        arrow = "▲ Increase" if direction == "increase" else "▼ Decrease"
        return f"{arrow} {label}"

    if all_same_score:
        lines = [fmt(param, direction) for param, (direction, _) in results]
    else:
        high = [fmt(p, d) for p, (d, s) in results if s >= 1]
        also = [fmt(p, d) for p, (d, s) in results if s == 0]
        lines = []
        if high:
            lines.append("High impact:")
            lines.extend(f"  {l}" for l in high)
        if also:
            lines.append("Also try:")
            lines.extend(f"  {l}" for l in also)

    context_parts = [f"symptom={symptom}", f"drivetrain={drivetrain}"]
    if phase:
        context_parts.append(f"phase={phase}")
    if throttle:
        context_parts.append(f"throttle={throttle}")
    if corner_speed:
        context_parts.append(f"corner_speed={corner_speed}")
    if elevation:
        context_parts.append(f"elevation={elevation}")

    header = f"Tuning recommendations ({', '.join(context_parts)}):\n"
    return header + "\n".join(lines)


BRAKE_BALANCE_BASELINES = {
    "RR": {
        "range": "-1 to -2",
        "reason": "Rear mass overloads rear wheels under braking, causing lockup and snap oversteer on entry. Front bias is essential.",
    },
    "MR": {
        "range": "0 to -1",
        "reason": "Near-balanced weight. Neutral to slight front bias prevents front lockup without destabilizing the rear.",
    },
    "FR": {
        "range": "+1 to +3",
        "reason": "Front-heavy layout. Rearward bias lets the rear tyres share braking load and improves rotation on entry.",
    },
    "FF": {
        "range": "+2 to +5",
        "reason": "Engine, drivetrain, and braking all load the front axle. Strong rear bias unloads the front so the tyres can steer under braking. Start at +3 and go higher if understeer persists.",
    },
    "4WD": {
        "range": "0",
        "reason": "Inherently balanced under braking. Start neutral and adjust ±1 based on preference — slightly negative for maximum grip, slightly positive for sharper turn-in.",
    },
}


@tool
def get_brake_balance_baseline(drivetrain: str) -> str:
    """Return GT7 brake balance starting-point guidance for a given drivetrain.
    Call this when a driver asks what brake balance to set, where to start, or what the default should be.
    Brake balance runs -5 (full front bias) to +5 (full rear bias).

    Args:
        drivetrain: The car's drivetrain layout. One of: FR, FF, MR, RR, 4WD.
    """
    drivetrain = drivetrain.upper().strip()
    entry = BRAKE_BALANCE_BASELINES.get(drivetrain)
    if not entry:
        valid = ", ".join(sorted(BRAKE_BALANCE_BASELINES))
        return f"Unknown drivetrain '{drivetrain}'. Use one of: {valid}."

    return (
        f"Brake balance baseline for {drivetrain}: {entry['range']}\n"
        f"Reason: {entry['reason']}\n"
        f"Scale: -5 = full front bias, +5 = full rear bias. Adjust from the baseline based on handling symptoms."
    )
