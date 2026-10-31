"""Kenyan Cadastral Land Valuation & Due Diligence Advisory Engine.

Provides indicative regional valuation benchmarks across Kenya based on:
- Locality / County (Nairobi, Kiambu, Machakos, Mombasa/Kilifi, Nakuru, Kisumu, Rural)
- Zoning class (Commercial, Urban Residential, Peri-Urban, Agricultural, Coastal)
- Calculated polygon area in acres and hectares

Statutory Disclaimer:
Valuations are indicative estimates based on prevailing regional cadastral benchmarks.
If an official government valuation or registered cadastral listing is identified on
Ardhisasa, the exact statutory figure applies. Always confirm with the Ministry of Lands
Chief Government Valuer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValuationEstimate:
    """Estimated market price range and statutory fees for a Kenyan parcel."""

    locality: str
    county: str
    zoning: str
    area_acres: float
    area_ha: float
    price_min_kes: float
    price_max_kes: float
    formatted_range: str
    rate_per_acre_kes: float
    stamp_duty_estimate_kes: float
    is_exact_record: bool
    source_notes: str
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "locality": self.locality,
            "county": self.county,
            "zoning": self.zoning,
            "area_acres": round(self.area_acres, 3),
            "area_ha": round(self.area_ha, 3),
            "price_min_kes": round(self.price_min_kes, 0),
            "price_max_kes": round(self.price_max_kes, 0),
            "formatted_range": self.formatted_range,
            "rate_per_acre_kes": round(self.rate_per_acre_kes, 0),
            "stamp_duty_estimate_kes": round(self.stamp_duty_estimate_kes, 0),
            "is_exact_record": self.is_exact_record,
            "source_notes": self.source_notes,
            "disclaimer": self.disclaimer,
        }


# Prevailing benchmark rates per acre (KES) by region keywords
REGIONAL_BENCHMARKS: list[dict[str, Any]] = [
    {
        "keywords": ["nairobi", "westlands", "karen", "runda", "kilimani", "upper hill"],
        "county": "Nairobi",
        "zoning": "Prime Urban Commercial / High-Density Residential",
        "rate_min": 60_000_000,
        "rate_max": 120_000_000,
        "rate_avg": 85_000_000,
        "stamp_duty_rate": 0.04,  # 4% in municipalities
    },
    {
        "keywords": ["ruiru", "kiambu", "thika", "kikuyu", "juja", "limuru", "karura"],
        "county": "Kiambu",
        "zoning": "Peri-Urban Residential / Mixed Development",
        "rate_min": 12_000_000,
        "rate_max": 28_000_000,
        "rate_avg": 18_000_000,
        "stamp_duty_rate": 0.04,
    },
    {
        "keywords": [
            "machakos",
            "syokimau",
            "athi river",
            "mavoko",
            "kitengela",
            "ngong",
            "kajiado",
            "rongai",
        ],
        "county": "Machakos / Kajiado",
        "zoning": "Industrial Corridor / Commuter Residential",
        "rate_min": 8_000_000,
        "rate_max": 20_000_000,
        "rate_avg": 14_000_000,
        "stamp_duty_rate": 0.04,
    },
    {
        "keywords": ["mombasa", "nyali", "diani", "kilifi", "malindi", "shanzu", "bamburi"],
        "county": "Mombasa / Kilifi / Kwale",
        "zoning": "Coastal Tourism & Marine Residential",
        "rate_min": 14_000_000,
        "rate_max": 32_000_000,
        "rate_avg": 22_000_000,
        "stamp_duty_rate": 0.04,
    },
    {
        "keywords": ["nakuru", "naivasha", "ol karia", "gilgil", "hells gate"],
        "county": "Nakuru",
        "zoning": "Rift Valley Commercial / Agricultural / Eco-Tourism",
        "rate_min": 4_000_000,
        "rate_max": 12_000_000,
        "rate_avg": 7_500_000,
        "stamp_duty_rate": 0.04,
    },
    {
        "keywords": ["kisumu", "victoria", "milimani", "dunga", "nyalenda"],
        "county": "Kisumu",
        "zoning": "Lakeside Commercial & Residential",
        "rate_min": 5_000_000,
        "rate_max": 15_000_000,
        "rate_avg": 9_000_000,
        "stamp_duty_rate": 0.04,
    },
    {
        "keywords": ["eldoret", "uasin gishu", "kitale", "trans nzoia", "meru", "nyeri"],
        "county": "Highland Agricultural",
        "zoning": "High-Yield Agricultural / Settlement",
        "rate_min": 1_200_000,
        "rate_max": 4_500_000,
        "rate_avg": 2_500_000,
        "stamp_duty_rate": 0.02,  # 2% agricultural / non-municipal
    },
]

DEFAULT_BENCHMARK = {
    "county": "General Kenya Cadastral Zone",
    "zoning": "Suburban / Agricultural Mixed",
    "rate_min": 2_500_000,
    "rate_max": 6_500_000,
    "rate_avg": 4_000_000,
    "stamp_duty_rate": 0.02,
}


def estimate_land_valuation(
    locality: str,
    district: str,
    computed_m2: float,
    stated_m2: float = 0.0,
    exact_price_kes: float | None = None,
    lr_number: str = "",
) -> ValuationEstimate:
    """Calculate indicative market valuation range and statutory acquisition fees."""
    # Preferred area is computed m2 from coordinates, fallback to stated
    effective_m2 = computed_m2 if computed_m2 > 10 else stated_m2
    area_acres = effective_m2 / 4046.8564224
    area_ha = effective_m2 / 10000.0

    # Match benchmark by keyword
    search_text = f"{locality} {district} {lr_number}".lower()
    matched_bench = DEFAULT_BENCHMARK
    for bench in REGIONAL_BENCHMARKS:
        if any(kw in search_text for kw in bench["keywords"]):
            matched_bench = bench
            break

    # If exact listed / gazetted price is known
    if exact_price_kes and exact_price_kes > 0:
        price_min = exact_price_kes
        price_max = exact_price_kes
        rate_acre = price_min / max(area_acres, 0.01)
        formatted_range = f"KES {exact_price_kes:,.0f} (Exact Official Listing)"
        is_exact = True
        notes = "Exact registered valuation record confirmed."
    else:
        is_exact = False
        rate_min = matched_bench["rate_min"]
        rate_max = matched_bench["rate_max"]
        rate_avg = matched_bench["rate_avg"]

        # Ensure small plots (e.g. 1/8 acre = 0.125 acre, 1/4 acre = 0.25 acre) scale correctly
        scale_area = max(area_acres, 0.05)
        price_min = rate_min * scale_area
        price_max = rate_max * scale_area
        rate_acre = rate_avg

        # Format human readable range
        if price_max >= 1_000_000:
            formatted_range = (
                f"KES {price_min/1_000_000:.2f}M - KES {price_max/1_000_000:.2f}M"
            )
        else:
            formatted_range = f"KES {price_min:,.0f} - KES {price_max:,.0f}"

        notes = (
            f"Indicative market estimate based on {matched_bench['county']} "
            f"cadastral benchmark (~KES {rate_avg/1_000_000:.1f}M / acre)."
        )

    # Stamp duty estimate (4% for urban municipalities, 2% for rural)
    stamp_duty = price_min * matched_bench.get("stamp_duty_rate", 0.04)

    disclaimer = (
        "Indicative market estimate for due diligence budgeting only. "
        "Not an official bank or government appraisal. "
        "Statutory transfer fees require confirmation from the Ministry of Lands "
        "Chief Government Valuer."
    )

    return ValuationEstimate(
        locality=locality or matched_bench["county"],
        county=matched_bench["county"],
        zoning=matched_bench["zoning"],
        area_acres=area_acres,
        area_ha=area_ha,
        price_min_kes=price_min,
        price_max_kes=price_max,
        formatted_range=formatted_range,
        rate_per_acre_kes=rate_acre,
        stamp_duty_estimate_kes=stamp_duty,
        is_exact_record=is_exact,
        source_notes=notes,
        disclaimer=disclaimer,
    )
