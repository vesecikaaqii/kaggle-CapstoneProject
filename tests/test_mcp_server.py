import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server import check_local_interactions, generate_dosage_schedule, search_fda_drug_label

class TestCheckLocalInteractions:


    def test_warfarin_aspirin_high(self):
        res = json.loads(check_local_interactions(["warfarin", "aspirin"]))
        assert res["status"] == "Warning"
        assert any(i["severity"] == "High" for i in res["interactions_found"])
        assert any("bleeding" in i["risk"].lower() for i in res["interactions_found"])

    def test_sildenafil_nitroglycerin_critical(self):
        res = json.loads(check_local_interactions(["sildenafil", "nitroglycerin"]))
        assert res["status"] == "Warning"
        assert any(i["severity"] == "Critical" for i in res["interactions_found"])
        assert any("hypotension" in i["risk"].lower() for i in res["interactions_found"])

    def test_lisinopril_spironolactone_medium(self):
        res = json.loads(check_local_interactions(["lisinopril", "spironolactone"]))
        assert res["status"] == "Warning"
        assert any("hyperkalemia" in i["risk"].lower() for i in res["interactions_found"])

    def test_ibuprofen_aspirin_medium(self):
        res = json.loads(check_local_interactions(["ibuprofen", "aspirin"]))
        assert res["status"] == "Warning"
        assert any("gastrointestinal" in i["risk"].lower() for i in res["interactions_found"])

    def test_simvastatin_amlodipine_medium(self):
        res = json.loads(check_local_interactions(["simvastatin", "amlodipine"]))
        assert res["status"] == "Warning"
        assert any("myopathy" in i["risk"].lower() for i in res["interactions_found"])

    def test_ciprofloxacin_calcium_carbonate_medium(self):
        res = json.loads(check_local_interactions(["ciprofloxacin", "calcium carbonate"]))
        assert res["status"] == "Warning"
        assert any("absorption" in i["risk"].lower() for i in res["interactions_found"])

    def test_phenelzine_sertraline_critical(self):
        res = json.loads(check_local_interactions(["phenelzine", "sertraline"]))
        assert res["status"] == "Warning"
        assert any(i["severity"] == "Critical" for i in res["interactions_found"])
        assert any("serotonin" in i["risk"].lower() for i in res["interactions_found"])

    def test_metformin_contrast_dye_high(self):
        res = json.loads(check_local_interactions(["metformin", "contrast dye"]))
        assert res["status"] == "Warning"
        assert any("lactic acidosis" in i["risk"].lower() for i in res["interactions_found"])


    def test_bidirectional_aspirin_warfarin(self):
        res_fwd = json.loads(check_local_interactions(["warfarin", "aspirin"]))
        res_rev = json.loads(check_local_interactions(["aspirin",  "warfarin"]))
        assert res_fwd["status"] == "Warning"
        assert res_rev["status"] == "Warning"
        assert len(res_fwd["interactions_found"]) == len(res_rev["interactions_found"])

    def test_bidirectional_sildenafil_nitroglycerin(self):
        res_fwd = json.loads(check_local_interactions(["sildenafil",   "nitroglycerin"]))
        res_rev = json.loads(check_local_interactions(["nitroglycerin","sildenafil"]))
        assert res_fwd["status"] == res_rev["status"] == "Warning"


    def test_case_insensitive_lookup(self):
        res = json.loads(check_local_interactions(["WARFARIN", "ASPIRIN"]))
        assert res["status"] == "Warning"

    def test_mixed_case(self):
        res = json.loads(check_local_interactions(["Warfarin", "Aspirin"]))
        assert res["status"] == "Warning"


    def test_safe_amoxicillin_vitamin_c(self):
        res = json.loads(check_local_interactions(["amoxicillin", "vitamin c"]))
        assert res["status"] == "Safe"
        assert res["interactions_found"] == []

    def test_safe_single_drug(self):
        res = json.loads(check_local_interactions(["warfarin"]))
        assert res["status"] == "Safe"

    def test_safe_empty_list(self):
        res = json.loads(check_local_interactions([]))
        assert res["status"] == "Safe"

    def test_safe_unknown_drugs(self):
        res = json.loads(check_local_interactions(["magicpill", "fantasydrug"]))
        assert res["status"] == "Safe"


    def test_multiple_interactions_detected(self):
        res = json.loads(check_local_interactions(["warfarin", "aspirin", "ibuprofen"]))
        assert res["status"] == "Warning"
        assert len(res["interactions_found"]) == 2


    def test_return_is_valid_json_string(self):
        result = check_local_interactions(["warfarin", "aspirin"])
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "status" in parsed
        assert "interactions_found" in parsed

    def test_interaction_fields_present(self):
        res = json.loads(check_local_interactions(["warfarin", "aspirin"]))
        interaction = res["interactions_found"][0]
        for field in ("drug_a", "drug_b", "severity", "risk", "description"):
            assert field in interaction, f"Missing field: {field}"


