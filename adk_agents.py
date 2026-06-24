import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from mcp import StdioServerParameters
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import McpToolset, AgentTool
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types

from security import mask_pii, enforce_safety_disclaimer

# Setup logger
logger = logging.getLogger("safemed-agents")
logger.setLevel(logging.INFO)

# Determine model based on API keys
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.5-flash" if GEMINI_KEY else "mock-model"

# --- Mock LLM Implementation for Offline/Testing Mode ---
class MockLlm(BaseLlm):
    """
    Mock LLM implementation for SafeMed Concierge.
    Simulates clinical triage, drug checks, and dosing schedule responses
    to allow the app to be fully interactive without an active Gemini API key.
    """
    @classmethod
    def supported_models(cls) -> List[str]:
        return ["mock-model"]

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        user_msg = ""
        for content in llm_request.contents:
            if content.role == "user":
                for part in content.parts:
                    if part.text:
                        user_msg += part.text + " "
        
        user_msg = user_msg.lower()
        response_text = ""

        # Routing simulation based on keyword matching
        if "warfarin" in user_msg and "aspirin" in user_msg:
            response_text = (
                "🚨 **HIGH RISK INTERACTION DETECTED (Warfarin + Aspirin)**\n\n"
                "Combining warfarin (an anticoagulant) and aspirin (an antiplatelet) increases your risk of "
                "severe internal bleeding. The local safety database warns that this combination has a **High** severity level.\n\n"
                "**Clinical Description:**\n"
                "These medications work in different ways to prevent blood clots. Taking them together has a synergistic effect, "
                "making it much easier for bleeding to occur, particularly in the stomach or brain.\n\n"
                "*Recommendation:* Immediately contact your prescribing physician. Do not stop taking prescribed medications "
                "without direct medical guidance."
            )
        elif "sildenafil" in user_msg and "nitroglycerin" in user_msg:
            response_text = (
                "🚨 **CRITICAL SAFETY ALERT (Sildenafil + Nitroglycerin)**\n\n"
                "Sildenafil (Viagra) and nitroglycerin or other nitrates are **strictly contraindicated**.\n\n"
                "**Clinical Description:**\n"
                "Co-administration can cause a dramatic, sudden, and potentially life-threatening drop in blood pressure "
                "(severe hypotension) that can lead to fainting, stroke, or heart attack.\n\n"
                "*Action Required:* DO NOT take sildenafil if you use nitroglycerin patches, tablets, or sprays. "
                "If you experience chest pain after taking sildenafil, seek emergency medical services immediately. "
                "Do NOT take nitroglycerin."
            )
        elif "lisinopril" in user_msg and "spironolactone" in user_msg:
            response_text = (
                "⚠️ **POTENTIAL DRUG INTERACTION (Lisinopril + Spironolactone)**\n\n"
                "This combination has a **Medium** severity warning for **Hyperkalemia (High Potassium)**.\n\n"
                "**Clinical Description:**\n"
                "Both lisinopril (an ACE inhibitor) and spironolactone (a potassium-sparing diuretic) cause your kidneys to "
                "retain potassium. Elevated blood potassium can be dangerous and affect your heart's rhythm.\n\n"
                "*Recommendation:* Your doctor should regularly monitor your blood potassium levels and kidney function."
            )
        elif "ciprofloxacin" in user_msg and "calcium" in user_msg:
            response_text = (
                "⚠️ **ABSORPTION CONFLICT (Ciprofloxacin + Calcium Carbonate)**\n\n"
                "This combination has a **Medium** severity warning for **Reduced Antibiotic Efficacy**.\n\n"
                "**Clinical Description:**\n"
                "Calcium carbonate (antacids or supplements) binds to ciprofloxacin in your stomach, preventing your body "
                "from absorbing the antibiotic. This can make the treatment fail.\n\n"
                "*Recommendation:* Take ciprofloxacin at least 2 hours before or 6 hours after taking calcium supplements or antacids."
            )
        elif "schedule" in user_msg or "timetable" in user_msg or "daily calendar" in user_msg or "dosing" in user_msg:
            # Generate a mock schedule
            response_text = (
                "📅 **OPTIMIZED DOSAGE SCHEDULE TIMELINE**\n\n"
                "Based on the medications provided, here is your organized daily schedule:\n\n"
                "⏰ **Morning (approx. 8:00 AM):**\n"
                "  • **Lisinopril** - 10mg (Once daily for blood pressure)\n\n"
                "⏰ **Afternoon (approx. 1:00 PM):**\n"
                "  • (No medications scheduled)\n\n"
                "⏰ **Evening (approx. 6:00 PM):**\n"
                "  • (No medications scheduled)\n\n"
                "⏰ **Night (approx. 10:00 PM):**\n"
                "  • **Simvastatin** - 20mg (Once daily for cholesterol, best taken at night)\n\n"
                "*Note: Ensure you log each dose to keep an accurate record for your doctor.*"
            )
        elif "hello" in user_msg or "hi " in user_msg or "hey" in user_msg:
            response_text = (
                "Hello! I am your SafeMed Concierge. I can help you with:\n"
                "1. Checking for drug-drug interactions (e.g., 'Check aspirin and warfarin').\n"
                "2. Searching FDA drug label warnings (e.g., 'What are the FDA warnings for Simvastatin?').\n"
                "3. Setting up an optimized daily dosing schedule.\n\n"
                "How can I assist you today?"
            )
        else:
            response_text = (
                f"I received your inquiry about: '{user_msg[:60]}...'\n\n"
                "To check for drug safety, please enter specific medication names. E.g., 'Check warfarin and ibuprofen'. "
                "Alternatively, I can help schedule your doses or query the FDA database. "
                "What medication would you like to review?"
            )

        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)]
            )
        )

