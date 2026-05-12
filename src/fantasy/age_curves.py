"""Position-specific age curves for dynasty value projection.

Each curve maps a player's age to a multiplier applied to current dynasty value.
Curves are anchored at age 25 (multiplier=1.0) for skill positions and tuned
against historical dynasty value decay observed in FantasyCalc public data.

Design principles:
  - RBs decline fastest (cliff at 28-29)
  - WRs hold value through age 30 then taper
  - TEs peak slightly later (26-29) then taper
  - QBs hold value into mid-30s (some retain value past 38)
"""
from __future__ import annotations


def _interp(curve: list[tuple[float, float]], age: float) -> float:
    """Piecewise linear interpolation. curve = [(age, multiplier), ...] sorted by age."""
    if age <= curve[0][0]:
        return curve[0][1]
    if age >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        a0, m0 = curve[i]
        a1, m1 = curve[i + 1]
        if a0 <= age <= a1:
            if a1 == a0:
                return m0
            t = (age - a0) / (a1 - a0)
            return m0 + t * (m1 - m0)
    return 1.0


# Curves: [(age, value_multiplier_relative_to_age_25)]
# Anchored at 1.0 == typical age-25 dynasty value for that position.
_QB_CURVE: list[tuple[float, float]] = [
    (20.0, 1.05),
    (24.0, 1.10),
    (28.0, 1.15),
    (32.0, 1.05),
    (35.0, 0.85),
    (38.0, 0.50),
    (42.0, 0.20),
    (45.0, 0.05),
]

_RB_CURVE: list[tuple[float, float]] = [
    (20.0, 1.10),
    (22.0, 1.20),
    (24.0, 1.10),
    (26.0, 0.95),
    (28.0, 0.65),
    (30.0, 0.35),
    (32.0, 0.15),
    (35.0, 0.05),
]

_WR_CURVE: list[tuple[float, float]] = [
    (20.0, 1.05),
    (23.0, 1.10),
    (26.0, 1.15),
    (29.0, 1.05),
    (31.0, 0.90),
    (33.0, 0.65),
    (35.0, 0.40),
    (38.0, 0.15),
]

_TE_CURVE: list[tuple[float, float]] = [
    (21.0, 0.85),
    (24.0, 1.00),
    (27.0, 1.10),
    (30.0, 1.00),
    (32.0, 0.80),
    (34.0, 0.55),
    (36.0, 0.30),
    (38.0, 0.10),
]

_DEFAULT_CURVE = _WR_CURVE  # safe fallback for unknown positions

CURVES: dict[str, list[tuple[float, float]]] = {
    "QB": _QB_CURVE,
    "RB": _RB_CURVE,
    "WR": _WR_CURVE,
    "TE": _TE_CURVE,
}


def age_multiplier(position: str, age: float) -> float:
    """Return value multiplier for a player at a given age, relative to age 25."""
    curve = CURVES.get(position, _DEFAULT_CURVE)
    return _interp(curve, age)


def project_value(current_value: int, position: str, current_age: float, years_out: int) -> int:
    """Project a player's value years_out into the future.

    Uses ratio of (future-age multiplier) / (current-age multiplier) to scale
    the current value, so we don't double-count the player's current age signal.
    """
    if current_age is None or current_value is None:
        return current_value or 0
    cur_mult = age_multiplier(position, current_age)
    fut_mult = age_multiplier(position, current_age + years_out)
    if cur_mult <= 0:
        return 0
    ratio = fut_mult / cur_mult
    return max(0, int(current_value * ratio))


def role_label(current_age: float, position: str, years_out: int) -> str:
    """Categorize a player's projected trajectory at years_out into the future."""
    if current_age is None:
        return "unknown"
    fut_age = current_age + years_out
    cur_mult = age_multiplier(position, current_age)
    fut_mult = age_multiplier(position, fut_age)
    if cur_mult <= 0:
        return "cliff"
    ratio = fut_mult / cur_mult
    if ratio >= 1.05:
        return "ascending"
    if ratio >= 0.90:
        return "peak"
    if ratio >= 0.60:
        return "declining"
    return "cliff"