class TestGenerateDosageSchedule:

    def test_once_daily_at_night_goes_to_night_slot(self):
        meds = [{"name": "Simvastatin", "dose": "20mg", "frequency": "Once daily at night"}]
        schedule = generate_dosage_schedule(meds)
        assert "Night (approx. 10:00 PM):" in schedule
        night_idx    = schedule.index("Night (approx. 10:00 PM):")
        simvastatin_idx = schedule.index("Simvastatin")
        assert simvastatin_idx > night_idx, "Simvastatin should appear after the Night slot header"

    def test_once_daily_morning_default(self):
        meds = [{"name": "Lisinopril", "dose": "10mg", "frequency": "Once daily"}]
        schedule = generate_dosage_schedule(meds)
        morning_idx     = schedule.index("Morning (approx. 8:00 AM):")
        lisinopril_idx  = schedule.index("Lisinopril")
        assert lisinopril_idx > morning_idx

    def test_twice_daily_morning_and_night(self):
        meds = [{"name": "Metformin", "dose": "500mg", "frequency": "Twice daily"}]
        schedule = generate_dosage_schedule(meds)
        assert schedule.count("Metformin") == 2

    def test_three_times_daily(self):
        meds = [{"name": "Amoxicillin", "dose": "250mg", "frequency": "Three times daily"}]
        schedule = generate_dosage_schedule(meds)
        assert schedule.count("Amoxicillin") == 3

    def test_every_8_hours_three_slots(self):
        meds = [{"name": "Ibuprofen", "dose": "400mg", "frequency": "Every 8 hours"}]
        schedule = generate_dosage_schedule(meds)
        assert schedule.count("Ibuprofen") == 3

    def test_every_6_hours_four_slots(self):
        meds = [{"name": "Penicillin", "dose": "250mg", "frequency": "Every 6 hours"}]
        schedule = generate_dosage_schedule(meds)
        assert schedule.count("Penicillin") == 4

    def test_bedtime_goes_to_night(self):
        meds = [{"name": "Zolpidem", "dose": "10mg", "frequency": "Bedtime"}]
        schedule = generate_dosage_schedule(meds)
        night_idx   = schedule.index("Night (approx. 10:00 PM):")
        zolpidem_idx = schedule.index("Zolpidem")
        assert zolpidem_idx > night_idx

    def test_evening_goes_to_evening_slot(self):
        meds = [{"name": "Vitamin D", "dose": "1000 IU", "frequency": "Once daily at evening"}]
        schedule = generate_dosage_schedule(meds)
        assert "Evening (approx. 6:00 PM):" in schedule
        evening_idx = schedule.index("Evening (approx. 6:00 PM):")
        vitamin_idx = schedule.index("Vitamin D")
        assert vitamin_idx > evening_idx

    def test_multiple_meds_schedule(self):
        meds = [
            {"name": "Lisinopril",  "dose": "10mg", "frequency": "Once daily"},
            {"name": "Simvastatin", "dose": "20mg", "frequency": "Once daily at night"},
        ]
        schedule = generate_dosage_schedule(meds)
        assert "Lisinopril"  in schedule
        assert "Simvastatin" in schedule

    def test_returns_string(self):
        result = generate_dosage_schedule([{"name": "A", "dose": "1mg", "frequency": "Once daily"}])
        assert isinstance(result, str)

    def test_all_slots_present(self):
        schedule = generate_dosage_schedule([{"name": "X", "dose": "1mg", "frequency": "Once daily"}])
        for slot in ["Morning", "Afternoon", "Evening", "Night"]:
            assert slot in schedule

    def test_empty_list(self):
        schedule = generate_dosage_schedule([])
        assert isinstance(schedule, str)
        assert "Morning" in schedule

class TestSearchFdaDrugLabel:

    def _make_mock_response(self, status_code=200, json_data=None):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        return mock

    def _fda_label_payload(self, brand="WARFARIN", generic="warfarin"):
        return {
            "results": [{
                "openfda": {
                    "brand_name":   [brand],
                    "generic_name": [generic]
                },
                "warnings":          ["Bleeding risk warning text."],
                "drug_interactions": ["Do not combine with aspirin."],
                "contraindications": ["Hypersensitivity contraindicated."],
                "boxed_warning":     ["BLACK BOX: Serious bleeding risk."]
            }]
        }

    def test_successful_fda_lookup(self):
        with patch("httpx.get", return_value=self._make_mock_response(200, self._fda_label_payload())):
            result = search_fda_drug_label("warfarin")
        assert "WARFARIN" in result
        assert "BLACK BOX" in result
        assert "Bleeding risk" in result
        assert "Drug Interactions" in result.upper() or "DRUG INTERACTIONS" in result

    def test_boxed_warning_present(self):
        with patch("httpx.get", return_value=self._make_mock_response(200, self._fda_label_payload())):
            result = search_fda_drug_label("warfarin")
        assert "BLACK BOX" in result or "BOXED WARNING" in result

    def test_404_returns_not_found_message(self):
        with patch("httpx.get", return_value=self._make_mock_response(404)):
            result = search_fda_drug_label("fakemedicineXYZ")
        assert "No openFDA" in result or "not found" in result.lower()

    def test_non_200_returns_error_message(self):
        with patch("httpx.get", return_value=self._make_mock_response(500)):
            result = search_fda_drug_label("warfarin")
        assert "Error" in result or "error" in result

    def test_empty_results_handled(self):
        with patch("httpx.get", return_value=self._make_mock_response(200, {"results": []})):
            result = search_fda_drug_label("unknowndrug")
        assert "No detailed results" in result or "not found" in result.lower()

    def test_network_error_handled(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.RequestError("timeout")):
            result = search_fda_drug_label("warfarin")
        assert "Network error" in result or "error" in result.lower()

    def test_no_boxed_warning_still_works(self):
        payload = self._fda_label_payload()
        payload["results"][0].pop("boxed_warning")
        with patch("httpx.get", return_value=self._make_mock_response(200, payload)):
            result = search_fda_drug_label("warfarin")
        assert "WARFARIN" in result
        assert "WARNINGS" in result or "Warnings" in result

    def test_result_contains_sections(self):
        with patch("httpx.get", return_value=self._make_mock_response(200, self._fda_label_payload())):
            result = search_fda_drug_label("warfarin")
        assert "WARNINGS" in result.upper() or "WARNING" in result.upper()
        assert "CONTRAINDICATIONS" in result.upper() or "Contraindications" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
