"""Tests for app.geo.area – area computation and unit conversion."""

import pytest

from app.geo.area import compare_stated_area, convert_area, polygon_area_m2


class TestPolygonArea:
    """Shoelace area computation."""

    def test_rectangle_100x50(self):
        """100 m × 50 m rectangle = 5000 m²."""
        coords = [
            (0.0, 0.0),
            (0.0, 100.0),
            (50.0, 100.0),
            (50.0, 0.0),
        ]
        assert polygon_area_m2(coords) == pytest.approx(5000.0)

    def test_rectangle_closed_polygon(self):
        """Same rectangle but with explicit closing vertex."""
        coords = [
            (0.0, 0.0),
            (0.0, 100.0),
            (50.0, 100.0),
            (50.0, 0.0),
            (0.0, 0.0),
        ]
        assert polygon_area_m2(coords) == pytest.approx(5000.0)

    def test_right_triangle(self):
        """Right triangle with base 40, height 30 = 600 m²."""
        coords = [
            (0.0, 0.0),
            (40.0, 0.0),
            (40.0, 30.0),
        ]
        assert polygon_area_m2(coords) == pytest.approx(600.0)

    def test_unit_square(self):
        coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert polygon_area_m2(coords) == pytest.approx(1.0)

    def test_fewer_than_3_raises(self):
        with pytest.raises(ValueError, match="at least 3"):
            polygon_area_m2([(0, 0), (1, 1)])


class TestConvertArea:
    """Area unit conversions."""

    def test_m2_to_ha(self):
        """10000 m² = 1 ha."""
        assert convert_area(10_000.0, "m2", "ha") == pytest.approx(1.0)

    def test_ha_to_m2(self):
        """1 ha = 10000 m²."""
        assert convert_area(1.0, "ha", "m2") == pytest.approx(10_000.0)

    def test_m2_to_acre(self):
        """1 acre = 4046.8564224 m²."""
        assert convert_area(4046.8564224, "m2", "acre") == pytest.approx(1.0)

    def test_acre_to_m2(self):
        assert convert_area(1.0, "acre", "m2") == pytest.approx(4046.8564224)

    def test_ha_to_acre(self):
        assert convert_area(1.0, "ha", "acre") == pytest.approx(10_000.0 / 4046.8564224)

    def test_identity_conversion(self):
        assert convert_area(42.0, "m2", "m2") == pytest.approx(42.0)

    def test_5000m2_in_ha(self):
        """5000 m² = 0.5 ha (the rectangle from the spec)."""
        assert convert_area(5000.0, "m2", "ha") == pytest.approx(0.5)

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            convert_area(1.0, "ft2", "m2")

    def test_unknown_target_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            convert_area(1.0, "m2", "sqft")


class TestCompareStatedArea:
    """Stated vs computed area comparison."""

    def test_matching_area(self):
        result = compare_stated_area(0.5, "ha", 5000.0)
        assert result["within_tolerance"]
        assert result["difference_pct"] == pytest.approx(0.0)

    def test_area_within_tolerance(self):
        # 0.5 ha stated, computed 5050 m² → 1% difference
        result = compare_stated_area(0.5, "ha", 5050.0, tolerance_pct=2.0)
        assert result["within_tolerance"]
        assert result["difference_pct"] == pytest.approx(1.0)

    def test_area_outside_tolerance(self):
        # 0.5 ha stated, computed 5200 m² → 4% difference
        result = compare_stated_area(0.5, "ha", 5200.0, tolerance_pct=2.0)
        assert not result["within_tolerance"]
        assert result["difference_pct"] == pytest.approx(4.0)

    def test_zero_stated_raises(self):
        with pytest.raises(ValueError, match="positive"):
            compare_stated_area(0, "ha", 5000.0)