# Register mock model if running in mock mode
if MODEL_NAME == "mock-model":
    logger.info("Registering MockLlm provider since GEMINI_API_KEY is not set.")
    LLMRegistry.register(MockLlm)

# --- MCP Toolset Initialization ---
server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=[server_script]
    )
)

# --- Sub-Agent Definitions ---

# 1. Safety Interaction Agent
safety_agent = Agent(
    name="safety_interaction_agent",
    model=MODEL_NAME,
    tools=[mcp_toolset],
    instruction=(
        "You are an clinical drug safety specialist. "
        "Your primary job is to check for drug-drug interactions using: "
        "1. check_local_interactions (for quick check in our high-risk interaction database) "
        "2. search_fda_drug_label (for detailed official FDA label lookups) "
        "Analyze the user's drug list. Explain identified interactions, listing severity, risk, and a short clinical explanation. "
        "Keep your output clear, structured, and easy for a patient to read."
    )
)

# 2. Dosage Scheduling Agent
dosage_agent = Agent(
    name="dosage_scheduling_agent",
    model=MODEL_NAME,
    tools=[mcp_toolset],
    instruction=(
        "You are a medication scheduling specialist. "
        "Your job is to generate a clean, conflicts-free daily timeline schedule using generate_dosage_schedule. "
        "If there are specific instructions (like ciprofloxacin vs calcium), emphasize them in the schedule notes."
    )
)

# --- Primary Coordinator Agent ---
triage_agent = Agent(
    name="triage_agent",
    model=MODEL_NAME,
    sub_agents=[safety_agent, dosage_agent],
    tools=[AgentTool(safety_agent), AgentTool(dosage_agent)],
    instruction=(
        "You are the primary SafeMed Concierge. "
        "Greet the user warmly and coordinate their requests. "
        "If the user wants to check drug-drug interactions or safety warnings, delegate to safety_interaction_agent. "
        "If the user wants to construct a medication schedule or daily plan, delegate to dosage_scheduling_agent. "
        "Always maintain a professional, supportive, safety-first healthcare concierge tone. "
        "Ensure your response is helpful and ends with a friendly signature."
    )
)

# --- Runner & Session Service Implementation ---
session_service = InMemorySessionService()

def run_agent_query(user_id: str, session_id: str, query: str) -> str:
    """
    Masks PII, runs the query through the google-adk agent runner,
    and returns the sanitized, safety-checked response.
    """
    # 1. Mask PII from user query
    masked_query, redacted_items = mask_pii(query)
    if redacted_items:
        logger.info(f"Redacted sensitive items in query: {redacted_items.keys()}")
        
    # 2. Create Runner
    runner = Runner(
        agent=triage_agent,
        app_name="safemed_app",
        session_service=session_service,
        auto_create_session=True
    )

    # 4. Invoke agent
    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=masked_query)]
    )
    
    events = runner.run(user_id=user_id, session_id=session_id, new_message=user_message)
    
    # 5. Extract response text
    response_text = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    if not response_text:
        response_text = "I'm sorry, I encountered an issue processing your request."

    # 6. Apply output safety guardrail (append medical disclaimer if missing)
    final_output = enforce_safety_disclaimer(response_text)
    
    return final_output
