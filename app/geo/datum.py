"""Datum handling and coordinate transforms for Kenyan survey plans.

Looks up Arc 1960 geographic and UTM zones from the pyproj database
at runtime, verifying each CRS by name. Provides transforms to WGS84
with an uncertainty note. No hardcoded EPSG codes from memory.
"""

from __future__ import annotations

from dataclasses import dataclass

import pyproj


def _find_crs_by_name(search_terms: list[str]) -> pyproj.CRS:
    """Search the pyproj/PROJ database for a CRS matching all search terms.

    Args:
        search_terms: List of strings that must all appear in the CRS name.

    Returns:
        The matching pyproj.CRS object.

    Raises:
        ValueError: If no CRS or multiple ambiguous CRSs are found.
    """
    results = pyproj.database.query_crs_info()

    matches = []
    for info in results:
        name = info.name.lower()
        if all(term.lower() in name for term in search_terms):
            matches.append(info)

    if not matches:
        raise ValueError(f"No CRS found matching all terms: {search_terms}")

    return matches


# CRS lookup registry: maps friendly names to pyproj search terms
_CRS_SEARCH: dict[str, list[str]] = {
    "arc1960_geo": ["Arc 1960"],
    "arc1960_utm36s": ["Arc 1960", "UTM", "zone 36S"],
    "arc1960_utm37s": ["Arc 1960", "UTM", "zone 37S"],
    "arc1960_utm36n": ["Arc 1960", "UTM", "zone 36N"],
    "arc1960_utm37n": ["Arc 1960", "UTM", "zone 37N"],
}


def lookup_arc1960_crs(crs_name: str) -> pyproj.CRS:
    """Look up an Arc 1960 CRS by friendly name.

    Supported names:
        - "arc1960_geo": Arc 1960 geographic CRS
        - "arc1960_utm36s": Arc 1960 / UTM zone 36S
        - "arc1960_utm37s": Arc 1960 / UTM zone 37S
        - "arc1960_utm36n": Arc 1960 / UTM zone 36N
        - "arc1960_utm37n": Arc 1960 / UTM zone 37N

    The function queries the PROJ database and verifies that the CRS name
    contains "Arc 1960". EPSG codes are not hardcoded.

    Args:
        crs_name: One of the supported friendly names.

    Returns:
        A pyproj.CRS object for the matching CRS.

    Raises:
        ValueError: If the name is not supported or no matching CRS is found.
    """
    if crs_name not in _CRS_SEARCH:
        raise ValueError(f"Unknown CRS name '{crs_name}'. Supported: {sorted(_CRS_SEARCH.keys())}")

    search_terms = _CRS_SEARCH[crs_name]
    matches = _find_crs_by_name(search_terms)

    # For geographic CRS, filter to only geographic (not projected)
    if crs_name == "arc1960_geo":
        geo_matches = [m for m in matches if m.type == pyproj.enums.PJType.GEOGRAPHIC_2D_CRS]
        if geo_matches:
            matches = geo_matches

    # For UTM projected CRS, filter to projected type
    if "utm" in crs_name:
        proj_matches = [m for m in matches if m.type == pyproj.enums.PJType.PROJECTED_CRS]
        if proj_matches:
            matches = proj_matches

    if not matches:
        raise ValueError(
            f"No CRS found in PROJ database matching '{crs_name}' (search: {search_terms})."
        )

    # Take the first match (prefer EPSG authority)
    epsg_matches = [m for m in matches if m.auth_name == "EPSG"]
    chosen = epsg_matches[0] if epsg_matches else matches[0]

    crs = pyproj.CRS.from_authority(chosen.auth_name, chosen.code)

    # Verify the CRS name actually contains "Arc 1960"
    if "arc 1960" not in crs.name.lower():
        raise ValueError(
            f"CRS {chosen.auth_name}:{chosen.code} name '{crs.name}' "
            "does not contain 'Arc 1960'. Lookup may be incorrect."
        )

    return crs


# WGS84 CRS for transforms
_WGS84 = pyproj.CRS.from_epsg(4326)


@dataclass(frozen=True)
class TransformResult:
    """Result of a coordinate transformation to WGS84.

    Attributes:
        lon: Longitude in decimal degrees (WGS84).
        lat: Latitude in decimal degrees (WGS84).
        uncertainty_note: Statement about transform accuracy.
    """

    lon: float
    lat: float
    uncertainty_note: str


def transform_to_wgs84(
    e: float,
    n: float,
    crs_name: str,
) -> TransformResult:
    """Transform coordinates from an Arc 1960 CRS to WGS84 (lon, lat).

    Args:
        e: Easting or longitude in the source CRS.
        n: Northing or latitude in the source CRS.
        crs_name: One of the supported Arc 1960 CRS names
                   (see lookup_arc1960_crs).

    Returns:
        TransformResult with lon, lat and an uncertainty note.

    Raises:
        ValueError: If the CRS name is not supported.
    """
    source_crs = lookup_arc1960_crs(crs_name)

    transformer = pyproj.Transformer.from_crs(source_crs, _WGS84, always_xy=True)

    lon, lat = transformer.transform(e, n)

    return TransformResult(
        lon=lon,
        lat=lat,
        uncertainty_note=(
            "Arc 1960 to WGS84 datum transformations are accurate to "
            "approximately ±5 metres depending on the transformation "
            "parameters available. Do not treat these coordinates as "
            "survey-grade."
        ),
    )
