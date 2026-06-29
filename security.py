import re
import base64
import json
from typing import Dict, List, Tuple

MEDICAL_DISCLAIMER = (
    "\n\n*DISCLAIMER: SafeMed Concierge is an AI assistant providing informational resource material. "
    "It is NOT a medical device and does NOT provide medical advice. "
    "Always consult with a qualified physician or pharmacist before starting, stopping, "
    "or altering any medication regimen.*"
)

PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.●]?)?\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "DOB": re.compile(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b"),
    "ZIP": re.compile(r"\b\d{5}(?:-\d{4})?\b")
}

def mask_pii(text: str) -> Tuple[str, Dict[str, List[str]]]:
    """
    Scans the input text for PII (SSN, Phone, Email, DOB, ZIP) and replaces them with masked placeholders.
    Returns the masked text and a dictionary of masked items for traceability.
    """
    masked_text = text
    masked_items = {}
    
    for label, pattern in PII_PATTERNS.items():
        matches = pattern.findall(masked_text)
        if matches:
            if label == "PHONE":
                formatted_matches = [f"({m[0]}) {m[1]}-{m[2]}" for m in matches if isinstance(m, tuple)]
                masked_items[label] = formatted_matches
                for m in matches:
                    phone_str = "".join(m)
                    masked_text = re.sub(
                        r"\b(?:\+?1[-.●]?)?\(?" + m[0] + r"\)?[-.●]?" + m[1] + r"[-.●]?" + m[2] + r"\b",
                        f"[{label}_REDACTED]",
                        masked_text
                    )
            else:
                masked_items[label] = matches
                masked_text = pattern.sub(f"[{label}_REDACTED]", masked_text)
                
    return masked_text, masked_items

def verify_output_safety(text: str) -> bool:
    """
    Verifies if the agent's output contains a safety disclaimer or recommendation
    to consult a medical professional.
    """
    safety_keywords = [
        "disclaimer",
        "consult",
        "doctor",
        "physician",
        "pharmacist",
        "medical professional",
        "healthcare provider",
        "prescribing information"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in safety_keywords)

def enforce_safety_disclaimer(text: str) -> str:
    """
    Ensures a medical disclaimer is present in the response. If not found, appends it.
    """
    if verify_output_safety(text):
        if "DISCLAIMER:" not in text:
            return text + MEDICAL_DISCLAIMER
        return text
    else:
        return text + MEDICAL_DISCLAIMER

ENCRYPTION_KEY = b"SafeMedSecretKey"

def encrypt_data(data: dict) -> str:
    """
    Encrypts a data dictionary into an encrypted base64 string.
    """
    serialized = json.dumps(data).encode("utf-8")
    encrypted = bytearray()
    for i, byte in enumerate(serialized):
        key_byte = ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)]
        encrypted.append(byte ^ key_byte)
    return base64.b64encode(encrypted).decode("utf-8")

def decrypt_data(encrypted_str: str) -> dict:
    """
    Decrypts an encrypted base64 string back into a dictionary.
    """
    try:
        encrypted_bytes = base64.b64decode(encrypted_str.encode("utf-8"))
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            key_byte = ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)]
            decrypted.append(byte ^ key_byte)
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}
