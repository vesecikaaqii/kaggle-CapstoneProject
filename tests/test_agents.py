import pytest
import os
import json
from security import mask_pii, verify_output_safety, enforce_safety_disclaimer, encrypt_data, decrypt_data
from mcp_server import check_local_interactions, search_fda_drug_label, generate_dosage_schedule
from adk_agents import run_agent_query, MODEL_NAME

def test_pii_masking():
    sensitive_text = "Patient John Doe (DOB: 12/04/1990, SSN: 123-45-6789) can be reached at +1-555-019-2834."
    masked_text, redacted = mask_pii(sensitive_text)
    
    assert "[SSN_REDACTED]" in masked_text
    assert "[DOB_REDACTED]" in masked_text
    assert "[PHONE_REDACTED]" in masked_text
    assert "123-45-6789" not in masked_text
    assert "12/04/1990" not in masked_text
    
    assert "SSN" in redacted
    assert "DOB" in redacted
    assert "PHONE" in redacted

def test_local_interactions_database():
    # Warfarin and Aspirin should trigger warning
    res_str = check_local_interactions(["warfarin", "aspirin"])
    res = json.loads(res_str)
    assert res["status"] == "Warning"
    assert len(res["interactions_found"]) > 0
    assert "bleeding" in res["interactions_found"][0]["risk"].lower()
    
    # Safe combination
    res_safe_str = check_local_interactions(["amoxicillin", "vitamin c"])
    res_safe = json.loads(res_safe_str)
    assert res_safe["status"] == "Safe"
    assert len(res_safe["interactions_found"]) == 0

def test_safety_disclaimer_verification():
    text_unsafe = "Take 1 pill of Aspirin daily."
    assert not verify_output_safety(text_unsafe)
    
    text_safe = "Take 1 pill of Aspirin. Please consult your physician."
    assert verify_output_safety(text_safe)
    
    enforced = enforce_safety_disclaimer(text_unsafe)
    assert "DISCLAIMER:" in enforced
    assert verify_output_safety(enforced)

def test_secure_storage_encryption():
    patient_meds = {
        "user_id": "u_982",
        "meds": ["Warfarin", "Lisinopril"]
    }
    
    encrypted = encrypt_data(patient_meds)
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    assert encrypted != json.dumps(patient_meds)
    
    decrypted = decrypt_data(encrypted)
    assert decrypted["user_id"] == "u_982"
    assert "Warfarin" in decrypted["meds"]

def test_agent_query_runner():
    # Verify we can execute a basic triage query
    resp = run_agent_query(user_id="user_test", session_id="sess_test", query="Hello, how does this work?")
    assert len(resp) > 0
    # Response must contain the medical disclaimer
    assert "DISCLAIMER" in resp or "consult" in resp.lower()

if __name__ == "__main__":
    pytest.main([__file__])
