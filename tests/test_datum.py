"""Tests for app.geo.datum – Arc 1960 CRS lookups and WGS84 transforms.

Sample point: The KICC building in Nairobi, Kenya.
Chosen because it is a well-known landmark in Nairobi, and its approximate
WGS84 coordinates are publicly available (lat ≈ -1.2864, lon ≈ 36.8172).
The point is in UTM zone 37S, making it useful for testing the Arc 1960
UTM 37S lookup and transform.

We test that:
1. All Arc 1960 CRS lookups find a valid CRS whose name contains "Arc 1960".
2. A transform from Arc 1960 / UTM zone 37S to WGS84 returns lon/lat inside
   Kenya (roughly lat -5 to 5, lon 33 to 42).
3. The uncertainty note is present.
"""

import pytest

from app.geo.datum import lookup_arc1960_crs, transform_to_wgs84


class TestArc1960CrsLookup:
    """Verify that all Arc 1960 CRS lookups find a valid CRS."""

    @pytest.mark.parametrize(
        "crs_name",
        [
            "arc1960_geo",
            "arc1960_utm36s",
            "arc1960_utm37s",
            "arc1960_utm36n",
            "arc1960_utm37n",
        ],
    )
    def test_lookup_contains_arc1960(self, crs_name):
        """Each looked-up CRS name must contain 'Arc 1960'."""
        crs = lookup_arc1960_crs(crs_name)
        assert "arc 1960" in crs.name.lower(), (
            f"CRS '{crs_name}' resolved to '{crs.name}', which does not contain 'Arc 1960'."
        )

    def test_unknown_crs_raises(self):
        with pytest.raises(ValueError, match="Unknown CRS"):
            lookup_arc1960_crs("wgs84")


class TestTransformToWgs84:
    """Transform from Arc 1960 / UTM zone 37S to WGS84.

    Sample point: approximate UTM zone 37S coordinates for the KICC
    building, Nairobi. The KICC (Kenyatta International Convention Centre)
    is at roughly WGS84 lat -1.2864, lon 36.8172.

    Approximate Arc 1960 / UTM zone 37S coordinates for this point:
    Easting ≈ 257_000, Northing ≈ 9_857_000 (southern hemisphere,
    with 10,000,000 m false northing). These are approximate; the test
    checks that the result lands inside Kenya, not that it hits an exact
    spot.
    """

    def test_nairobi_point_in_kenya(self):
        result = transform_to_wgs84(257_000, 9_857_000, "arc1960_utm37s")

        # Kenya bounding box (generous):
        # Latitude: roughly -5 to 5
        # Longitude: roughly 33 to 42
        assert 33.0 < result.lon < 42.0, f"Longitude {result.lon} outside Kenya"
        assert -5.0 < result.lat < 5.0, f"Latitude {result.lat} outside Kenya"

    def test_nairobi_approximate_location(self):
        """The result should be somewhere near central Nairobi."""
        result = transform_to_wgs84(257_000, 9_857_000, "arc1960_utm37s")

        # Within ~50 km of KICC (very generous for datum transform uncertainty)
        assert abs(result.lon - 36.8) < 0.5
        assert abs(result.lat - (-1.3)) < 0.5

    def test_uncertainty_note_present(self):
        result = transform_to_wgs84(257_000, 9_857_000, "arc1960_utm37s")
        assert (
            "accurate to" in result.uncertainty_note.lower()
            or "metres" in result.uncertainty_note.lower()
        )
        assert "survey-grade" in result.uncertainty_note.lower()

    def test_geographic_crs_transform(self):
        """Transform from Arc 1960 geographic (lon/lat) to WGS84."""
        # Arc 1960 geographic coords near Nairobi
        # (approximately the same as WGS84, shifted by a few hundred metres)
        result = transform_to_wgs84(36.82, -1.29, "arc1960_geo")
        assert 33.0 < result.lon < 42.0
        assert -5.0 < result.lat < 5.0
