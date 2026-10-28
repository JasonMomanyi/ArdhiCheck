"""Tests for app.geo.bearings – bearing parsing and formatting."""

import pytest

from app.geo.bearings import format_bearing, parse_bearing


class TestParseBearingWholeCircle:
    """Whole-circle bearing parsing."""

    def test_simple_degrees(self):
        assert parse_bearing("90") == pytest.approx(90.0)

    def test_due_north(self):
        assert parse_bearing("0") == pytest.approx(0.0)

    def test_due_south(self):
        assert parse_bearing("180") == pytest.approx(180.0)

    def test_due_east(self):
        assert parse_bearing("90") == pytest.approx(90.0)

    def test_due_west(self):
        assert parse_bearing("270") == pytest.approx(270.0)

    def test_with_degree_symbol(self):
        assert parse_bearing("045°30'15\"") == pytest.approx(45.504166666, rel=1e-6)

    def test_space_separated(self):
        assert parse_bearing("45 30 15") == pytest.approx(45.504166666, rel=1e-6)

    def test_zero_minutes_seconds(self):
        assert parse_bearing("90 0 0") == pytest.approx(90.0)

    def test_360_becomes_0(self):
        assert parse_bearing("360") == pytest.approx(0.0)

    def test_leading_zeros(self):
        assert parse_bearing("045 30 15") == pytest.approx(45.504166666, rel=1e-6)

    def test_degrees_minutes_only(self):
        assert parse_bearing("90°30'") == pytest.approx(90.5)


class TestParseBearingQuadrant:
    """Quadrant bearing parsing."""

    def test_ne_quadrant(self):
        # N 45°30' E = 45°30' = 45.5°
        assert parse_bearing("N 45°30' E") == pytest.approx(45.5)

    def test_se_quadrant(self):
        # S 45°30' E = 180 - 45.5 = 134.5°
        assert parse_bearing("S 45°30' E") == pytest.approx(134.5)

    def test_sw_quadrant(self):
        # S 45° W = 180 + 45 = 225°
        assert parse_bearing("S 45 W") == pytest.approx(225.0)

    def test_nw_quadrant(self):
        # N 45° W = 360 - 45 = 315°
        assert parse_bearing("N 45 W") == pytest.approx(315.0)

    def test_due_north_quadrant(self):
        # N 0 E should be 0° (due north)
        assert parse_bearing("N 0 E") == pytest.approx(0.0)

    def test_due_east_quadrant(self):
        # N 90 E = 90°
        assert parse_bearing("N 90 E") == pytest.approx(90.0)

    def test_due_south_via_quadrant(self):
        # S 0 E = 180°  (or S 0 W = 180°, both should work)
        assert parse_bearing("S 0 E") == pytest.approx(180.0)

    def test_s10_w(self):
        # S 10° W = 180 + 10 = 190°
        assert parse_bearing("S 10 W") == pytest.approx(190.0)

    def test_s45_w_equals_225(self):
        """Explicit test case from requirements: S 45 W = 225."""
        assert parse_bearing("S 45 W") == pytest.approx(225.0)

    def test_lowercase_quadrant(self):
        assert parse_bearing("n 45 e") == pytest.approx(45.0)

    def test_quadrant_with_dms(self):
        # N 45°30'15" E
        assert parse_bearing("N 45°30'15\" E") == pytest.approx(45.504166666, rel=1e-6)


class TestParseBearingInvalid:
    """Invalid bearing inputs should raise ValueError."""

    def test_empty_string(self):
        with pytest.raises(ValueError):
            parse_bearing("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            parse_bearing("   ")

    def test_invalid_minutes_60(self):
        with pytest.raises(ValueError, match="[Mm]inutes"):
            parse_bearing("45 60 0")

    def test_invalid_seconds_60(self):
        with pytest.raises(ValueError, match="[Ss]econds"):
            parse_bearing("45 30 60")

    def test_quadrant_angle_over_90(self):
        with pytest.raises(ValueError, match="[Qq]uadrant"):
            parse_bearing("N 91 E")

    def test_no_numbers(self):
        with pytest.raises(ValueError):
            parse_bearing("abc")

    def test_malformed_quadrant(self):
        with pytest.raises(ValueError):
            parse_bearing("X 45 Y")


class TestFormatBearing:
    """Bearing formatting."""

    def test_format_with_seconds(self):
        result = format_bearing(45.504166666)
        assert result == "045°30'15\""

    def test_format_without_seconds(self):
        result = format_bearing(45.5, seconds=False)
        assert result == "045°30'"

    def test_format_zero(self):
        result = format_bearing(0.0)
        assert result == "000°00'00\""

    def test_format_180(self):
        result = format_bearing(180.0)
        assert result == "180°00'00\""

    def test_format_359(self):
        result = format_bearing(359.0)
        assert result == "359°00'00\""


class TestFormatRoundTrip:
    """Parse → format → parse should round-trip."""

    @pytest.mark.parametrize(
        "text",
        [
            "045°30'15\"",
            "180°00'00\"",
            "000°00'00\"",
            "270°45'30\"",
        ],
    )
    def test_round_trip(self, text):
        azimuth = parse_bearing(text)
        formatted = format_bearing(azimuth)
        reparsed = parse_bearing(formatted)
        assert reparsed == pytest.approx(azimuth, abs=1e-6)
