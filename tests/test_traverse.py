"""Tests for app.geo.traverse – traverse computation and closure."""

import math

import pytest

from app.geo.traverse import Leg, bowditch_adjust, closure, compute_traverse


class TestComputeTraverse:
    """Basic traverse coordinate computation."""

    def test_single_leg_north(self):
        coords = compute_traverse(0.0, 0.0, [Leg(0.0, 100.0)])
        assert len(coords) == 2
        assert coords[0] == (0.0, 0.0)
        assert coords[1][0] == pytest.approx(0.0, abs=1e-10)
        assert coords[1][1] == pytest.approx(100.0, abs=1e-10)

    def test_single_leg_east(self):
        coords = compute_traverse(0.0, 0.0, [Leg(90.0, 50.0)])
        assert coords[1][0] == pytest.approx(50.0, abs=1e-10)
        assert coords[1][1] == pytest.approx(0.0, abs=1e-10)

    def test_empty_legs(self):
        coords = compute_traverse(100.0, 200.0, [])
        assert coords == [(100.0, 200.0)]


class TestRectangleClosure:
    """A 100 m × 50 m rectangle should close perfectly and have area 5000 m²."""

    @pytest.fixture()
    def rectangle_legs(self):
        """100 m × 50 m rectangle: N, E, S, W."""
        return [
            Leg(bearing_deg=0.0, distance_m=100.0),  # North 100 m
            Leg(bearing_deg=90.0, distance_m=50.0),  # East 50 m
            Leg(bearing_deg=180.0, distance_m=100.0),  # South 100 m
            Leg(bearing_deg=270.0, distance_m=50.0),  # West 50 m
        ]

    def test_rectangle_closes_to_zero(self, rectangle_legs):
        cr = closure(rectangle_legs)
        assert cr.misclosure_e == pytest.approx(0.0, abs=1e-10)
        assert cr.misclosure_n == pytest.approx(0.0, abs=1e-10)
        assert cr.linear_misclosure == pytest.approx(0.0, abs=1e-10)
        assert cr.relative_precision == "1:inf"

    def test_rectangle_perimeter(self, rectangle_legs):
        cr = closure(rectangle_legs)
        assert cr.perimeter == pytest.approx(300.0)

    def test_rectangle_returns_to_start(self, rectangle_legs):
        coords = compute_traverse(0.0, 0.0, rectangle_legs)
        assert coords[-1][0] == pytest.approx(0.0, abs=1e-10)
        assert coords[-1][1] == pytest.approx(0.0, abs=1e-10)


class TestTriangle:
    """A known equilateral-ish triangle should give correct closure and area."""

    @pytest.fixture()
    def right_triangle_legs(self):
        """Right triangle: 3-4-5 scaled to 30-40-50.

        Start at origin, go East 40 m, then bearing to go North 30 m and
        West 40 m (hypotenuse), then South 30 m.
        Actually, let's use a simple right triangle:
        East 40, North 30, then back to origin.
        """
        # Bearing from (40, 30) back to (0, 0):
        # delta_e = -40, delta_n = -30
        # atan2(-40, -30) = atan2(-40, -30) in degrees
        bearing_back = math.degrees(math.atan2(-40, -30)) % 360
        dist_back = math.sqrt(40**2 + 30**2)

        return [
            Leg(bearing_deg=90.0, distance_m=40.0),  # East 40 m
            Leg(bearing_deg=0.0, distance_m=30.0),  # North 30 m
            Leg(bearing_deg=bearing_back, distance_m=dist_back),  # Back to origin
        ]

    def test_triangle_closes(self, right_triangle_legs):
        cr = closure(right_triangle_legs)
        assert cr.linear_misclosure == pytest.approx(0.0, abs=1e-8)

    def test_triangle_area(self, right_triangle_legs):
        """Right triangle with base 40 and height 30 → area = 600 m²."""
        from app.geo.area import polygon_area_m2

        coords = compute_traverse(0.0, 0.0, right_triangle_legs)
        # Drop the closing point (same as start) for area calc
        area = polygon_area_m2(coords[:-1])
        assert area == pytest.approx(600.0, abs=1e-6)


class TestMisclosureWithError:
    """Injecting a 0.5 m error in one leg should give the expected misclosure."""

    def test_injected_error(self):
        """Take a rectangle but shorten one leg by 0.5 m."""
        legs = [
            Leg(bearing_deg=0.0, distance_m=100.0),
            Leg(bearing_deg=90.0, distance_m=50.0),
            Leg(bearing_deg=180.0, distance_m=99.5),  # 0.5 m short
            Leg(bearing_deg=270.0, distance_m=50.0),
        ]
        cr = closure(legs)
        # The 0.5 m shortfall in the south leg means we don't return
        # far enough south. Misclosure is in the northing direction.
        assert cr.misclosure_n == pytest.approx(0.5, abs=1e-10)
        assert cr.misclosure_e == pytest.approx(0.0, abs=1e-10)
        assert cr.linear_misclosure == pytest.approx(0.5, abs=1e-10)
        # Perimeter = 100 + 50 + 99.5 + 50 = 299.5
        assert cr.perimeter == pytest.approx(299.5)
        # Relative precision = 1:(299.5 / 0.5) = 1:599
        assert cr.relative_precision == "1:599"


class TestBowditchAdjust:
    """Bowditch-adjusted traverse should close exactly."""

    def test_adjusted_rectangle_closes(self):
        """Rectangle with a small error, adjusted should close."""
        legs = [
            Leg(bearing_deg=0.0, distance_m=100.0),
            Leg(bearing_deg=90.0, distance_m=50.0),
            Leg(bearing_deg=180.0, distance_m=99.5),  # 0.5 m short
            Leg(bearing_deg=270.0, distance_m=50.0),
        ]
        coords = bowditch_adjust(0.0, 0.0, legs)

        # The adjusted traverse must close: last point == first point
        assert coords[-1][0] == pytest.approx(coords[0][0], abs=1e-12)
        assert coords[-1][1] == pytest.approx(coords[0][1], abs=1e-12)
        assert len(coords) == 5

    def test_already_closed_traverse(self):
        """A perfectly closed traverse should return the same coordinates."""
        legs = [
            Leg(bearing_deg=0.0, distance_m=100.0),
            Leg(bearing_deg=90.0, distance_m=50.0),
            Leg(bearing_deg=180.0, distance_m=100.0),
            Leg(bearing_deg=270.0, distance_m=50.0),
        ]
        raw = compute_traverse(0.0, 0.0, legs)
        adjusted = bowditch_adjust(0.0, 0.0, legs)

        for r, a in zip(raw, adjusted):
            assert r[0] == pytest.approx(a[0], abs=1e-10)
            assert r[1] == pytest.approx(a[1], abs=1e-10)

    def test_adjusted_with_larger_error(self):
        """Injecting errors in both E and N, Bowditch still closes."""
        legs = [
            Leg(bearing_deg=0.0, distance_m=100.0),
            Leg(bearing_deg=90.0, distance_m=50.5),  # 0.5 m excess east
            Leg(bearing_deg=180.0, distance_m=99.7),  # 0.3 m short south
            Leg(bearing_deg=270.0, distance_m=50.0),
        ]
        coords = bowditch_adjust(1000.0, 2000.0, legs)
        assert coords[-1][0] == pytest.approx(1000.0, abs=1e-12)
        assert coords[-1][1] == pytest.approx(2000.0, abs=1e-12)


class TestLegValidation:
    """Leg dataclass validation."""

    def test_negative_distance_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Leg(bearing_deg=0.0, distance_m=-10.0)
