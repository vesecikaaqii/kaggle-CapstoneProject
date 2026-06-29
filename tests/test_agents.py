"""
test_agents.py
==============
Integration tests for the SafeMed Concierge agent system.
Covers: PII masking, interaction DB, disclaimer enforcement,
        encryption round-trip, agent query runner.
"""

import pytest
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security import mask_pii, verify_output_safety, enforce_safety_disclaimer, encrypt_data, decrypt_data
from mcp_server import check_local_interactions, search_fda_drug_label, generate_dosage_schedule
from adk_agents import run_agent_query, MODEL_NAME


# ══════════════════════════════════════════════════════════════════════════════
#  PII Masking Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestPiiMasking:

    def test_ssn_and_dob_masked(self):
        text = "Patient John Doe (DOB: 12/04/1990, SSN: 123-45-6789) can be reached at +1-555-019-2834."
        masked, redacted = mask_pii(text)
        assert "[SSN_REDACTED]"   in masked
        assert "[DOB_REDACTED]"   in masked
        assert "[PHONE_REDACTED]" in masked
        assert "123-45-6789"      not in masked
        assert "12/04/1990"       not in masked
        assert "SSN"  in redacted
        assert "DOB"  in redacted
        assert "PHONE" in redacted

    def test_email_masked(self):
        text = "Send records to patient@hospital.org"
        masked, redacted = mask_pii(text)
        assert "[EMAIL_REDACTED]" in masked
        assert "patient@hospital.org" not in masked
        assert "EMAIL" in redacted

    def test_clean_medical_text_unchanged(self):
        text = "Take Lisinopril 10mg once daily with water."
        masked, redacted = mask_pii(text)
        assert masked == text
        assert redacted == {}


# ══════════════════════════════════════════════════════════════════════════════
#  Interaction Database
# ══════════════════════════════════════════════════════════════════════════════

class TestLocalInteractionsDatabase:

    def test_warfarin_aspirin_warning(self):
        res = json.loads(check_local_interactions(["warfarin", "aspirin"]))
        assert res["status"] == "Warning"
        assert len(res["interactions_found"]) > 0
        assert "bleeding" in res["interactions_found"][0]["risk"].lower()

    def test_sildenafil_nitroglycerin_critical(self):
        res = json.loads(check_local_interactions(["sildenafil", "nitroglycerin"]))
        assert res["status"] == "Warning"
        assert any(i["severity"] == "Critical" for i in res["interactions_found"])

    def test_phenelzine_sertraline_critical(self):
        res = json.loads(check_local_interactions(["phenelzine", "sertraline"]))
        assert res["status"] == "Warning"
        assert any("serotonin" in i["risk"].lower() for i in res["interactions_found"])

    def test_safe_combination_returns_safe(self):
        res = json.loads(check_local_interactions(["amoxicillin", "vitamin c"]))
        assert res["status"] == "Safe"
        assert res["interactions_found"] == []

    def test_bidirectional_lookup(self):
        res_fwd = json.loads(check_local_interactions(["warfarin", "aspirin"]))
        res_rev = json.loads(check_local_interactions(["aspirin",  "warfarin"]))
        assert res_fwd["status"] == res_rev["status"]
        assert len(res_fwd["interactions_found"]) == len(res_rev["interactions_found"])

    def test_empty_list_is_safe(self):
        res = json.loads(check_local_interactions([]))
        assert res["status"] == "Safe"

    def test_single_drug_is_safe(self):
        res = json.loads(check_local_interactions(["warfarin"]))
        assert res["status"] == "Safe"

    def test_unknown_drugs_are_safe(self):
        res = json.loads(check_local_interactions(["xyzmedA", "xyzmedB"]))
        assert res["status"] == "Safe"

    def test_case_insensitive(self):
        res = json.loads(check_local_interactions(["WARFARIN", "ASPIRIN"]))
        assert res["status"] == "Warning"


# ══════════════════════════════════════════════════════════════════════════════
#  Safety Disclaimer
# ══════════════════════════════════════════════════════════════════════════════

