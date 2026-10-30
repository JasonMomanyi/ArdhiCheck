"""Tests for the end-to-end ArdhiCheck pipeline."""

from app.pipeline import run_survey_audit


class TestPipelineScenarios:
    """Verify that all 4 primary user scenarios yield expected verdicts."""

    def test_scenario_1_clean_gives_green(self):
        result = run_survey_audit(preset_hint="scenario_1")
        assert result["verdict"] == "GREEN"
        assert result["closure"]["relative_precision"] == "1:inf"
        assert result["area"]["within_tolerance"] is True
        assert result["satellite"]["overlap_area_m2"] == 0.0
        assert "VERIFIED (GREEN)" in result["advisory_report"]
        assert "land_advisory" in result
        assert result["land_advisory"]["county"] != ""
        assert result["land_advisory"]["valuation_kes_mid"] > 0

    def test_scenario_2_transposed_bearing_gives_amber_with_fix(self):
        result = run_survey_audit(preset_hint="scenario_2")
        assert result["verdict"] == "AMBER"
        assert result["closure"]["linear_misclosure"] > 1.0
        assert len(result["candidate_fixes"]) > 0
        top_fix = result["candidate_fixes"][0]
        assert top_fix["leg_index"] == 1
        assert top_fix["field"] == "bearing"
        assert "090" in top_fix["corrected_value"]
        assert "AMBER" in result["advisory_report"]

    def test_scenario_3_riparian_overlap_gives_red(self):
        result = run_survey_audit(preset_hint="scenario_3")
        assert result["verdict"] == "RED"
        assert result["satellite"]["has_riparian_zone"] is True
        assert result["satellite"]["overlap_area_m2"] > 0.0
        assert "riparian" in result["verdict_reason"].lower()

    def test_scenario_4_area_deficit_gives_red(self):
        result = run_survey_audit(preset_hint="scenario_4")
        assert result["verdict"] == "RED"
        assert result["area"]["within_tolerance"] is False
        assert result["area"]["difference_pct"] > 50.0

    def test_manual_input_entry(self):
        manual_legs = [
            ("000°00'00\"", "50.000"),
            ("090°00'00\"", "50.000"),
            ("180°00'00\"", "50.000"),
            ("270°00'00\"", "50.000"),
        ]
        result = run_survey_audit(
            manual_legs=manual_legs,
            manual_lr_number="L.R. TEST/SQUARE",
            manual_stated_area=0.25,
            manual_stated_unit="ha",
        )
        assert result["verdict"] == "GREEN"
        assert result["area"]["computed_m2"] == 2500.0
