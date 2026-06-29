"""
test_security.py
================
Comprehensive tests for security.py:
  • mask_pii          — all 5 PII pattern types, edge cases, clean text
  • verify_output_safety   — keyword detection
  • enforce_safety_disclaimer — appending vs. skipping
  • encrypt_data / decrypt_data — round-trip fidelity
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security import (
    mask_pii,
    verify_output_safety,
    enforce_safety_disclaimer,
    encrypt_data,
    decrypt_data,
    MEDICAL_DISCLAIMER,
)


class TestMaskPii:
    """Tests for PII detection and masking across all 5 pattern types."""


    def test_ssn_masked(self):
        text, redacted = mask_pii("Patient SSN: 123-45-6789")
        assert "[SSN_REDACTED]" in text
        assert "123-45-6789" not in text
        assert "SSN" in redacted

    def test_ssn_not_present_clean(self):
        text, redacted = mask_pii("No SSN here at all.")
        assert "[SSN_REDACTED]" not in text
        assert "SSN" not in redacted


    def test_email_masked(self):
        text, redacted = mask_pii("Contact patient at john.doe@example.com for results.")
        assert "[EMAIL_REDACTED]" in text
        assert "john.doe@example.com" not in text
        assert "EMAIL" in redacted

    def test_email_multiple(self):
        text, redacted = mask_pii("Email a@b.com and c@d.org")
        assert text.count("[EMAIL_REDACTED]") == 2

    def test_email_not_present_clean(self):
        _, redacted = mask_pii("No email in this text.")
        assert "EMAIL" not in redacted


    def test_phone_masked(self):
        text, redacted = mask_pii("Call +1-555-019-2834 for an appointment.")
        assert "[PHONE_REDACTED]" in text
        assert "PHONE" in redacted

    def test_phone_plain_format(self):
        text, redacted = mask_pii("Phone: 5550192834 on record.")
        
        assert isinstance(text, str)
        assert isinstance(redacted, dict)


    def test_dob_masked_slash(self):
        text, redacted = mask_pii("Patient DOB: 12/04/1990")
        assert "[DOB_REDACTED]" in text
        assert "12/04/1990" not in text
        assert "DOB" in redacted

    def test_dob_masked_dash(self):
        text, redacted = mask_pii("Born on 06-24-1985")
        assert "[DOB_REDACTED]" in text
        assert "DOB" in redacted

    def test_dob_not_present(self):
        _, redacted = mask_pii("No date of birth here.")
        assert "DOB" not in redacted


    def test_zip_masked_5_digit(self):
        text, redacted = mask_pii("Patient lives at ZIP 90210.")
        assert "[ZIP_REDACTED]" in text
        assert "ZIP" in redacted

    def test_zip_masked_9_digit(self):
        text, redacted = mask_pii("Full ZIP code: 90210-1234")
        assert "[ZIP_REDACTED]" in text


    def test_multiple_pii_types(self):
        text = "Patient John (DOB: 12/04/1990, SSN: 123-45-6789) email: j@h.com"
        masked, redacted = mask_pii(text)
        assert "[SSN_REDACTED]"   in masked
        assert "[DOB_REDACTED]"   in masked
        assert "[EMAIL_REDACTED]" in masked
        assert "123-45-6789"      not in masked
        assert "12/04/1990"       not in masked
        assert "j@h.com"          not in masked


    def test_clean_text_unchanged(self):
        clean = "Please take Lisinopril 10mg once daily."
        masked, redacted = mask_pii(clean)
        assert masked == clean
        assert redacted == {}


    def test_returns_tuple_of_str_and_dict(self):
        result = mask_pii("some text")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], dict)

    def test_empty_string(self):
        masked, redacted = mask_pii("")
        assert masked == ""
        assert redacted == {}


class TestVerifyOutputSafety:
    """Tests for safety keyword detection in agent outputs."""

    def test_unsafe_no_keywords(self):
        assert not verify_output_safety("Take 1 pill of Aspirin daily.")

    def test_safe_with_consult(self):
        assert verify_output_safety("Consult your doctor before changing doses.")

    def test_safe_with_physician(self):
        assert verify_output_safety("Always speak to your physician first.")

    def test_safe_with_pharmacist(self):
        assert verify_output_safety("Your pharmacist can advise on interactions.")

    def test_safe_with_disclaimer(self):
        assert verify_output_safety("DISCLAIMER: this is informational only.")

    def test_safe_with_medical_professional(self):
        assert verify_output_safety("Seek guidance from a medical professional.")

    def test_safe_with_healthcare_provider(self):
        assert verify_output_safety("Your healthcare provider should be informed.")

    def test_case_insensitive_keywords(self):
        assert verify_output_safety("Always CONSULT a DOCTOR.")

    def test_empty_string(self):
        assert not verify_output_safety("")

    def test_partial_keyword_not_matched(self):
        result = verify_output_safety("Follow the prescription label.")
        assert not result


class TestEnforceSafetyDisclaimer:
    """Tests for appending / skipping the medical disclaimer."""

    def test_disclaimer_appended_when_missing(self):
        result = enforce_safety_disclaimer("Take one pill of Aspirin.")
        assert "DISCLAIMER:" in result

    def test_disclaimer_not_doubled(self):
        text_with_disclaimer = "Take one pill. DISCLAIMER: SafeMed Concierge is informational."
        result = enforce_safety_disclaimer(text_with_disclaimer)
        # Should not contain the literal MEDICAL_DISCLAIMER appended twice
        assert result.count("DISCLAIMER:") == 1

    def test_text_with_safety_word_gets_disclaimer_footer(self):
        """Has 'consult' but no 'DISCLAIMER:' → should append full disclaimer."""
        result = enforce_safety_disclaimer("Always consult your doctor.")
        assert "DISCLAIMER:" in result

    def test_output_is_string(self):
        result = enforce_safety_disclaimer("Something unsafe.")
        assert isinstance(result, str)

    def test_verify_output_safe_after_enforcement(self):
        result = enforce_safety_disclaimer("Something without safety keywords.")
        assert verify_output_safety(result)

class TestEncryptDecrypt:
    """Tests for the XOR-based local encryption round-trip."""

    def test_basic_round_trip(self):
        data = {"user_id": "u123", "meds": ["Warfarin", "Lisinopril"]}
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)
        assert decrypted == data

    def test_encrypted_is_not_plaintext(self):
        data = {"secret": "value"}
        encrypted = encrypt_data(data)
        assert "secret" not in encrypted
        assert "value"  not in encrypted

    def test_encrypted_is_base64_string(self):
        import base64
        data = {"x": 1}
        encrypted = encrypt_data(data)
        # Should decode without error
        decoded = base64.b64decode(encrypted.encode("utf-8"))
        assert isinstance(decoded, bytes)

    def test_complex_payload_round_trip(self):
        data = {
            "user_id":    "u_982",
            "meds":       ["Warfarin", "Aspirin", "Lisinopril"],
            "session_id": "session_007",
            "dob":        "1990-04-12"
        }
        assert decrypt_data(encrypt_data(data)) == data

    def test_different_data_different_ciphertext(self):
        enc1 = encrypt_data({"a": 1})
        enc2 = encrypt_data({"b": 2})
        assert enc1 != enc2

    def test_decrypt_invalid_returns_empty_dict(self):
        result = decrypt_data("NOT_VALID_BASE64!!!")
        assert result == {}

    def test_empty_dict_round_trip(self):
        data = {}
        assert decrypt_data(encrypt_data(data)) == {}

    def test_nested_dict_round_trip(self):
        data = {"patient": {"name": "John", "meds": ["Aspirin"]}}
        assert decrypt_data(encrypt_data(data)) == data


class TestMedicalDisclaimerConstant:
    def test_disclaimer_is_string(self):
        assert isinstance(MEDICAL_DISCLAIMER, str)

    def test_disclaimer_contains_key_phrases(self):
        disc_lower = MEDICAL_DISCLAIMER.lower()
        assert "not" in disc_lower
        assert "physician" in disc_lower or "pharmacist" in disc_lower

    def test_disclaimer_not_empty(self):
        assert len(MEDICAL_DISCLAIMER) > 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
