"""Tests for Kenyan protected reserve screening and layer attribution (app.geo.reserves)."""

from __future__ import annotations

from app.geo.reserves import (
    get_layer_metadata,
    is_inside_kenya,
    screen_reserves_pure,
)


def test_is_inside_kenya() -> None:
    # Nairobi point
    assert is_inside_kenya(36.8172, -1.2864) is True
    # Mombasa point
    assert is_inside_kenya(39.6682, -4.0435) is True
    # Point outside Kenya (London)
    assert is_inside_kenya(-0.1276, 51.5074) is False


def test_screen_reserves_clean() -> None:
    # Clean suburban parcel in Ruiru
    coords = [
        (36.9600, -1.1450),
        (36.9609, -1.1450),
        (36.9609, -1.1455),
        (36.9600, -1.1455),
    ]
    conflicts = screen_reserves_pure(coords)
    assert len(conflicts) == 0


def test_screen_reserves_karura_forest() -> None:
    # Inside Karura Forest Reserve
    coords = [
        (36.830, -1.240),
        (36.835, -1.240),
        (36.835, -1.245),
        (36.830, -1.245),
    ]
    conflicts = screen_reserves_pure(coords)
    assert len(conflicts) >= 1
    assert any("Karura Forest" in c["name"] for c in conflicts)
    assert any("Forest Conservation and Management Act" in c["statute"] for c in conflicts)
    assert conflicts[0]["is_illustrative"] is True
    assert conflicts[0]["source"] != ""
    assert conflicts[0]["licence"] != ""


def test_screen_reserves_national_park() -> None:
    # Inside Nairobi National Park
    coords = [
        (36.850, -1.380),
        (36.855, -1.380),
        (36.855, -1.385),
    ]
    conflicts = screen_reserves_pure(coords)
    assert len(conflicts) >= 1
    assert any("Nairobi National Park" in c["name"] for c in conflicts)
    assert any("Wildlife Conservation" in c["statute"] for c in conflicts)


def test_screen_reserves_configurable_riparian_buffer() -> None:
    # Nairobi River corridor with custom buffer widths
    coords = [
        (36.840, -1.275),
        (36.842, -1.275),
    ]
    # Test default 30m buffer
    conflicts_30m = screen_reserves_pure(coords, riparian_buffer_m=30.0)
    assert len(conflicts_30m) >= 1
    riparian_conf = [c for c in conflicts_30m if c["category"] == "Riparian Buffer"][0]
    assert riparian_conf["configured_riparian_buffer_m"] == 30.0
    assert "Survey Act Cap 299" in riparian_conf["statute"]

    # Test custom 15m buffer
    conflicts_15m = screen_reserves_pure(coords, riparian_buffer_m=15.0)
    assert len(conflicts_15m) >= 1
    riparian_conf_15m = [c for c in conflicts_15m if c["category"] == "Riparian Buffer"][0]
    assert riparian_conf_15m["configured_riparian_buffer_m"] == 15.0


def test_layer_attribution_and_licences() -> None:
    layers = get_layer_metadata()
    assert len(layers) >= 4
    layer_names = [lyr["layer_name"] for lyr in layers]
    assert "OpenStreetMap Standard" in layer_names
    assert "Esri World Imagery" in layer_names
    assert any("Forests" in name for name in layer_names)
    assert any("Riparian" in name for name in layer_names)

    # Confirm all layers have source, licence, and explicit illustrative flag
    for lyr in layers:
        assert "source" in lyr and len(lyr["source"]) > 0
        assert "licence" in lyr and len(lyr["licence"]) > 0
        assert "is_illustrative" in lyr
