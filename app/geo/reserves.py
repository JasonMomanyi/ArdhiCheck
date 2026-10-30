"""Kenyan protected reserves and environmental buffer screening (app.geo.reserves).

Pure geometric verification of parcel coordinates against illustrative gazetted
public reserves, forest reserves, national parks, and statutory riparian buffers.

Conforms to:
- Kenya Survey Act Cap 299
- Forest Conservation and Management Act 2016
- Wildlife Conservation and Management Act 2013
- EMCA Cap 387 Section 42 & Water Resources Management Rules 2007

Pure functions, type hints, no AI calls, no valuation, no investment advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point, Polygon

# Kenya Geographic Bounding Box
KENYA_BBOX = {"min_lat": -4.75, "max_lat": 5.55, "min_lon": 33.85, "max_lon": 41.95}


@dataclass(frozen=True)
class ProtectedReserve:
    """An illustrative gazetted protected zone in Kenya."""

    name: str
    category: str
    statute: str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    source: str
    licence: str
    is_illustrative: bool = True
    details: str = ""


# Illustrative reference datasets of gazetted reserves with explicit attribution
ILLUSTRATIVE_RESERVES: list[ProtectedReserve] = [
    ProtectedReserve(
        name="Nairobi National Park (Illustrative)",
        category="National Park",
        statute="Wildlife Conservation and Management Act 2013",
        min_lon=36.780,
        min_lat=-1.450,
        max_lon=36.980,
        max_lat=-1.320,
        source="Kenya Wildlife Service (KWS) Gazette Notices",
        licence="Public Record / Open Government Information",
        details="Statutory wildlife conservation sanctuary. Non-alienable public land.",
    ),
    ProtectedReserve(
        name="Karura Forest Reserve (Illustrative)",
        category="Forest Reserve",
        statute="Forest Conservation and Management Act 2016",
        min_lon=36.815,
        min_lat=-1.260,
        max_lon=36.855,
        max_lat=-1.228,
        source="Kenya Forest Service (KFS) Gazette Notices",
        licence="Public Record / Open Government Information",
        details="Gazetted public indigenous forest. Strictly non-alienable.",
    ),
    ProtectedReserve(
        name="Ngong Road Forest Reserve (Illustrative)",
        category="Forest Reserve",
        statute="Forest Conservation and Management Act 2016",
        min_lon=36.720,
        min_lat=-1.335,
        max_lon=36.765,
        max_lat=-1.305,
        source="Kenya Forest Service (KFS) Gazette Notices",
        licence="Public Record / Open Government Information",
        details="Gazetted urban forest reserve.",
    ),
    ProtectedReserve(
        name="Nairobi River Riparian Corridor (Illustrative)",
        category="Riparian Buffer",
        statute="Survey Act Cap 299 & EMCA Cap 387 Section 42",
        min_lon=36.800,
        min_lat=-1.288,
        max_lon=36.935,
        max_lat=-1.268,
        source="Water Resources Authority (WRA) & Survey of Kenya",
        licence="Public Statutory Reference",
        details="Statutory environmental setback corridor along the Nairobi River basin.",
    ),
    ProtectedReserve(
        name="Ngong River Basin Riparian Corridor (Illustrative)",
        category="Riparian Buffer",
        statute="Survey Act Cap 299 & EMCA Cap 387 Section 42",
        min_lon=36.785,
        min_lat=-1.320,
        max_lon=36.870,
        max_lat=-1.300,
        source="Water Resources Authority (WRA) & Survey of Kenya",
        licence="Public Statutory Reference",
        details="Statutory environmental riparian reserve along Ngong River course.",
    ),
]


def is_inside_kenya(lon: float, lat: float) -> bool:
    """Verify whether geographic coordinates fall inside Kenya territorial boundary."""
    return (
        KENYA_BBOX["min_lon"] <= lon <= KENYA_BBOX["max_lon"]
        and KENYA_BBOX["min_lat"] <= lat <= KENYA_BBOX["max_lat"]
    )


def screen_reserves_pure(
    coords: list[tuple[float, float]],
    riparian_buffer_m: float = 30.0,
) -> list[dict[str, Any]]:
    """Screen parcel vertices and polygon against illustrative protected reserves.

    Args:
        coords: List of (longitude, latitude) WGS84 vertices.
        riparian_buffer_m: User-configurable riparian setback buffer in metres.
                           Statutory setbacks under Kenyan law range from 6 m
                           for narrow streams to 30 m or more for major rivers.

    Returns:
        List of conflict dictionaries with statute citations, layer provenance,
        and overlap notes.
    """
    conflicts: list[dict[str, Any]] = []
    if not coords:
        return conflicts

    poly = Polygon(coords) if len(coords) >= 3 else None

    for res in ILLUSTRATIVE_RESERVES:
        res_poly = Polygon(
            [
                (res.min_lon, res.min_lat),
                (res.max_lon, res.min_lat),
                (res.max_lon, res.max_lat),
                (res.min_lon, res.max_lat),
            ]
        )

        overlap = False
        # Point containment check
        for lon, lat in coords:
            pt = Point(lon, lat)
            if res_poly.contains(pt) or (
                res.min_lon <= lon <= res.max_lon and res.min_lat <= lat <= res.max_lat
            ):
                overlap = True
                break

        # Polygon intersection check
        if not overlap and poly and poly.intersects(res_poly):
            overlap = True

        if overlap:
            conflicts.append(
                {
                    "name": res.name,
                    "category": res.category,
                    "statute": res.statute,
                    "source": res.source,
                    "licence": res.licence,
                    "is_illustrative": res.is_illustrative,
                    "configured_riparian_buffer_m": (
                        riparian_buffer_m if res.category == "Riparian Buffer" else None
                    ),
                    "details": res.details,
                    "disclaimer": (
                        "Illustrative layer for screening only; verify with official RIM at Lands."
                    ),
                }
            )

    return conflicts


def get_layer_metadata() -> list[dict[str, Any]]:
    """Return explicit attribution and licensing metadata for all map layers."""
    return [
        {
            "layer_name": "OpenStreetMap Standard",
            "type": "Base Map",
            "source": "OpenStreetMap Contributors",
            "licence": "Open Database Licence (ODbL) 1.0",
            "attribution_url": "https://www.openstreetmap.org/copyright",
            "is_illustrative": False,
        },
        {
            "layer_name": "Esri World Imagery",
            "type": "Satellite Base Map",
            "source": "Esri, Maxar, Earthstar Geographics, CNES/Airbus DS",
            "licence": "Esri Master License Agreement (Evaluation/Developer)",
            "attribution_url": "https://www.esri.com",
            "is_illustrative": False,
        },
        {
            "layer_name": "Gazetted Forests & National Parks",
            "type": "Public Reserve Overlay",
            "source": "Kenya Forest Service (KFS) / Kenya Wildlife Service (KWS)",
            "licence": "Public Record / Kenya Gazette",
            "attribution_url": "http://kenyalaw.org",
            "is_illustrative": True,
        },
        {
            "layer_name": "Riparian Buffer Corridor",
            "type": "Environmental Setback Overlay",
            "source": "Water Resources Authority (WRA) & EMCA Cap 387",
            "licence": "Public Record / Survey Act Cap 299",
            "attribution_url": "http://kenyalaw.org",
            "is_illustrative": True,
        },
    ]

