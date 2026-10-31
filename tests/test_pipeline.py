"""Tests for the end-to-end ArdhiCheck pipeline."""

from unittest.mock import MagicMock

from app.meta.client import (
    PlanExtractionResult,
    SatelliteAnalysisResult,
)
from app.pipeline import run_survey_audit


class TestPipelineScenarios:
    """Verify that all primary user scenarios yield expected verdicts and provenance."""

    def test_scenario_1_clean_gives_green(self):
        result = run_survey_audit(preset_hint="scenario_1")
        assert result["verdict"] == "GREEN"
        assert result["closure"]["relative_precision"] == "1:inf"
        assert result["area"]["within_tolerance"] is True
        assert result["satellite"]["overlap_area_m2"] == 0.0
        assert "GREEN" in result["advisory_report"] or "Pass" in result["advisory_report"]
        # Valuation must be completely removed
        assert "land_advisory" not in result
        # Check provenance
        assert "provenance" in result
        prov = result["provenance"]
        src = prov["extraction"]["source"]
        assert "muse-spark-1.3" in src or "Offline replay" in src
        assert prov["geometry"]["source"] == "app.geo (pure Python, 0 tokens)"
        assert "disclaimer" in result
        assert "Not legal advice" in result["disclaimer"]

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

    def test_scenario_3_offline_reports_not_run(self):
        # Offline replay: zero fabricated encroachment numbers
        result = run_survey_audit(preset_hint="scenario_3")
        assert result["satellite"]["status"] == "not run"
        assert result["satellite"]["overlap_area_m2"] == 0.0
        assert result["provenance"]["satellite"]["model_name"] == "not run"

    def test_scenario_3_with_live_sam_encroachment_gives_red(self):
        # When live SAM 3.1 detects encroachment
        mock_client = MagicMock()
        mock_client.is_live = True
        mock_client.model = "muse-spark-1.3"

        mock_client.extract_plan_from_image.return_value = PlanExtractionResult(
            lr_number="L.R. 11942/8",
            district="Kiambu",
            locality="Ruaka",
            stated_area=0.5,
            stated_unit="ha",
            datum_name="arc1960_utm37s",
            legs=[
                ("000°00'00\"", "100.000"),
                ("090°00'00\"", "50.000"),
                ("180°00'00\"", "100.000"),
                ("270°00'00\"", "50.000"),
            ],
            source="muse-spark-1.3 (live)",
            model_name="muse-spark-1.3",
            request_id="req_live_123",
            latency_ms=120,
            tokens_used=45,
        )
        mock_client.segment_satellite_features.return_value = SatelliteAnalysisResult(
            has_riparian_zone=True,
            riparian_buffer_m=30.0,
            has_road_reserve=False,
            road_buffer_m=0.0,
            detected_features=["Nairobi River riparian reserve"],
            overlap_area_m2=240.0,
            source="sam-3.1 (live)",
            model_name="sam-3.1",
            request_id="sam_live_456",
            latency_ms=350,
            tokens_used=12,
            status="live",
        )
        mock_client.synthesize_advisory_report.return_value = (
            "Encroachment detected in riparian corridor.",
            {
                "source": "muse-spark-1.3 (live)",
                "model_name": "muse-spark-1.3",
                "request_id": "rep_live_789",
                "latency_ms": 200,
                "tokens_used": 60,
            },
        )

        res = run_survey_audit(preset_hint="scenario_3", meta_client=mock_client)
        assert res["verdict"] == "RED"
        assert "riparian" in res["verdict_reason"].lower()
        assert res["provenance"]["satellite"]["status"] == "live"
        assert res["provenance"]["satellite"]["model_name"] == "sam-3.1"
        assert res["satellite"]["overlap_area_m2"] == 240.0

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
        assert result["provenance"]["extraction"]["source"] == "Manual User Entry"

    def test_uploaded_csv_audit(self):
        csv_data = (
            "Bearing_DMS,Distance_m\n"
            "000°00'00\",100.000\n"
            "090°00'00\",50.000\n"
            "180°00'00\",100.000\n"
            "270°00'00\",50.000\n"
        )
        result = run_survey_audit(
            document_text=csv_data,
            filename="upperhill_boundary.csv",
            manual_stated_area=0.50,
        )
        assert result["verdict"] == "GREEN"
        assert result["closure"]["relative_precision"] == "1:inf"
        assert result["area"]["within_tolerance"] is True
        assert "upperhill_boundary.csv" in result["provenance"]["extraction"]["source"]

    def test_uploaded_geojson_audit(self):
        geojson_data = """{
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"lr_number": "L.R. 209/TEST", "stated_area_ha": 0.446},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [36.8160, -1.2990],
                        [36.8160, -1.2981],
                        [36.8164, -1.2981],
                        [36.8164, -1.2990],
                        [36.8160, -1.2990]
                    ]]
                }
            }]
        }"""
        result = run_survey_audit(
            document_text=geojson_data,
            filename="parcel_boundary.geojson",
        )
        assert result["verdict"] in ("GREEN", "AMBER")
        assert len(result["legs"]) == 4
        assert "L.R. 209/TEST" in result["lr_number"]

    def test_scenario_5_mombasa_nyali(self):
        result = run_survey_audit(preset_hint="scenario_5")
        assert result["verdict"] == "GREEN"
        assert len(result["legs"]) == 5

    def test_scenario_6_athi_river(self):
        result = run_survey_audit(preset_hint="scenario_6")
        assert result["verdict"] == "GREEN"