class TestSafetyDisclaimer:

    def test_unsafe_text_flagged(self):
        assert not verify_output_safety("Take 1 pill of Aspirin daily.")

    def test_safe_text_with_physician(self):
        assert verify_output_safety("Always consult your physician.")

    def test_disclaimer_appended_when_missing(self):
        enforced = enforce_safety_disclaimer("Take 1 pill of Aspirin daily.")
        assert "DISCLAIMER:" in enforced
        assert verify_output_safety(enforced)

    def test_disclaimer_not_doubled(self):
        text = "DISCLAIMER: This is for informational purposes. Consult a pharmacist."
        result = enforce_safety_disclaimer(text)
        assert result.count("DISCLAIMER:") == 1


# ══════════════════════════════════════════════════════════════════════════════
#  Secure Storage Encryption
# ══════════════════════════════════════════════════════════════════════════════

class TestSecureStorage:

    def test_encrypt_decrypt_round_trip(self):
        data = {"user_id": "u_982", "meds": ["Warfarin", "Lisinopril"]}
        encrypted = encrypt_data(data)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        assert encrypted != json.dumps(data)
        decrypted = decrypt_data(encrypted)
        assert decrypted["user_id"] == "u_982"
        assert "Warfarin" in decrypted["meds"]

    def test_ciphertext_not_readable(self):
        data = {"secret_field": "my_secret_value"}
        encrypted = encrypt_data(data)
        assert "my_secret_value" not in encrypted

    def test_invalid_ciphertext_returns_empty(self):
        assert decrypt_data("!!INVALID!!") == {}


# ══════════════════════════════════════════════════════════════════════════════
#  Dosage Schedule (bug-fix regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestDosageScheduleRegression:

    def test_once_daily_at_night_not_in_morning(self):
        """Regression for operator-precedence bug: 'Once daily at night' must NOT be morning."""
        meds = [{"name": "Simvastatin", "dose": "20mg", "frequency": "Once daily at night"}]
        schedule = generate_dosage_schedule(meds)
        # Find positions of night slot header and the drug name
        night_idx = schedule.find("Night (approx. 10:00 PM):")
        morning_idx = schedule.find("Morning (approx. 8:00 AM):")
        simva_idx = schedule.find("Simvastatin")
        assert simva_idx > night_idx, "Simvastatin should be listed AFTER the Night header"
        # Also verify it is NOT in the morning section
        # Morning section ends just before the next slot header
        afternoon_idx = schedule.find("Afternoon (approx. 1:00 PM):")
        morning_section = schedule[morning_idx:afternoon_idx]
        assert "Simvastatin" not in morning_section, "Simvastatin must NOT appear in the Morning section"


# ══════════════════════════════════════════════════════════════════════════════
#  Agent Query Runner (end-to-end)
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentQueryRunner:

    def test_basic_greeting_returns_response(self):
        resp = run_agent_query(user_id="user_test", session_id="sess_test_a", query="Hello, how does this work?")
        assert isinstance(resp, str)
        assert len(resp) > 0

    def test_response_contains_disclaimer(self):
        resp = run_agent_query(user_id="user_test", session_id="sess_test_b", query="What can you help with?")
        assert "DISCLAIMER" in resp or "consult" in resp.lower()

    def test_pii_stripped_before_agent(self):
        """Query containing PII should not cause a crash and should still return a response."""
        resp = run_agent_query(
            user_id="user_test",
            session_id="sess_test_c",
            query="My SSN is 123-45-6789 and I take warfarin."
        )
        assert isinstance(resp, str)
        assert len(resp) > 0

    def test_interaction_query_returns_response(self):
        resp = run_agent_query(
            user_id="user_test",
            session_id="sess_test_d",
            query="Check warfarin and aspirin interaction."
        )
        assert isinstance(resp, str)
        assert len(resp) > 0

    def test_schedule_query_returns_response(self):
        resp = run_agent_query(
            user_id="user_test",
            session_id="sess_test_e",
            query="Generate my daily dosing schedule."
        )
        assert isinstance(resp, str)
        assert len(resp) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
