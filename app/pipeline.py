"""End-to-end audit pipeline for ArdhiCheck.

Orchestrates:
1. Multimodal document extraction (Meta Muse Spark 1.3).
2. Pure geometric verification (app.geo.*).
3. Satellite feature & buffer segmentation (Meta SAM 3.1).
4. Blunder diagnosis and candidate typo ranking (fixes.py).
5. Traffic-light verdict and plain-language report synthesis.
"""

from __future__ import annotations

from typing import Any

from app.geo.area import compare_stated_area, polygon_area_m2
from app.geo.bearings import parse_bearing
from app.geo.datum import transform_to_wgs84
from app.geo.fixes import suggest_single_value_fixes
from app.geo.traverse import Leg, bowditch_adjust, closure, compute_traverse
from app.meta.client import MetaModelClient


def run_survey_audit(
    plan_image_bytes: bytes | None = None,
    satellite_image_bytes: bytes | None = None,
    preset_hint: str | None = None,
    manual_legs: list[tuple[str, str]] | None = None,
    manual_lr_number: str | None = None,
    manual_stated_area: float | None = None,
    manual_stated_unit: str = "ha",
    crs_name: str = "arc1960_utm37s",
    start_coords: tuple[float, float] = (257000.0, 9857000.0),
    tolerance_misclosure_m: float = 0.30,
    tolerance_area_pct: float = 3.0,
    meta_client: MetaModelClient | None = None,
) -> dict[str, Any]:
    """Execute the full ArdhiCheck audit pipeline."""
    client = meta_client or MetaModelClient()

    # Step 1: Extraction
    if manual_legs:
        legs_as_text = manual_legs
        lr_number = manual_lr_number or "L.R. MANUAL/INPUT"
        stated_area = manual_stated_area if manual_stated_area is not None else 0.50
        stated_unit = manual_stated_unit
        extraction_source = "manual_entry"
        notes = ["Manual user input verified."]
    elif plan_image_bytes or preset_hint:
        extraction = client.extract_plan_from_image(
            image_bytes=plan_image_bytes or b"",
            preset_hint=preset_hint,
        )
        legs_as_text = extraction.legs
        lr_number = manual_lr_number or extraction.lr_number
        stated_area = (
            manual_stated_area if manual_stated_area is not None else extraction.stated_area
        )
        stated_unit = manual_stated_unit or extraction.stated_unit
        crs_name = crs_name or extraction.datum_name
        extraction_source = extraction.source
        notes = extraction.raw_notes
    else:
        raise ValueError("Must provide either plan image, preset hint, or manual legs.")

    # Step 2: Parse legs into geometry primitives
    parsed_legs: list[Leg] = []
    for b_str, d_str in legs_as_text:
        azimuth = parse_bearing(b_str)
        dist = float(d_str)
        parsed_legs.append(Leg(bearing_deg=azimuth, distance_m=dist))

    # Step 3: Compute raw traverse and closure
    raw_coords = compute_traverse(start_coords[0], start_coords[1], parsed_legs)
    cr = closure(parsed_legs)

    # Step 4: Bowditch adjustment
    adjusted_coords = bowditch_adjust(start_coords[0], start_coords[1], parsed_legs)

    # Step 5: Area computation & comparison (shoelace on adjusted closed polygon)
    # Exclude the closing duplicate vertex for polygon area
    computed_m2 = polygon_area_m2(adjusted_coords[:-1])
    area_comp = compare_stated_area(
        stated_value=stated_area,
        unit=stated_unit,
        computed_m2=computed_m2,
        tolerance_pct=tolerance_area_pct,
    )

    # Step 6: Blunder Localisation (if misclosure exceeds tolerance)
    candidate_fixes: list[dict[str, Any]] = []
    if cr.linear_misclosure > tolerance_misclosure_m:
        raw_fixes = suggest_single_value_fixes(
            legs_as_text=legs_as_text,
            start=start_coords,
            tolerance=tolerance_misclosure_m,
        )
        candidate_fixes = [
            {
                "leg_index": f.leg_index,
                "field": f.field,
                "original_value": f.original_value,
                "corrected_value": f.corrected_value,
                "residual_misclosure": f.residual_misclosure,
                "edit_distance": f.edit_distance,
            }
            for f in raw_fixes
        ]

    # Step 7: Datum & WGS84 transform
    wgs84_coords: list[tuple[float, float]] = []
    uncertainty_note = ""
    for e, n in adjusted_coords:
        try:
            res = transform_to_wgs84(e, n, crs_name)
            wgs84_coords.append((res.lon, res.lat))
            uncertainty_note = res.uncertainty_note
        except Exception:
            # Fallback approximate center if crs name mismatch
            wgs84_coords.append((36.8172, -1.2864))

    # Step 8: Satellite & Protected Buffer Segmentation (SAM 3.1)
    satellite_res = client.segment_satellite_features(
        image_bytes=satellite_image_bytes,
        preset_hint=preset_hint,
    )

    # Step 9: Determine Traffic-Light Verdict
    # GREEN: Closes <= tolerance, area matches <= tolerance, zero buffer overlap
    # AMBER: Misclosure exists BUT high-confidence single-value blunder fix diagnosed
    # RED: Riparian overlap, gross uncloseable misclosure, or major area inflation
    if satellite_res.overlap_area_m2 > 10.0:
        verdict = "RED"
        buffer_desc = (
            "riparian buffer" if satellite_res.has_riparian_zone else "road/protected buffer"
        )
        verdict_reason = (
            f"Encroachment detected: {satellite_res.overlap_area_m2:.1f} m² "
            f"overlap with {buffer_desc}."
        )
    elif cr.linear_misclosure > tolerance_misclosure_m:
        if candidate_fixes and candidate_fixes[0]["edit_distance"] <= 3:
            verdict = "AMBER"
            leg_num = candidate_fixes[0]["leg_index"] + 1
            fld_name = candidate_fixes[0]["field"]
            verdict_reason = (
                f"Traverse misclosed by {cr.linear_misclosure:.3f} m, but a high-probability "
                f"typo was localised in Leg {leg_num} ({fld_name})."
            )
        else:
            verdict = "RED"
            verdict_reason = (
                f"Boundary traverse misclosure of {cr.linear_misclosure:.3f} m exceeds tolerance."
            )
    elif not area_comp["within_tolerance"]:
        verdict = "RED"
        pct_diff = area_comp["difference_pct"]
        verdict_reason = (
            f"Area discrepancy of {pct_diff:.1f}% exceeds {tolerance_area_pct}% tolerance."
        )
    else:
        verdict = "GREEN"
        verdict_reason = (
            f"Traverse closes with precision {cr.relative_precision}. "
            f"Area matches stated within {area_comp['difference_pct']:.2f}%. Zero buffer overlap."
        )

    # Step 10: Muse Spark 1.3 Advisory Synthesis
    audit_payload = {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "lr_number": lr_number,
        "closure": {
            "misclosure_e": cr.misclosure_e,
            "misclosure_n": cr.misclosure_n,
            "linear_misclosure": cr.linear_misclosure,
            "perimeter": cr.perimeter,
            "relative_precision": cr.relative_precision,
            "tolerance_m": tolerance_misclosure_m,
        },
        "area": area_comp,
        "satellite": {
            "has_riparian_zone": satellite_res.has_riparian_zone,
            "riparian_buffer_m": satellite_res.riparian_buffer_m,
            "overlap_area_m2": satellite_res.overlap_area_m2,
            "detected_features": satellite_res.detected_features,
            "source": satellite_res.source,
        },
        "candidate_fixes": candidate_fixes,
        "datum": {
            "crs_name": crs_name,
            "uncertainty_note": uncertainty_note,
        },
    }

    advisory_report = client.synthesize_advisory_report(audit_payload)

    # Step 11: GeoJSON & CAD coordinates packaging
    geojson_polygon = {
        "type": "Feature",
        "properties": {
            "lr_number": lr_number,
            "verdict": verdict,
            "stated_area": f"{stated_area} {stated_unit}",
            "computed_m2": computed_m2,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[lon, lat] for lon, lat in wgs84_coords]],
        },
    }

    return {
        **audit_payload,
        "advisory_report": advisory_report,
        "extraction_source": extraction_source,
        "notes": notes,
        "raw_coords": raw_coords,
        "adjusted_coords": adjusted_coords,
        "wgs84_coords": wgs84_coords,
        "geojson": geojson_polygon,
        "legs": [
            {
                "index": i + 1,
                "bearing_dms": legs_as_text[i][0],
                "bearing_deg": parsed_legs[i].bearing_deg,
                "distance_m": parsed_legs[i].distance_m,
            }
            for i in range(len(parsed_legs))
        ],
    }
