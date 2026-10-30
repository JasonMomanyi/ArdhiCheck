"""Generate realistic Kenyan survey plan diagrams and satellite clips for demo testing.

Creates 4 realistic test scenarios:
1. scenario_1_clean: Clean 0.5 ha parcel in Nairobi (Pass / Green).
2. scenario_2_transposed_bearing: 0.5 ha parcel with transposed bearing 009° vs 090° (Amber).
3. scenario_3_riparian_overlap: Parcel abutting a river reserve with 30m buffer overlap (Red).
4. scenario_4_area_mismatch: Stated 2.50 Acres, computed 1.75 Acres (Red).
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


def _draw_survey_plan(
    filename: Path,
    title: str,
    lr_number: str,
    district: str,
    locality: str,
    legs: list[tuple[str, str]],
    stated_area: str,
    datum_text: str,
    notes: list[str],
) -> None:
    """Render a survey plan image mimicking Kenyan Survey Regulations deed plans."""
    width, height = 1200, 1600
    img = Image.new("RGB", (width, height), color=(252, 250, 242))  # light parchment paper
    draw = ImageDraw.Draw(img)

    # Outer border (Survey regulations style)
    draw.rectangle([(30, 30), (width - 30, height - 30)], outline=(40, 40, 40), width=3)
    draw.rectangle([(38, 38), (width - 38, height - 38)], outline=(40, 40, 40), width=1)

    # Header title
    draw.text((width // 2, 80), "SURVEY OF KENYA", fill=(20, 20, 20), anchor="mm")
    draw.text(
        (width // 2, 115), "DEED PLAN / BOUNDARY SURVEY PLAN", fill=(40, 40, 40), anchor="mm"
    )
    draw.line([(60, 140), (width - 60, 140)], fill=(40, 40, 40), width=2)

    # Metadata block
    meta_lines = [
        f"L.R. NUMBER: {lr_number}",
        f"DISTRICT: {district} | LOCALITY: {locality}",
        f"STATED AREA: {stated_area}",
        f"DATUM / PROJECTION: {datum_text}",
    ]
    y = 160
    for line in meta_lines:
        draw.text((70, y), line, fill=(30, 30, 30))
        y += 28

    draw.line([(60, y + 10), (width - 60, y + 10)], fill=(120, 120, 120), width=1)
    y += 30

    # Draw Diagram Box
    diag_box = [(70, y), (width - 70, y + 600)]
    draw.rectangle(diag_box, outline=(80, 80, 80), fill=(255, 255, 255), width=2)

    # North Arrow
    na_x, na_y = width - 150, y + 80
    draw.line([(na_x, na_y + 40), (na_x, na_y - 40)], fill=(180, 0, 0), width=3)
    draw.polygon(
        [(na_x, na_y - 50), (na_x - 12, na_y - 30), (na_x + 12, na_y - 30)], fill=(180, 0, 0)
    )
    draw.text((na_x, na_y - 65), "GRID NORTH", fill=(180, 0, 0), anchor="mm")

    # Draw Cadastral Polygon inside the diagram box
    center_x = (diag_box[0][0] + diag_box[1][0]) // 2 - 40
    center_y = (diag_box[0][1] + diag_box[1][1]) // 2

    # A rectangle or polygon representation
    poly_pts = [
        (center_x - 180, center_y + 120),
        (center_x - 180, center_y - 120),
        (center_x + 180, center_y - 120),
        (center_x + 180, center_y + 120),
    ]
    draw.polygon(poly_pts, outline=(0, 60, 160), fill=(235, 245, 255), width=4)

    # Generate beacons dynamically
    num_legs = len(legs)
    beacons = [f"BP{i + 1}" for i in range(num_legs)]
    for i, pt in enumerate(poly_pts[:num_legs]):
        draw.ellipse(
            [(pt[0] - 6, pt[1] - 6), (pt[0] + 6, pt[1] + 6)],
            fill=(200, 0, 0),
            outline=(0, 0, 0),
            width=2,
        )
        offset = [(-25, 15), (-25, -20), (20, -20), (20, 15), (0, 25)][i % 5]
        draw.text((pt[0] + offset[0], pt[1] + offset[1]), beacons[i], fill=(160, 0, 0))

    # Annotate sides with bearings & distances
    for i in range(min(4, num_legs)):
        side_annotations = [
            (center_x - 240, center_y, f"{legs[0][0]}  {legs[0][1]}m"),
            (center_x, center_y - 150, f"{legs[1][0]}  {legs[1][1]}m"),
            (center_x + 200, center_y, f"{legs[2][0]}  {legs[2][1]}m"),
            (center_x, center_y + 140, f"{legs[3][0]}  {legs[3][1]}m"),
        ]
        ax, ay, text = side_annotations[i]
        draw.text((ax, ay), text, fill=(10, 50, 120), anchor="mm")

    # Plot details badge in center of polygon
    draw.text((center_x, center_y - 10), lr_number, fill=(20, 20, 20), anchor="mm")
    draw.text((center_x, center_y + 15), stated_area, fill=(80, 80, 80), anchor="mm")

    # Table of Traverse Observations
    tbl_y = y + 640
    draw.text((70, tbl_y), "SCHEDULE OF BOUNDARY TRAVERSE READINGS", fill=(20, 20, 20))
    tbl_y += 30

    col_widths = [150, 150, 300, 250]
    headers = ["FROM", "TO", "BEARING (DMS)", "DISTANCE (M)"]
    draw.rectangle(
        [(70, tbl_y), (width - 70, tbl_y + 35)],
        fill=(220, 225, 230),
        outline=(80, 80, 80),
        width=2,
    )
    cx = 85
    for h_idx, h in enumerate(headers):
        draw.text((cx, tbl_y + 10), h, fill=(10, 10, 10))
        cx += col_widths[h_idx]

    tbl_y += 35
    for idx, (b_txt, d_txt) in enumerate(legs):
        from_b = beacons[idx]
        to_b = beacons[(idx + 1) % len(beacons)]
        row_bg = (248, 248, 248) if idx % 2 == 0 else (255, 255, 255)
        draw.rectangle(
            [(70, tbl_y), (width - 70, tbl_y + 35)], fill=row_bg, outline=(150, 150, 150), width=1
        )
        cx = 85
        row_vals = [from_b, to_b, b_txt, f"{float(d_txt):.3f}"]
        for r_idx, val in enumerate(row_vals):
            draw.text((cx, tbl_y + 8), val, fill=(20, 20, 20))
            cx += col_widths[r_idx]
        tbl_y += 35

    # Legal notes and stamps
    tbl_y += 30
    draw.text((70, tbl_y), "SURVEYOR'S CERTIFICATE & NOTES:", fill=(20, 20, 20))
    tbl_y += 25
    for n in notes:
        draw.text((85, tbl_y), f"• {n}", fill=(60, 60, 60))
        tbl_y += 24

    # Stamp
    stamp_box = [(width - 320, tbl_y - 10), (width - 80, tbl_y + 110)]
    draw.rectangle(stamp_box, outline=(160, 40, 40), width=2)
    stamp_cx = (stamp_box[0][0] + stamp_box[1][0]) // 2
    draw.text((stamp_cx, tbl_y + 15), "LICENSED SURVEYOR", fill=(160, 40, 40), anchor="mm")
    draw.text((stamp_cx, tbl_y + 40), "REPUBLIC OF KENYA", fill=(160, 40, 40), anchor="mm")
    draw.text((stamp_cx, tbl_y + 65), "SURVEY ACT CAP 299", fill=(160, 40, 40), anchor="mm")
    draw.text((stamp_cx, tbl_y + 90), "AUTHENTICATED", fill=(160, 40, 40), anchor="mm")

    filename.parent.mkdir(parents=True, exist_ok=True)
    img.save(filename, format="PNG")


def _draw_satellite_clip(
    filename: Path,
    title: str,
    feature_type: str | None = None,
    overlap_box: tuple[int, int, int, int] | None = None,
) -> None:
    """Render a synthetic satellite / aerial patch (simulating Google Earth / Sentinel-2)."""
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color=(48, 75, 42))  # foliage green
    draw = ImageDraw.Draw(img)

    # Draw agricultural / terrain texture variations
    draw.rectangle([(0, 0), (400, 300)], fill=(55, 82, 45))
    draw.rectangle([(400, 0), (800, 300)], fill=(62, 88, 48))
    draw.rectangle([(0, 300), (450, 600)], fill=(42, 68, 38))
    draw.rectangle([(450, 300), (800, 600)], fill=(50, 78, 44))

    # Road alignment (Access road)
    draw.line([(0, 520), (800, 480)], fill=(140, 135, 125), width=24)
    draw.line([(0, 520), (800, 480)], fill=(220, 220, 220), width=2)  # road markings

    # Parcel Outline (Cadastral boundary in yellow)
    parcel_poly = [(250, 150), (250, 350), (550, 350), (550, 150)]
    draw.polygon(parcel_poly, outline=(255, 235, 0), width=3)
    draw.text((400, 250), "PARCEL PLOT", fill=(255, 255, 255), anchor="mm")

    if feature_type == "river":
        # Draw winding river along the right / top side
        river_pts = [(520, 0), (560, 120), (600, 250), (640, 400), (680, 600)]
        for i in range(len(river_pts) - 1):
            p1 = river_pts[i]
            p2 = river_pts[i + 1]
            # Riparian buffer 30m zone (transparent / tinted zone)
            draw.line([p1, p2], fill=(80, 160, 100), width=90)
            # Water channel
            draw.line([p1, p2], fill=(45, 95, 140), width=36)
        draw.text((640, 280), "NAIROBI RIVER BASIN", fill=(200, 240, 255), anchor="mm")
        draw.text((580, 180), "30M RIPARIAN BUFFER", fill=(255, 200, 150), anchor="mm")

        # Highlight overlap encroachment area in translucent red
        if overlap_box:
            draw.rectangle(overlap_box, outline=(255, 40, 40), fill=(220, 30, 30), width=2)
            draw.text(
                ((overlap_box[0] + overlap_box[2]) // 2, (overlap_box[1] + overlap_box[3]) // 2),
                "ENCROACHMENT\nOVERLAP 240m²",
                fill=(255, 255, 255),
                anchor="mm",
            )

    # Satellite metadata overlay (Google Earth / Sentinel-2 style HUD)
    draw.rectangle([(10, height - 35), (width - 10, height - 10)], fill=(0, 0, 0))
    draw.text(
        (20, height - 28),
        "IMAGERY: Sentinel-2 / Copernicus (10m) & Google Earth High-Res Overlay",
        fill=(220, 220, 220),
    )
    draw.text((width - 200, height - 28), "1:2,500 | Kenya Grid", fill=(180, 180, 180))

    filename.parent.mkdir(parents=True, exist_ok=True)
    img.save(filename, format="PNG")


def main() -> None:
    data_dir = Path("data/examples")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean Deed Plan (Pass / Green)
    p1 = data_dir / "scenario_1_clean_plan.png"
    s1 = data_dir / "scenario_1_satellite.png"
    meta1 = {
        "id": "scenario_1_clean",
        "title": "Clean Survey Plan - Nairobi Upper Hill",
        "lr_number": "L.R. 209/14582",
        "district": "Nairobi",
        "locality": "Upper Hill / Community",
        "stated_area": 0.50,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm37s",
        "start_coords": [257000.0, 9857000.0],
        "legs": [
            ("000°00'00\"", "100.000"),
            ("090°00'00\"", "50.000"),
            ("180°00'00\"", "100.000"),
            ("270°00'00\"", "50.000"),
        ],
        "expected_verdict": "GREEN",
        "notes": [
            "All boundary beacons found in situ (iron pins in concrete).",
            "Survey carried out in accordance with Survey Act Cap 299.",
            "Traverse closes with zero linear error.",
        ],
    }
    _draw_survey_plan(
        p1,
        title=meta1["title"],
        lr_number=meta1["lr_number"],
        district=meta1["district"],
        locality=meta1["locality"],
        legs=meta1["legs"],
        stated_area="0.500 Ha (approx 1.235 Acres)",
        datum_text="Arc 1960 / UTM Zone 37S (EPSG 21037)",
        notes=meta1["notes"],
    )
    _draw_satellite_clip(s1, title=meta1["title"])
    (data_dir / "scenario_1.json").write_text(json.dumps(meta1, indent=2))

    # 2. Transposed Bearing Blunder (Amber / Typo localized)
    p2 = data_dir / "scenario_2_transposed_plan.png"
    s2 = data_dir / "scenario_2_satellite.png"
    meta2 = {
        "id": "scenario_2_transposed",
        "title": "Transposed Bearing Blunder - Nakuru Municipality",
        "lr_number": "L.R. 8421/39",
        "district": "Nakuru",
        "locality": "Milimani Estate",
        "stated_area": 0.50,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm36s",
        "start_coords": [182000.0, 9965000.0],
        "legs": [
            ("000°00'00\"", "100.000"),
            ("009°00'00\"", "50.000"),  # Transposed from 090°00'00"
            ("180°00'00\"", "100.000"),
            ("270°00'00\"", "50.000"),
        ],
        "expected_verdict": "AMBER",
        "notes": [
            "Survey conducted using total station equipment.",
            "Suspected clerical transposition in leg BP2-BP3 azimuth.",
            "ArdhiCheck Error Localiser identifies 009° -> 090° correction.",
        ],
    }
    _draw_survey_plan(
        p2,
        title=meta2["title"],
        lr_number=meta2["lr_number"],
        district=meta2["district"],
        locality=meta2["locality"],
        legs=meta2["legs"],
        stated_area="0.500 Ha",
        datum_text="Arc 1960 / UTM Zone 36S (EPSG 21036)",
        notes=meta2["notes"],
    )
    _draw_satellite_clip(s2, title=meta2["title"])
    (data_dir / "scenario_2.json").write_text(json.dumps(meta2, indent=2))

    # 3. Riparian Reserve Encroachment (Red / Site Fail)
    p3 = data_dir / "scenario_3_riparian_plan.png"
    s3 = data_dir / "scenario_3_satellite.png"
    meta3 = {
        "id": "scenario_3_riparian",
        "title": "Riparian Reserve Overlap - Kiambu / Nairobi River",
        "lr_number": "L.R. 11942/8",
        "district": "Kiambu",
        "locality": "Ruaka / Karura River Basin",
        "stated_area": 0.50,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm37s",
        "start_coords": [254000.0, 9864000.0],
        "legs": [
            ("000°00'00\"", "100.000"),
            ("090°00'00\"", "50.000"),
            ("180°00'00\"", "100.000"),
            ("270°00'00\"", "50.000"),
        ],
        "has_riparian_overlap": True,
        "overlap_area_m2": 240.0,
        "expected_verdict": "RED",
        "notes": [
            "Bordering perennial stream / river reserve on Eastern flank.",
            "Environmental Management and Coordination Act (EMCA) requires 30m buffer.",
            "Satellite clip shows building/fence inside protected riparian reserve.",
        ],
    }
    _draw_survey_plan(
        p3,
        title=meta3["title"],
        lr_number=meta3["lr_number"],
        district=meta3["district"],
        locality=meta3["locality"],
        legs=meta3["legs"],
        stated_area="0.500 Ha",
        datum_text="Arc 1960 / UTM Zone 37S (EPSG 21037)",
        notes=meta3["notes"],
    )
    _draw_satellite_clip(
        s3,
        title=meta3["title"],
        feature_type="river",
        overlap_box=(520, 150, 550, 230),
    )
    (data_dir / "scenario_3.json").write_text(json.dumps(meta3, indent=2))

    # 4. Area Discrepancy (Red / Geometric Deficit)
    p4 = data_dir / "scenario_4_area_deficit_plan.png"
    s4 = data_dir / "scenario_4_satellite.png"
    meta4 = {
        "id": "scenario_4_area_mismatch",
        "title": "Stated Area Discrepancy - Eldoret Municipality",
        "lr_number": "L.R. 6140/11",
        "district": "Uasin Gishu",
        "locality": "Eldoret Town",
        "stated_area": 1.20,  # Claimed 1.20 Ha (12,000 m2)
        "stated_unit": "ha",
        "crs_name": "arc1960_utm36n",
        "start_coords": [198000.0, 58000.0],
        "legs": [
            ("000°00'00\"", "100.000"),
            ("090°00'00\"", "50.000"),
            ("180°00'00\"", "100.000"),
            ("270°00'00\"", "50.000"),
        ],  # Geometry only has 5,000 m2 (0.50 Ha) -> 58% discrepancy!
        "expected_verdict": "RED",
        "notes": [
            "Deed states 1.20 Ha (approx 2.96 Acres).",
            "Survey coordinates calculate to only 0.500 Ha (5,000 m²).",
            "Severe area inflation detected. Potential land title fraud.",
        ],
    }
    _draw_survey_plan(
        p4,
        title=meta4["title"],
        lr_number=meta4["lr_number"],
        district=meta4["district"],
        locality=meta4["locality"],
        legs=meta4["legs"],
        stated_area="1.200 Ha (Inflated Claim)",
        datum_text="Arc 1960 / UTM Zone 36N (EPSG 21096)",
        notes=meta4["notes"],
    )
    _draw_satellite_clip(s4, title=meta4["title"])
    (data_dir / "scenario_4.json").write_text(json.dumps(meta4, indent=2))

    # 5. Coastal Beach Plot - Mombasa Nyali (Pass / Green - Irregular 5-sided perimeter)
    p5 = data_dir / "scenario_5_nyali_beach_plan.png"
    s5 = data_dir / "scenario_5_satellite.png"
    meta5 = {
        "id": "scenario_5_nyali_beach",
        "title": "Mombasa Nyali Coastal Plot (5-Sided Perimeter)",
        "lr_number": "L.R. MN/I/5432",
        "district": "Mombasa",
        "locality": "Nyali Beachfront / Links Road",
        "stated_area": 1.25,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm37s",
        "start_coords": [573000.0, 9553000.0],
        "legs": [
            ("015°00'00\"", "120.000"),
            ("095°00'00\"", "105.000"),
            ("165°00'00\"", "115.000"),
            ("245°00'00\"", "80.000"),
            ("290°36'12\"", "45.280"),
        ],
        "expected_verdict": "GREEN",
        "notes": [
            "Cadastral survey of prime coastal residential/hotel development parcel.",
            "Traverse loop closes within statutory 1:10,000 Class A precision.",
            "Outside 60m high-water mark tidal statutory setback.",
        ],
    }
    _draw_survey_plan(
        p5,
        title=meta5["title"],
        lr_number=meta5["lr_number"],
        district=meta5["district"],
        locality=meta5["locality"],
        legs=meta5["legs"],
        stated_area="1.250 Ha",
        datum_text="Arc 1960 / UTM Zone 37S (EPSG 21037)",
        notes=meta5["notes"],
    )
    _draw_satellite_clip(s5, title=meta5["title"])
    (data_dir / "scenario_5.json").write_text(json.dumps(meta5, indent=2))

    # 6. Industrial Logistics Park - Machakos / Athi River (Pass / Green)
    p6 = data_dir / "scenario_6_athi_river_plan.png"
    s6 = data_dir / "scenario_6_satellite.png"
    meta6 = {
        "id": "scenario_6_athi_river",
        "title": "Athi River Industrial Logistics Park",
        "lr_number": "L.R. 12800/4",
        "district": "Machakos",
        "locality": "Athi River / Mombasa Road Corridor",
        "stated_area": 2.50,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm37s",
        "start_coords": [278000.0, 9839000.0],
        "legs": [
            ("000°00'00\"", "200.000"),
            ("090°00'00\"", "125.000"),
            ("180°00'00\"", "200.000"),
            ("270°00'00\"", "125.000"),
        ],
        "expected_verdict": "GREEN",
        "notes": [
            "Heavy industrial warehousing zoned parcel.",
            "Traverse closes with zero linear error; perimeter 650.0m.",
            "Clear of SGR railway reserve buffer and highway setback.",
        ],
    }
    _draw_survey_plan(
        p6,
        title=meta6["title"],
        lr_number=meta6["lr_number"],
        district=meta6["district"],
        locality=meta6["locality"],
        legs=meta6["legs"],
        stated_area="2.500 Ha",
        datum_text="Arc 1960 / UTM Zone 37S (EPSG 21037)",
        notes=meta6["notes"],
    )
    _draw_satellite_clip(s6, title=meta6["title"])
    (data_dir / "scenario_6.json").write_text(json.dumps(meta6, indent=2))

    # 7. Lake Victoria Buffer Zone - Kisumu (Fail / Red - Riparian)
    p7 = data_dir / "scenario_7_kisumu_lakefront_plan.png"
    s7 = data_dir / "scenario_7_satellite.png"
    meta7 = {
        "id": "scenario_7_kisumu_lakefront",
        "title": "Kisumu Dunga Lake Victoria Buffer Zone Overlap",
        "lr_number": "L.R. KSM/BLOCK 14/89",
        "district": "Kisumu",
        "locality": "Dunga Beach / Lake Victoria Shore",
        "stated_area": 0.75,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm36s",
        "start_coords": [693000.0, 9987000.0],
        "legs": [
            ("020°00'00\"", "100.000"),
            ("110°00'00\"", "75.000"),
            ("200°00'00\"", "100.000"),
            ("290°00'00\"", "75.000"),
        ],
        "has_riparian_overlap": True,
        "overlap_area_m2": 450.0,
        "expected_verdict": "RED",
        "notes": [
            "Direct frontage on Lake Victoria high-water buffer.",
            "Violates statutory 100m lake protection zone (Survey Act & EMCA).",
            "High risk of reclamation or structure demolition by NEMA.",
        ],
    }
    _draw_survey_plan(
        p7,
        title=meta7["title"],
        lr_number=meta7["lr_number"],
        district=meta7["district"],
        locality=meta7["locality"],
        legs=meta7["legs"],
        stated_area="0.750 Ha",
        datum_text="Arc 1960 / UTM Zone 36S (EPSG 21036)",
        notes=meta7["notes"],
    )
    _draw_satellite_clip(s7, title=meta7["title"], feature_type="river")
    (data_dir / "scenario_7.json").write_text(json.dumps(meta7, indent=2))

    # 8. Naivasha Wildlife & Energy Corridor (Fail / Red - Reserve Overlap)
    p8 = data_dir / "scenario_8_naivasha_corridor_plan.png"
    s8 = data_dir / "scenario_8_satellite.png"
    meta8 = {
        "id": "scenario_8_naivasha_corridor",
        "title": "Naivasha Geothermal & Wildlife Corridor Encroachment",
        "lr_number": "L.R. 3981/15",
        "district": "Nakuru",
        "locality": "Lake Naivasha / Olkaria Buffer",
        "stated_area": 3.20,
        "stated_unit": "ha",
        "crs_name": "arc1960_utm37s",
        "start_coords": [205000.0, 9918000.0],
        "legs": [
            ("045°00'00\"", "200.000"),
            ("135°00'00\"", "160.000"),
            ("225°00'00\"", "200.000"),
            ("315°00'00\"", "160.000"),
        ],
        "has_riparian_overlap": True,
        "expected_verdict": "RED",
        "notes": [
            "Survey overlaps gazetted KWS wildlife dispersal corridor.",
            "Infringes upon KenGen high-pressure geothermal pipeline wayleave.",
            "Title cannot be registered; deed plan revoked under Cap 299.",
        ],
    }
    _draw_survey_plan(
        p8,
        title=meta8["title"],
        lr_number=meta8["lr_number"],
        district=meta8["district"],
        locality=meta8["locality"],
        legs=meta8["legs"],
        stated_area="3.200 Ha",
        datum_text="Arc 1960 / UTM Zone 37S (EPSG 21037)",
        notes=meta8["notes"],
    )
    _draw_satellite_clip(s8, title=meta8["title"])
    (data_dir / "scenario_8.json").write_text(json.dumps(meta8, indent=2))

    # Build Downloads directory with CSV, GeoJSON and ZIP
    downloads_dir = data_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    # 1. CSV coordinates
    csv1 = downloads_dir / "nairobi_upperhill_lr209_14682.csv"
    csv1.write_text(
        "Leg,Bearing_DMS,Distance_m\n"
        "1,000°00'00\",100.000\n"
        "2,090°00'00\",50.000\n"
        "3,180°00'00\",100.000\n"
        "4,270°00'00\",50.000\n",
        encoding="utf-8",
    )

    csv2 = downloads_dir / "nakuru_residential_lr8421_39.csv"
    csv2.write_text(
        "Leg,Bearing_DMS,Distance_m,Notes\n"
        "1,000°00'00\",100.000,BP1 to BP2\n"
        "2,009°00'00\",50.000,BP2 to BP3 (Transposed typo 009 vs 090)\n"
        "3,180°00'00\",100.000,BP3 to BP4\n"
        "4,270°00'00\",50.000,BP4 to BP1\n",
        encoding="utf-8",
    )

    csv6 = downloads_dir / "athi_river_industrial_lr12800_4.csv"
    csv6.write_text(
        "Leg,Bearing_DMS,Distance_m\n"
        "1,000°00'00\",200.000\n"
        "2,090°00'00\",125.000\n"
        "3,180°00'00\",200.000\n"
        "4,270°00'00\",125.000\n",
        encoding="utf-8",
    )

    # 2. GeoJSON boundaries
    geojson1 = downloads_dir / "nairobi_upperhill_lr209_14682.geojson"
    geojson1.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "lr_number": "L.R. 209/14682",
                        "locality": "Upper Hill, Nairobi",
                        "stated_area_ha": 0.50,
                        "datum": "Arc 1960 / UTM Zone 37S"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [36.8160, -1.2990],
                            [36.8160, -1.2981],
                            [36.8164, -1.2981],
                            [36.8164, -1.2990],
                            [36.8160, -1.2990]
                        ]]
                    }
                }
            ]
        }, indent=2),
        encoding="utf-8",
    )

    # 3. Create a master ZIP archive of all sample datasets
    import zipfile
    zip_path = downloads_dir / "ArdhiCheck_Kenya_Test_Survey_Pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(data_dir.glob("scenario_*_plan.png")):
            zf.write(p, arcname=f"plans/{p.name}")
        for s in sorted(data_dir.glob("scenario_*_satellite.png")):
            zf.write(s, arcname=f"satellite/{s.name}")
        for j in sorted(data_dir.glob("scenario_*.json")):
            zf.write(j, arcname=f"metadata/{j.name}")
        zf.write(csv1, arcname=f"tables/{csv1.name}")
        zf.write(csv2, arcname=f"tables/{csv2.name}")
        zf.write(csv6, arcname=f"tables/{csv6.name}")
        zf.write(geojson1, arcname=f"gis/{geojson1.name}")

    print("Generated 8 realistic Kenyan demo scenarios & downloadable test survey pack in data/examples/")


if __name__ == "__main__":
    main()
