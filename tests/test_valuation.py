"""Unit tests for Kenyan land valuation and due diligence advisory."""

import pytest

from app.geo.valuation import estimate_land_valuation


def test_valuation_nairobi_urban():
    val = estimate_land_valuation(
        locality="Karen, Nairobi",
        district="Nairobi",
        computed_m2=4046.85,  # 1 acre
    )
    assert val.county == "Nairobi"
    assert val.price_min_kes >= 50_000_000
    assert "M" in val.formatted_range
    assert val.stamp_duty_estimate_kes > 0
    assert val.is_exact_record is False
    assert "Indicative market estimate" in val.source_notes


def test_valuation_kiambu_peri_urban():
    val = estimate_land_valuation(
        locality="Ruiru",
        district="Kiambu",
        computed_m2=2023.4,  # 0.5 acre
    )
    assert val.county == "Kiambu"
    assert val.price_min_kes > 5_000_000
    assert val.area_acres == pytest.approx(0.5, abs=0.05)


def test_valuation_exact_price():
    val = estimate_land_valuation(
        locality="Naivasha",
        district="Nakuru",
        computed_m2=4046.85,
        exact_price_kes=12_500_000,
    )
    assert val.is_exact_record is True
    assert val.price_min_kes == 12_500_000
    assert "Exact Official Listing" in val.formatted_range


def test_valuation_to_dict():
    val = estimate_land_valuation("Syokimau", "Machakos", 1000.0)
    d = val.to_dict()
    assert "formatted_range" in d
    assert "stamp_duty_estimate_kes" in d
    assert "disclaimer" in d
