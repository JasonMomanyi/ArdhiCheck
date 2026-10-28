"""Area computation and unit conversion for survey parcels.

Pure functions for computing polygon areas via the shoelace formula,
converting between area units, and comparing stated vs computed areas.
No global state.
"""

from __future__ import annotations

from typing import Any

# Conversion factors to square metres
_AREA_FACTORS: dict[str, float] = {
    "m2": 1.0,
    "ha": 10_000.0,
    "acre": 4046.8564224,
}

_VALID_UNITS = set(_AREA_FACTORS.keys())


def polygon_area_m2(coords: list[tuple[float, float]]) -> float:
    """Compute the area of a simple polygon using the shoelace formula.

    The polygon does not need to be explicitly closed (i.e. the last
    coordinate does not need to repeat the first). If it does repeat,
    the result is the same.

    Args:
        coords: List of (x, y) or (easting, northing) coordinate tuples.
                 Must have at least 3 distinct vertices.

    Returns:
        Absolute area in square metres.

    Raises:
        ValueError: If fewer than 3 coordinates are provided.
    """
    n = len(coords)
    if n < 3:
        raise ValueError(f"Need at least 3 coordinates for an area, got {n}.")

    # Shoelace formula
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]

    return abs(area) / 2.0


def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    """Convert an area value between supported units.

    Supported units: "m2" (square metres), "ha" (hectares),
    "acre" (international acres, 1 acre = 4046.8564224 m²).

    Args:
        value: The area value to convert.
        from_unit: Source unit (case-sensitive).
        to_unit: Target unit (case-sensitive).

    Returns:
        Converted area value.

    Raises:
        ValueError: If either unit is not supported.
    """
    if from_unit not in _VALID_UNITS:
        raise ValueError(f"Unknown source unit '{from_unit}'. Supported: {sorted(_VALID_UNITS)}")
    if to_unit not in _VALID_UNITS:
        raise ValueError(f"Unknown target unit '{to_unit}'. Supported: {sorted(_VALID_UNITS)}")

    # Convert to m² first, then to target
    m2 = value * _AREA_FACTORS[from_unit]
    return m2 / _AREA_FACTORS[to_unit]


def compare_stated_area(
    stated_value: float,
    unit: str,
    computed_m2: float,
    tolerance_pct: float = 2.0,
) -> dict[str, Any]:
    """Compare a stated area against a computed area.

    Args:
        stated_value: The area value stated on the plan.
        unit: The unit of the stated value ("m2", "ha", or "acre").
        computed_m2: The computed area in square metres.
        tolerance_pct: Acceptable percentage difference (default 2%).

    Returns:
        Dictionary with keys:
            - stated_m2: stated value converted to m²
            - computed_m2: the computed area in m²
            - difference_m2: absolute difference in m²
            - difference_pct: percentage difference relative to stated
            - within_tolerance: bool, True if difference_pct <= tolerance_pct

    Raises:
        ValueError: If the unit is not supported or stated_value is <= 0.
    """
    if stated_value <= 0:
        raise ValueError(f"Stated area must be positive, got {stated_value}.")

    stated_m2 = convert_area(stated_value, unit, "m2")
    diff_m2 = abs(computed_m2 - stated_m2)
    diff_pct = (diff_m2 / stated_m2) * 100.0

    return {
        "stated_m2": stated_m2,
        "computed_m2": computed_m2,
        "difference_m2": diff_m2,
        "difference_pct": diff_pct,
        "within_tolerance": diff_pct <= tolerance_pct,
    }
