"""Bearing parsing and formatting for Kenyan survey plans.

Supports whole-circle bearings (e.g. 045°30'15", 45 30 15) and quadrant
bearings (e.g. N 45°30' E, S 10° W). Pure functions, no global state.
"""

from __future__ import annotations

import re


def _parse_dms_tokens(tokens: list[str]) -> tuple[float, float, float]:
    """Parse up to three numeric tokens into degrees, minutes, seconds.

    Args:
        tokens: List of 1-3 numeric strings (degrees, minutes, seconds).

    Returns:
        Tuple of (degrees, minutes, seconds) as floats.

    Raises:
        ValueError: If minutes or seconds are >= 60 or negative, or if
                     degrees are negative.
    """
    if not tokens:
        raise ValueError("No numeric values found in bearing string.")

    deg = float(tokens[0])
    mins = float(tokens[1]) if len(tokens) > 1 else 0.0
    secs = float(tokens[2]) if len(tokens) > 2 else 0.0

    if deg < 0:
        raise ValueError(f"Degrees must be non-negative, got {deg}.")
    if not (0 <= mins < 60):
        raise ValueError(f"Minutes must be in [0, 60), got {mins}.")
    if not (0 <= secs < 60):
        raise ValueError(f"Seconds must be in [0, 60), got {secs}.")

    return deg, mins, secs


def _dms_to_decimal(deg: float, mins: float, secs: float) -> float:
    """Convert degrees-minutes-seconds to decimal degrees."""
    return deg + mins / 60.0 + secs / 3600.0


# Regex to extract the numeric parts, stripping degree/minute/second symbols
_NUM_RE = re.compile(r"[\d]+(?:\.[\d]+)?")

# Quadrant pattern: leading N/S, trailing E/W, with DMS in between
_QUADRANT_RE = re.compile(
    r"^\s*([NS])\s+(.+?)\s+([EW])\s*$",
    re.IGNORECASE,
)


def parse_bearing(text: str) -> float:
    """Parse a bearing string to an azimuth in decimal degrees [0, 360).

    Supported formats:
        - Whole-circle: "045°30'15\"", "45 30 15", "180", "359°59'59\""
        - Quadrant:     "N 45°30' E", "S 10° W", "N 0 E" (due north)

    Args:
        text: Bearing string to parse.

    Returns:
        Azimuth in decimal degrees, normalised to [0, 360).

    Raises:
        ValueError: On invalid format, impossible minutes/seconds (>= 60),
                     impossible quadrant angles (> 90 for the angle part),
                     or unrecognised input.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty bearing string.")

    # Try quadrant form first
    qm = _QUADRANT_RE.match(text)
    if qm:
        ns = qm.group(1).upper()
        angle_part = qm.group(2)
        ew = qm.group(3).upper()

        tokens = _NUM_RE.findall(angle_part)
        deg, mins, secs = _parse_dms_tokens(tokens)

        if deg > 90 or (deg == 90 and (mins > 0 or secs > 0)):
            raise ValueError(f"Quadrant angle must be in [0, 90], got {deg}°{mins}'{secs}\".")

        angle = _dms_to_decimal(deg, mins, secs)

        # Convert quadrant bearing to whole-circle azimuth
        if ns == "N" and ew == "E":
            azimuth = angle
        elif ns == "S" and ew == "E":
            azimuth = 180.0 - angle
        elif ns == "S" and ew == "W":
            azimuth = 180.0 + angle
        elif ns == "N" and ew == "W":
            azimuth = 360.0 - angle
        else:
            raise ValueError(f"Invalid quadrant: {ns}...{ew}.")

        return azimuth % 360.0

    # Whole-circle form
    tokens = _NUM_RE.findall(text)
    if not tokens:
        raise ValueError(f"No numeric values found in bearing string: '{text}'.")

    # Check that the remaining non-numeric chars are only valid symbols/spaces
    stripped = _NUM_RE.sub("", text)
    stripped = stripped.replace("°", "").replace("'", "").replace("'", "")
    stripped = stripped.replace('"', "").replace('"', "").replace('"', "")
    stripped = stripped.replace("\u2033", "")  # double prime ″
    stripped = stripped.replace("\u2032", "")  # single prime ′
    stripped = stripped.strip()
    if stripped and not stripped.isspace():
        # Check for stray letters that might indicate a malformed quadrant
        if re.search(r"[A-Za-z]", stripped):
            raise ValueError(
                f"Unrecognised bearing format: '{text}'. "
                "Looks like a quadrant bearing but doesn't match N/S ... E/W pattern."
            )

    deg, mins, secs = _parse_dms_tokens(tokens)

    if deg >= 360 and (mins > 0 or secs > 0):
        raise ValueError(f"Whole-circle bearing must be in [0, 360), got {deg}°{mins}'{secs}\".")
    if deg > 360:
        raise ValueError(f"Whole-circle bearing must be in [0, 360), got {deg}°.")

    azimuth = _dms_to_decimal(deg, mins, secs)
    return azimuth % 360.0


def format_bearing(azimuth: float, seconds: bool = True) -> str:
    """Format an azimuth in decimal degrees as a DMS bearing string.

    Args:
        azimuth: Azimuth in decimal degrees [0, 360).
        seconds: If True, include seconds; otherwise only degrees and minutes.

    Returns:
        Formatted bearing string like "045°30'15\"" or "045°30'" .
    """
    azimuth = azimuth % 360.0
    deg = int(azimuth)
    remainder = (azimuth - deg) * 60.0
    mins = int(remainder)
    secs = (remainder - mins) * 60.0

    # Round seconds to avoid floating-point display artefacts
    secs = round(secs, 2)
    if secs >= 60.0:
        secs -= 60.0
        mins += 1
    if mins >= 60:
        mins -= 60
        deg += 1
        deg %= 360

    if seconds:
        # Show integer seconds when there's no fractional part
        if secs == int(secs):
            return f"{deg:03d}°{mins:02d}'{int(secs):02d}\""
        return f"{deg:03d}°{mins:02d}'{secs:05.2f}\""
    return f"{deg:03d}°{mins:02d}'"
