import os
import sys
import json
import httpx
import logging
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("safemed-mcp")

mcp = FastMCP("SafeMed-Server")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "interactions_db.json")

def load_local_db() -> Dict[str, Any]:
    """Loads the local interactions database."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Local database not found at {DB_PATH}")
        return {"interactions": []}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading local database: {str(e)}")
        return {"interactions": []}

@mcp.tool()
def check_local_interactions(drug_list: List[str]) -> str:
    db = load_local_db()
    interactions = db.get("interactions", [])
    
    normalized_input = [drug.strip().lower() for drug in drug_list]
    found_interactions = []
    
    for i in range(len(normalized_input)):
        for j in range(i + 1, len(normalized_input)):
            drug1 = normalized_input[i]
            drug2 = normalized_input[j]
            
            for interact in interactions:
                da = interact["drug_a"].lower()
                db_name = interact["drug_b"].lower()
                
                if (da == drug1 and db_name == drug2) or (da == drug2 and db_name == drug1):
                    found_interactions.append(interact)
                    
    if not found_interactions:
        return json.dumps({
            "status": "Safe",
            "message": "No high-risk interactions found in the local reference database for the specified drugs.",
            "interactions_found": []
        }, indent=2)
        
    return json.dumps({
        "status": "Warning",
        "message": f"Found {len(found_interactions)} known high-risk drug-drug interaction(s).",
        "interactions_found": found_interactions
    }, indent=2)

@mcp.tool()
def search_fda_drug_label(drug_name: str) -> str:
    """
    Searches the public openFDA API for official FDA drug labeling, focusing on safety warnings and interactions.
    
    Args:
        drug_name (str): The brand or generic name of the drug.
        
    Returns:
        str: A text summary of FDA warnings, drug interactions, and contraindications.
    """
    cleaned_name = drug_name.strip().lower()
    url = f"https://api.fda.gov/drug/label.json"
    params = {
        "search": f'openfda.generic_name:"{cleaned_name}" OR openfda.brand_name:"{cleaned_name}"',
        "limit": 1
    }
    
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        if response.status_code == 404:
            return f"No openFDA label records found for drug '{drug_name}'."
        elif response.status_code != 200:
            return f"Error contacting openFDA API (HTTP status {response.status_code})."
            
        data = response.json()
        results = data.get("results", [])
        if not results:
            return f"No detailed results found for '{drug_name}' in the openFDA database."
            
        label = results[0]
        
        brand_name = label.get("openfda", {}).get("brand_name", [drug_name])[0]
        generic_name = label.get("openfda", {}).get("generic_name", ["N/A"])[0]
        
        warnings = label.get("warnings", ["No general warnings listed."])[0]
        drug_interactions = label.get("drug_interactions", ["No specific drug-drug interactions listed in FDA database."])[0]
        contraindications = label.get("contraindications", ["No contraindications listed."])[0]
        boxed_warning = label.get("boxed_warning", [""])[0]
        
        summary = [
            f"--- FDA OFFICIAL DRUG LABEL FOR {brand_name.upper()} ({generic_name.upper()}) ---",
        ]
        
        if boxed_warning:
            summary.append(f"🚨 BOXED WARNING:\n{boxed_warning.strip()}\n")
            
        summary.extend([
            f"⚠️ GENERAL WARNINGS & PRECAUTIONS:\n{warnings.strip()}\n",
            f"🔄 DRUG INTERACTIONS:\n{drug_interactions.strip()}\n",
            f"🚫 CONTRAINDICATIONS:\n{contraindications.strip()}"
        ])
        
        return "\n".join(summary)
        
    except httpx.RequestError as e:
        logger.error(f"HTTP request error: {str(e)}")
        return f"Network error when trying to reach openFDA: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error querying openFDA: {str(e)}")
        return f"An unexpected error occurred while parsing openFDA data: {str(e)}"

@mcp.tool()
def generate_dosage_schedule(medications_and_dosing: List[Dict[str, str]], daily_start_hour: int = 8) -> str:
    """
    Generates an optimized daily schedule to organize dosing times and avoid scheduling conflicts.
    
    Args:
        medications_and_dosing (List[Dict[str, str]]): List of dicts, each with keys 'name', 'dose', and 'frequency'.
            Example frequency formats: 'Once daily', 'Twice daily', 'Three times daily', 'Every 8 hours'.
        daily_start_hour (int): The hour at which the user begins their day (default 8 for 8:00 AM).
        
    Returns:
        str: A formatted daily timeline schedule.
    """
    schedule = {
        "Morning (approx. 8:00 AM)": [],
        "Afternoon (approx. 1:00 PM)": [],
        "Evening (approx. 6:00 PM)": [],
        "Night (approx. 10:00 PM)": []
    }
    
    for med in medications_and_dosing:
        name = med.get("name", "Unknown").title()
        dose = med.get("dose", "1 pill")
        freq = med.get("frequency", "Once daily").lower()
        
        entry = f"{name} - {dose}"
        
        if "night" in freq or "bedtime" in freq or "qhs" in freq:
            schedule["Night (approx. 10:00 PM)"].append(entry)
        elif "evening" in freq:
            schedule["Evening (approx. 6:00 PM)"].append(entry)
        elif "afternoon" in freq:
            schedule["Afternoon (approx. 1:00 PM)"].append(entry)
        elif "twice" in freq or "2 times" in freq or "bid" in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
            schedule["Night (approx. 10:00 PM)"].append(entry)
        elif "three" in freq or "3 times" in freq or "tid" in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
            schedule["Afternoon (approx. 1:00 PM)"].append(entry)
            schedule["Night (approx. 10:00 PM)"].append(entry)
        elif "four" in freq or "4 times" in freq or "qid" in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
            schedule["Afternoon (approx. 1:00 PM)"].append(entry)
            schedule["Evening (approx. 6:00 PM)"].append(entry)
            schedule["Night (approx. 10:00 PM)"].append(entry)
        elif "every 8 hours" in freq or "every8" in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
            schedule["Afternoon (approx. 1:00 PM)"].append(entry + " (2nd dose ~4 PM)")
            schedule["Night (approx. 10:00 PM)"].append(entry + " (3rd dose ~12 AM)")
        elif "every 6 hours" in freq or "every6" in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
            schedule["Afternoon (approx. 1:00 PM)"].append(entry + " (2nd dose ~2 PM)")
            schedule["Evening (approx. 6:00 PM)"].append(entry + " (3rd dose ~8 PM)")
            schedule["Night (approx. 10:00 PM)"].append(entry + " (4th dose ~2 AM)")
        elif ("once" in freq or "daily" in freq) and "twice" not in freq and "three" not in freq and "every" not in freq:
            schedule["Morning (approx. 8:00 AM)"].append(entry)
        else:
            schedule["Morning (approx. 8:00 AM)"].append(entry + f" (Frequency: {freq.title()})")
            
    lines = ["📅 --- OPTIMIZED DOSAGE SCHEDULE TIMELINE ---"]
    for slot, items in schedule.items():
        lines.append(f"\n⏰ {slot}:")
        if not items:
            lines.append("  (No medications scheduled)")
        else:
            for item in items:
                lines.append(f"  • {item}")
                
    lines.append("\n*Note: If taking ciprofloxacin, do not take it simultaneously with calcium carbonate. Ensure at least a 2-hour buffer.*")
    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run()
