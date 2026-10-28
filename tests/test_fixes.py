"""Tests for app.geo.fixes – error localisation and single-value fix suggestions.

Test strategy:
1. Build a closed traverse (rectangle).
2. Corrupt one bearing by transposing two adjacent digits.
3. Run suggest_single_value_fixes and assert the true correction appears
   in the top results.
"""

from app.geo.fixes import _generate_perturbations, suggest_single_value_fixes
from app.geo.traverse import Leg, closure


class TestGeneratePerturbations:
    """Test the low-level perturbation generator."""

    def test_single_digit_substitutions(self):
        perturbed = _generate_perturbations("45")
        # 2 digit positions × 9 alternatives = 18 substitutions
        # plus any transpositions (4 and 5 are adjacent digits → 1 transposition)
        assert "55" in perturbed  # change 4→5
        assert "35" in perturbed  # change 4→3
        assert "46" in perturbed  # change 5→6
        assert "54" in perturbed  # transposition of 4,5

    def test_no_self_substitution(self):
        perturbed = _generate_perturbations("45")
        # The original should not be in the list
        assert "45" not in perturbed

    def test_transposition(self):
        perturbed = _generate_perturbations("12")
        assert "21" in perturbed

    def test_no_transposition_same_digits(self):
        perturbed = _generate_perturbations("11")
        # Transposing identical digits gives the same string; should be excluded
        assert perturbed.count("11") == 0


class TestFixesOnClosedTraverse:
    """Take a closed traverse, corrupt a bearing, find the fix."""

    def _make_closed_rectangle_text(self):
        """Create text representations for a 100×50 rectangle."""
        return [
            ("000°00'00\"", "100.000"),  # North
            ("090°00'00\"", "50.000"),  # East
            ("180°00'00\"", "100.000"),  # South
            ("270°00'00\"", "50.000"),  # West
        ]

    def test_original_has_zero_closure(self):
        """Verify our test rectangle actually closes."""
        text = self._make_closed_rectangle_text()
        from app.geo.bearings import parse_bearing

        legs = [Leg(parse_bearing(b), float(d)) for b, d in text]
        cr = closure(legs)
        assert cr.linear_misclosure < 1e-10

    def test_transposed_bearing_detected(self):
        """Transpose digits in bearing '090°00'00"' → '009°00'00"' and check
        that the fix module finds the correction.

        The true fix is to change the first leg's bearing back to 090.
        We expect this to appear in the top results.
        """
        text = list(self._make_closed_rectangle_text())

        # Corrupt leg 1 (East): swap first two digits of "090" → "009"
        corrupted_bearing = "009°00'00\""
        text[1] = (corrupted_bearing, text[1][1])

        # Verify the traverse is now misclosed
        from app.geo.bearings import parse_bearing

        legs = [Leg(parse_bearing(b), float(d)) for b, d in text]
        cr = closure(legs)
        assert cr.linear_misclosure > 1.0, "Corrupted traverse should have misclosure"

        # Run fixes
        candidates = suggest_single_value_fixes(text, tolerance=0.01)

        assert len(candidates) > 0, "Should find at least one candidate fix"

        # The correct fix should restore bearing to original "090°00'00\""
        # Check if it's in the top 3
        top_3 = candidates[:3]
        found_correct = False
        for c in top_3:
            if (
                c.leg_index == 1
                and c.field == "bearing"
                and abs(parse_bearing(c.corrected_value) - 90.0) < 0.01
            ):
                found_correct = True
                break

        candidate_summary = [
            (c.leg_index, c.field, c.corrected_value, c.residual_misclosure) for c in top_3
        ]
        assert found_correct, (
            f"Expected the correct bearing fix (090°) to be in the top 3 candidates. "
            f"Got: {candidate_summary}"
        )

    def test_corrupted_distance_detected(self):
        """Swap digits in distance '100.000' → '010.000' and check
        that the fix module finds it.
        """
        text = list(self._make_closed_rectangle_text())

        # Corrupt leg 0 (North): swap digits "100.000" → "010.000"
        text[0] = (text[0][0], "010.000")

        candidates = suggest_single_value_fixes(text, tolerance=0.01)
        assert len(candidates) > 0

        # The correct fix should restore distance to ~100
        top_5 = candidates[:5]
        found_correct = False
        for c in top_5:
            if c.leg_index == 0 and c.field == "distance":
                corrected_val = float(c.corrected_value)
                if abs(corrected_val - 100.0) < 1.0:
                    found_correct = True
                    break

        assert found_correct, (
            f"Expected a distance fix near 100.0 in top 5. "
            f"Got: {[(c.leg_index, c.field, c.corrected_value) for c in top_5]}"
        )

    def test_already_closed_returns_empty(self):
        """A closed traverse should return no fix suggestions."""
        text = self._make_closed_rectangle_text()
        candidates = suggest_single_value_fixes(text)
        assert candidates == []
