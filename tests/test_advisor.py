"""Tests for Meta AI Land Advisor and Kenyan spatial reserve screening."""

from __future__ import annotations

from app.meta.advisor import (
    evaluate_land_parcel,
    identify_kenya_locality,
    screen_kenyan_reserves,
)


def test_identify_kenya_locality_nairobi() -> None:
    # Upper Hill Nairobi
    sm = identify_kenya_locality(36.815, -1.295)
    assert sm.county == "Nairobi"
    assert "Upper Hill" in sm.locality
    assert sm.price_per_acre_kes_min >= 300_000_000


def test_identify_kenya_locality_kiambu() -> None:
    # Ruiru / Thika Road
    sm = identify_kenya_locality(36.960, -1.145)
    assert sm.county == "Kiambu"
    assert "Ruiru" in sm.locality


def test_screen_reserves_clean_residential() -> None:
    # Clean suburban point in Ruiru
    points = [
        (36.960, -1.145),
        (36.962, -1.145),
        (36.962, -1.147),
        (36.960, -1.147),
    ]
    conflicts = screen_kenyan_reserves(points)
    assert len(conflicts) == 0


def test_screen_reserves_karura_forest() -> None:
    # Inside Karura Forest Reserve
    points = [
        (36.830, -1.240),
        (36.832, -1.240),
        (36.832, -1.242),
    ]
    conflicts = screen_kenyan_reserves(points)
    assert len(conflicts) >= 1
    assert any("Karura Forest" in c["name"] for c in conflicts)
    assert conflicts[0]["risk_level"] == "RED"


def test_screen_reserves_national_park() -> None:
    # Inside Nairobi National Park
    points = [
        (36.850, -1.380),
        (36.855, -1.380),
        (36.855, -1.385),
    ]
    conflicts = screen_kenyan_reserves(points)
    assert len(conflicts) >= 1
    assert any("Nairobi National Park" in c["name"] for c in conflicts)


def test_screen_reserves_riparian_corridor() -> None:
    # Inside Nairobi River statutory corridor
    points = [
        (36.840, -1.275),
        (36.842, -1.275),
    ]
    conflicts = screen_kenyan_reserves(points)
    assert len(conflicts) >= 1
    assert any("Riparian" in c["category"] for c in conflicts)


def test_evaluate_land_parcel_clear_buy() -> None:
    # Clean 0.5 hectare (~1.23 acre) parcel in Ruiru
    coords = [
        (36.9600, -1.1450),
        (36.9609, -1.1450),
        (36.9609, -1.1455),
        (36.9600, -1.1455),
    ]
    res = evaluate_land_parcel(coords)
    assert res.is_inside_kenya is True
    assert res.is_safe_residential is True
    assert res.decision_verdict == "CLEAR_BUY"
    assert res.county == "Kiambu"
    assert res.area_m2 > 100.0
    assert res.valuation_kes_mid > 0
    assert "VIABLE ACQUISITION" in res.ai_advisory_text
    assert len(res.due_diligence_steps) >= 5


def test_evaluate_land_parcel_encroached_do_not_buy() -> None:
    # Encroaching on Karura Forest
    coords = [
        (36.830, -1.240),
        (36.835, -1.240),
        (36.835, -1.245),
        (36.830, -1.245),
    ]
    res = evaluate_land_parcel(coords)
    assert res.is_safe_residential is False
    assert res.decision_verdict == "DO_NOT_BUY"
    assert "DO NOT PURCHASE" in res.ai_advisory_text
    assert len(res.reserve_conflicts) > 0


def test_evaluate_land_parcel_overpriced_caution() -> None:
    # Clean parcel in Ruiru with 10x inflated asking price
    coords = [
        (36.9600, -1.1450),
        (36.9609, -1.1450),
        (36.9609, -1.1455),
        (36.9600, -1.1455),
    ]
    res = evaluate_land_parcel(coords, asking_price_kes=800_000_000.0)
    assert res.decision_verdict == "CAUTION"
    assert "OVERPRICED" in res.decision_summary

