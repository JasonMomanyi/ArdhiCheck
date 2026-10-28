"""Error localisation: suggest single-value fixes for a traverse misclosure.

Given a closed traverse with a misclosure, this module tries to identify
which single leg change (bearing or distance) would fix the traverse.

Two methods:
1. Exact cancellation: for each leg, compute the change that would exactly
   cancel the misclosure.
2. Digit perturbation: try every single-digit substitution and adjacent-digit
   transposition in each printed bearing and distance string, re-run closure,
   and keep candidates within tolerance.

Pure functions, no global state, no AI calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.geo.bearings import format_bearing, parse_bearing
from app.geo.traverse import Leg, closure


@dataclass(frozen=True)
class CandidateFix:
    """A candidate single-value correction.

    Attributes:
        leg_index: Index of the leg to modify (0-based).
        field: Which field was changed ("bearing" or "distance").
        original_value: The original string value.
        corrected_value: The proposed corrected string value.
        residual_misclosure: Linear misclosure after applying this fix (metres).
        edit_distance: Number of character changes from original to corrected.
    """

    leg_index: int
    field: str
    original_value: str
    corrected_value: str
    residual_misclosure: float
    edit_distance: int


def _char_edit_distance(a: str, b: str) -> int:
    """Count the number of character positions that differ (simple Hamming-like).

    For strings of different lengths, counts the length difference plus
    character mismatches in the overlapping portion.
    """
    dist = abs(len(a) - len(b))
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            dist += 1
    return dist


def _exact_cancellation_fixes(
    legs: list[Leg],
    legs_as_text: list[tuple[str, str]],
    tolerance: float = 0.1,
) -> list[CandidateFix]:
    """Method 1: For each leg, compute the bearing/distance that would
    exactly cancel the misclosure.

    Only candidates that bring the residual misclosure within tolerance
    and represent an actual change are returned.

    Args:
        legs: Parsed Leg objects.
        legs_as_text: List of (bearing_text, distance_text) for each leg.
        tolerance: Maximum acceptable linear misclosure in metres.

    Returns:
        List of CandidateFix for exact cancellations within tolerance.
    """
    cr = closure(legs)
    if cr.linear_misclosure < 1e-10:
        return []

    candidates: list[CandidateFix] = []

    for i, leg in enumerate(legs):
        bearing_rad = math.radians(leg.bearing_deg)

        # Current deltas for this leg
        de_i = leg.distance_m * math.sin(bearing_rad)
        dn_i = leg.distance_m * math.cos(bearing_rad)

        # Required deltas for this leg (to cancel misclosure)
        needed_de = de_i - cr.misclosure_e
        needed_dn = dn_i - cr.misclosure_n

        # Fix by changing the bearing (keep distance)
        needed_dist_for_bearing = math.hypot(needed_de, needed_dn)
        if abs(needed_dist_for_bearing - leg.distance_m) <= tolerance:
            needed_bearing_rad = math.atan2(needed_de, needed_dn)
            needed_bearing_deg = math.degrees(needed_bearing_rad) % 360.0

            corrected_bearing_str = format_bearing(needed_bearing_deg)
            original_bearing_str = legs_as_text[i][0]

            new_legs_b = list(legs)
            new_legs_b[i] = Leg(bearing_deg=needed_bearing_deg, distance_m=leg.distance_m)
            cr_b = closure(new_legs_b)

            if cr_b.linear_misclosure <= tolerance:
                edit_dist = _char_edit_distance(original_bearing_str, corrected_bearing_str)
                if edit_dist > 0:
                    candidates.append(
                        CandidateFix(
                            leg_index=i,
                            field="bearing",
                            original_value=original_bearing_str,
                            corrected_value=corrected_bearing_str,
                            residual_misclosure=cr_b.linear_misclosure,
                            edit_distance=edit_dist,
                        )
                    )

        # Fix by changing the distance (keep bearing)
        perp_error = abs(needed_de * math.cos(bearing_rad) - needed_dn * math.sin(bearing_rad))
        if perp_error <= tolerance:
            needed_dist = needed_de * math.sin(bearing_rad) + needed_dn * math.cos(bearing_rad)
            if needed_dist > 0:
                original_dist_str = legs_as_text[i][1]
                decimals = len(original_dist_str.split(".")[1]) if "." in original_dist_str else 3
                corrected_dist_str = f"{needed_dist:.{decimals}f}"

                new_legs_d = list(legs)
                new_legs_d[i] = Leg(bearing_deg=leg.bearing_deg, distance_m=needed_dist)
                cr_d = closure(new_legs_d)

                if cr_d.linear_misclosure <= tolerance:
                    edit_dist = _char_edit_distance(original_dist_str, corrected_dist_str)
                    if edit_dist > 0:
                        candidates.append(
                            CandidateFix(
                                leg_index=i,
                                field="distance",
                                original_value=original_dist_str,
                                corrected_value=corrected_dist_str,
                                residual_misclosure=cr_d.linear_misclosure,
                                edit_distance=edit_dist,
                            )
                        )

    return candidates


def _digit_perturbation_fixes(
    legs: list[Leg],
    legs_as_text: list[tuple[str, str]],
    tolerance: float,
) -> list[CandidateFix]:
    """Method 2: Try every single-digit substitution and adjacent-digit
    transposition in each bearing and distance string.

    Args:
        legs: Parsed Leg objects.
        legs_as_text: List of (bearing_text, distance_text) for each leg.
        tolerance: Maximum acceptable linear misclosure in metres.

    Returns:
        List of CandidateFix for perturbations that bring the traverse
        within tolerance.
    """
    candidates: list[CandidateFix] = []

    for i, (bearing_text, distance_text) in enumerate(legs_as_text):
        # Try bearing perturbations
        for perturbed in _generate_perturbations(bearing_text):
            try:
                new_az = parse_bearing(perturbed)
            except ValueError:
                continue

            new_legs = list(legs)
            new_legs[i] = Leg(bearing_deg=new_az, distance_m=legs[i].distance_m)
            cr = closure(new_legs)

            if cr.linear_misclosure <= tolerance:
                candidates.append(
                    CandidateFix(
                        leg_index=i,
                        field="bearing",
                        original_value=bearing_text,
                        corrected_value=perturbed,
                        residual_misclosure=cr.linear_misclosure,
                        edit_distance=_char_edit_distance(bearing_text, perturbed),
                    )
                )

        # Try distance perturbations
        for perturbed in _generate_perturbations(distance_text):
            try:
                new_dist = float(perturbed)
            except ValueError:
                continue
            if new_dist <= 0:
                continue

            new_legs = list(legs)
            new_legs[i] = Leg(bearing_deg=legs[i].bearing_deg, distance_m=new_dist)
            cr = closure(new_legs)

            if cr.linear_misclosure <= tolerance:
                candidates.append(
                    CandidateFix(
                        leg_index=i,
                        field="distance",
                        original_value=distance_text,
                        corrected_value=perturbed,
                        residual_misclosure=cr.linear_misclosure,
                        edit_distance=_char_edit_distance(distance_text, perturbed),
                    )
                )

    return candidates


def _generate_perturbations(text: str) -> list[str]:
    """Generate all single-digit substitutions and adjacent-digit transpositions.

    Args:
        text: The original string.

    Returns:
        List of perturbed strings (does not include the original).
    """
    results: list[str] = []
    chars = list(text)

    # Find positions of digit characters
    digit_positions = [i for i, c in enumerate(chars) if c.isdigit()]

    # Single-digit substitutions
    for pos in digit_positions:
        original_digit = chars[pos]
        for replacement in "0123456789":
            if replacement == original_digit:
                continue
            new_chars = chars.copy()
            new_chars[pos] = replacement
            results.append("".join(new_chars))

    # Adjacent-digit transpositions
    for idx in range(len(digit_positions) - 1):
        pos_a = digit_positions[idx]
        pos_b = digit_positions[idx + 1]
        # Only transpose truly adjacent characters
        if pos_b == pos_a + 1:
            if chars[pos_a] != chars[pos_b]:
                new_chars = chars.copy()
                new_chars[pos_a], new_chars[pos_b] = new_chars[pos_b], new_chars[pos_a]
                results.append("".join(new_chars))

    return results


def suggest_single_value_fixes(
    legs_as_text: list[tuple[str, str]],
    start: tuple[float, float] | None = None,
    tolerance: float = 0.1,
) -> list[CandidateFix]:
    """Suggest ranked single-value corrections for a traverse misclosure.

    Combines two methods:
    1. Exact cancellation: compute the ideal correction for each leg.
    2. Digit perturbation: try single-digit edits and rank by smallest edit.

    Results are ranked by (edit_distance, residual_misclosure).

    Args:
        legs_as_text: List of (bearing_text, distance_text) strings for
                       each leg of the traverse.
        start: Optional (easting, northing) start point (not used for
               closure computation but reserved for future use).
        tolerance: Maximum acceptable linear misclosure in metres for
                   digit-perturbation candidates.

    Returns:
        Sorted list of CandidateFix objects, best (smallest edit) first.

    Raises:
        ValueError: If any bearing or distance text cannot be parsed.
    """
    # Parse all legs
    legs: list[Leg] = []
    for bearing_text, distance_text in legs_as_text:
        az = parse_bearing(bearing_text)
        dist = float(distance_text)
        legs.append(Leg(bearing_deg=az, distance_m=dist))

    # Check current closure
    cr = closure(legs)
    if cr.linear_misclosure < 1e-10:
        return []  # Already closed

    # Method 1: exact cancellation
    exact = _exact_cancellation_fixes(legs, legs_as_text, tolerance)

    # Method 2: digit perturbation
    perturbed = _digit_perturbation_fixes(legs, legs_as_text, tolerance)

    # Combine, deduplicate, and sort
    all_candidates = exact + perturbed

    # Remove duplicates based on (leg_index, field, corrected_value)
    seen: set[tuple[int, str, str]] = set()
    unique: list[CandidateFix] = []
    for c in all_candidates:
        key = (c.leg_index, c.field, c.corrected_value)
        if key not in seen:
            seen.add(key)
            unique.append(c)

    # Sort by edit distance first, then by residual misclosure
    unique.sort(key=lambda c: (c.edit_distance, c.residual_misclosure))

    return unique
