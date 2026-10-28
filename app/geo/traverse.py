"""Traverse computation, closure analysis, and Bowditch adjustment.

Pure functions for processing survey traverse data. No global state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Leg:
    """A single traverse leg defined by bearing and distance.

    Attributes:
        bearing_deg: Whole-circle bearing in decimal degrees [0, 360).
        distance_m: Horizontal distance in metres (must be positive).
    """

    bearing_deg: float
    distance_m: float

    def __post_init__(self) -> None:
        if self.distance_m < 0:
            raise ValueError(f"Distance must be non-negative, got {self.distance_m}.")


def compute_traverse(
    start_e: float,
    start_n: float,
    legs: list[Leg],
) -> list[tuple[float, float]]:
    """Compute coordinates from a starting point and a series of legs.

    Args:
        start_e: Starting easting (x) coordinate in metres.
        start_n: Starting northing (y) coordinate in metres.
        legs: Ordered list of traverse legs.

    Returns:
        List of (easting, northing) coordinate tuples, starting with the
        start point and including one point after each leg (len = len(legs) + 1).
    """
    coords: list[tuple[float, float]] = [(start_e, start_n)]
    e, n = start_e, start_n

    for leg in legs:
        bearing_rad = math.radians(leg.bearing_deg)
        de = leg.distance_m * math.sin(bearing_rad)
        dn = leg.distance_m * math.cos(bearing_rad)
        e += de
        n += dn
        coords.append((e, n))

    return coords


@dataclass(frozen=True)
class ClosureResult:
    """Result of a traverse closure analysis.

    Attributes:
        misclosure_e: Misclosure in the easting direction (metres).
        misclosure_n: Misclosure in the northing direction (metres).
        linear_misclosure: Total linear misclosure (metres).
        perimeter: Total traverse perimeter (metres).
        relative_precision: Relative precision as "1:N" string, or
                            "1:inf" if misclosure is zero.
    """

    misclosure_e: float
    misclosure_n: float
    linear_misclosure: float
    perimeter: float
    relative_precision: str


def closure(legs: list[Leg]) -> ClosureResult:
    """Compute the misclosure and relative precision of a closed traverse.

    Assumes the traverse should return to its starting point.

    Args:
        legs: Ordered list of traverse legs forming a closed loop.

    Returns:
        ClosureResult with misclosure components, linear misclosure,
        perimeter and relative precision.
    """
    total_de = 0.0
    total_dn = 0.0
    perimeter = 0.0

    for leg in legs:
        bearing_rad = math.radians(leg.bearing_deg)
        total_de += leg.distance_m * math.sin(bearing_rad)
        total_dn += leg.distance_m * math.cos(bearing_rad)
        perimeter += leg.distance_m

    linear = math.sqrt(total_de**2 + total_dn**2)

    if linear < 1e-12:
        precision_str = "1:inf"
    else:
        ratio = perimeter / linear
        precision_str = f"1:{round(ratio)}"

    return ClosureResult(
        misclosure_e=total_de,
        misclosure_n=total_dn,
        linear_misclosure=linear,
        perimeter=perimeter,
        relative_precision=precision_str,
    )


def bowditch_adjust(
    start_e: float,
    start_n: float,
    legs: list[Leg],
) -> list[tuple[float, float]]:
    """Apply the Bowditch (compass) adjustment to a closed traverse.

    Distributes the misclosure proportionally to each leg's distance.
    Each point's correction is proportional to the cumulative distance
    travelled up to that point divided by the total perimeter.

    Args:
        start_e: Starting easting coordinate in metres.
        start_n: Starting northing coordinate in metres.
        legs: Ordered list of traverse legs forming a closed loop.

    Returns:
        List of adjusted (easting, northing) coordinate tuples
        (len = len(legs) + 1). The last point will coincide exactly
        with the first.
    """
    cr = closure(legs)
    perimeter = cr.perimeter

    # If already closed perfectly, just compute normally
    if cr.linear_misclosure < 1e-12:
        return compute_traverse(start_e, start_n, legs)

    # First compute raw (unadjusted) coordinates
    raw_coords = compute_traverse(start_e, start_n, legs)

    # Apply Bowditch corrections proportional to cumulative distance
    adjusted: list[tuple[float, float]] = [(start_e, start_n)]
    cumulative_dist = 0.0

    for i, leg in enumerate(legs):
        cumulative_dist += leg.distance_m
        fraction = cumulative_dist / perimeter

        adj_e = raw_coords[i + 1][0] - cr.misclosure_e * fraction
        adj_n = raw_coords[i + 1][1] - cr.misclosure_n * fraction

        adjusted.append((adj_e, adj_n))

    # Force the last point to be exactly the start (remove floating-point drift)
    adjusted[-1] = (start_e, start_n)

    return adjusted
