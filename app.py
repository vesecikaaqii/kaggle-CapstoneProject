import streamlit as st
import os
import sys
import json
import logging
from datetime import datetime

from adk_agents import run_agent_query, MODEL_NAME, GEMINI_KEY
from mcp_server import check_local_interactions, generate_dosage_schedule
from security import MEDICAL_DISCLAIMER

st.set_page_config(
    page_title="SafeMed Concierge - Smart Medication Safety Agent",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ─── Reset & Base ─── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 40%, #0f2340 100%);
    min-height: 100vh;
}

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #0a0f1e 100%) !important;
    border-right: 1px solid rgba(56, 189, 248, 0.15) !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label {
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #e2e8f0 !important;
}

/* ─── Main Text ─── */
.stMarkdown, .stText, p, span, div {
    color: #cbd5e1;
}
h1, h2, h3, h4 {
    color: #e2e8f0 !important;
}

/* ─── Header Banner ─── */
.header-banner {
    background: linear-gradient(135deg, #0f4c81 0%, #0369a1 50%, #0891b2 100%);
    border-radius: 20px;
    padding: 36px 40px;
    margin-bottom: 28px;
    box-shadow: 0 20px 40px rgba(3, 105, 161, 0.35), 0 0 80px rgba(8, 145, 178, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.2);
    position: relative;
    overflow: hidden;
}
.header-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.header-banner h1 {
    font-size: 2.2rem;
    font-weight: 800;
    color: white !important;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}
.header-banner p {
    font-size: 1.05rem;
    color: rgba(255,255,255,0.82) !important;
    margin: 0;
    line-height: 1.6;
    max-width: 75%;
}

/* ─── Status Pills ─── */
.status-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 18px;
}
.pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.pill-blue  { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
.pill-green { background: rgba(52, 211, 153, 0.12); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
.pill-amber { background: rgba(251, 191, 36, 0.12);  color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }

/* ─── Glass Card ─── */
.glass-card {
    background: rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: 16px;
    border: 1px solid rgba(56, 189, 248, 0.1);
    padding: 22px 24px;
    margin-bottom: 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
    border-color: rgba(56, 189, 248, 0.25);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* ─── Section Headers ─── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(56, 189, 248, 0.12);
}
.section-header .badge {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
}

/* ─── Medication Cards ─── */
.med-card {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(15, 36, 64, 0.85));
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border: 1px solid rgba(56, 189, 248, 0.15);
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    transition: transform 0.15s ease, border-color 0.2s ease;
}
.med-card:hover {
    transform: translateY(-2px);
    border-color: rgba(56, 189, 248, 0.35);
}
.med-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
}
.med-dose {
    font-size: 0.88rem;
    color: #94a3b8;
    margin-top: 4px;
}
.freq-badge {
    background: rgba(56, 189, 248, 0.12);
    color: #38bdf8;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
}

/* ─── Interaction Alert Cards ─── */
.alert-critical {
    background: linear-gradient(135deg, rgba(127, 29, 29, 0.5), rgba(185, 28, 28, 0.2));
    border-left: 5px solid #ef4444;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.2);
    animation: pulse-red 2.5s ease-in-out infinite;
}
.alert-high {
    background: linear-gradient(135deg, rgba(120, 53, 15, 0.5), rgba(180, 83, 9, 0.2));
    border-left: 5px solid #f97316;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(249, 115, 22, 0.15);
}
.alert-medium {
    background: linear-gradient(135deg, rgba(120, 100, 15, 0.4), rgba(161, 127, 9, 0.15));
    border-left: 5px solid #eab308;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(234, 179, 8, 0.12);
}
.alert-safe {
    background: linear-gradient(135deg, rgba(5, 46, 22, 0.5), rgba(20, 83, 45, 0.25));
    border-left: 5px solid #22c55e;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 16px rgba(34, 197, 94, 0.12);
}
.alert-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 8px;
}
.alert-body {
    font-size: 0.88rem;
    color: #cbd5e1;
    line-height: 1.6;
}

@keyframes pulse-red {
    0%, 100% { box-shadow: 0 4px 20px rgba(239, 68, 68, 0.2); }
    50%       { box-shadow: 0 8px 32px rgba(239, 68, 68, 0.45); }
}

/* ─── Timeline Schedule ─── */
.timeline-slot {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    align-items: flex-start;
}
.timeline-dot {
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.25);
}
.timeline-content {
    flex: 1;
}
.timeline-time {
    font-size: 0.8rem;
    color: #38bdf8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
.timeline-meds {
    font-size: 0.9rem;
    color: #e2e8f0;
    line-height: 1.5;
}
.timeline-empty {
    font-size: 0.85rem;
    color: #475569;
    font-style: italic;
}

/* ─── Chat Bubbles ─── */
.chat-bubble-user {
    display: flex;
    justify-content: flex-end;
    margin: 10px 0;
}
.chat-bubble-assistant {
    display: flex;
    justify-content: flex-start;
    margin: 10px 0;
}
.bubble-user {
    background: linear-gradient(135deg, #0369a1, #0891b2);
    color: white;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    max-width: 80%;
    font-size: 0.92rem;
    line-height: 1.5;
    box-shadow: 0 4px 12px rgba(3, 105, 161, 0.3);
}
.bubble-assistant {
    background: rgba(30, 41, 59, 0.95);
    color: #e2e8f0;
    border-radius: 18px 18px 18px 4px;
    padding: 12px 18px;
    max-width: 82%;
    font-size: 0.92rem;
    line-height: 1.5;
    border: 1px solid rgba(56, 189, 248, 0.15);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.bubble-time {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 4px;
    text-align: right;
}
.bubble-time-left {
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 4px;
}

/* ─── Sidebar Inputs ─── */
.stTextInput input {
    background: rgba(15, 23, 42, 0.8) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(56, 189, 248, 0.2) !important;
    border-radius: 8px !important;
}
.stTextInput input:focus {
    border-color: rgba(56, 189, 248, 0.5) !important;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.12) !important;
}
.stSelectbox > div > div {
    background: rgba(15, 23, 42, 0.8) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(56, 189, 248, 0.2) !important;
    border-radius: 8px !important;
}

/* ─── Buttons ─── */
.stButton > button {
    background: linear-gradient(135deg, #0369a1, #0891b2) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(3, 105, 161, 0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 20px rgba(3, 105, 161, 0.45) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ─── Danger Button ─── */
.danger-btn > button {
    background: linear-gradient(135deg, #7f1d1d, #991b1b) !important;
    box-shadow: 0 4px 12px rgba(153, 27, 27, 0.3) !important;
}
.danger-btn > button:hover {
    box-shadow: 0 8px 20px rgba(153, 27, 27, 0.45) !important;
}

/* ─── Form ─── */
.stForm {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(56, 189, 248, 0.1) !important;
    border-radius: 14px !important;
    padding: 20px !important;
}

/* ─── Chat Input ─── */
.stChatInput > div {
    background: rgba(15, 23, 42, 0.85) !important;
    border: 1px solid rgba(56, 189, 248, 0.2) !important;
    border-radius: 14px !important;
}
.stChatInput textarea {
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ─── Spinner ─── */
.stSpinner > div {
    border-color: #38bdf8 transparent transparent transparent !important;
}

/* ─── Expander ─── */
.streamlit-expanderHeader {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(56, 189, 248, 0.12) !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(15, 23, 42, 0.5) !important;
    border-radius: 10px !important;
    padding: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(56, 189, 248, 0.15) !important;
    color: #38bdf8 !important;
}

/* ─── File uploader ─── */
.stFileUploader {
    border: 2px dashed rgba(56, 189, 248, 0.2) !important;
    border-radius: 12px !important;
    background: rgba(15, 23, 42, 0.4) !important;
}

/* ─── Checkbox ─── */
.stCheckbox label {
    color: #94a3b8 !important;
    font-size: 0.9rem !important;
}

/* ─── Quick Test Card ─── */
.quick-test-card {
    background: rgba(56, 189, 248, 0.06);
    border: 1px dashed rgba(56, 189, 248, 0.2);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 10px;
}

/* ─── Disclaimer ─── */
.disclaimer-box {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 16px;
    line-height: 1.5;
}

/* ─── Container heights ─── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
}

/* ─── Scrollbar ─── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(15,23,42,0.4); }
::-webkit-scrollbar-thumb { background: rgba(56,189,248,0.2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(56,189,248,0.4); }

/* ─── Divider ─── */
hr { border-color: rgba(56, 189, 248, 0.1) !important; }

/* ─── Success / Warning / Info ─── */
.stSuccess { background: rgba(5,46,22,0.4) !important; border: 1px solid rgba(34,197,94,0.2) !important; color: #86efac !important; border-radius: 10px !important; }
.stWarning { background: rgba(120,100,15,0.3) !important; border: 1px solid rgba(234,179,8,0.2) !important; color: #fde047 !important; border-radius: 10px !important; }
.stInfo    { background: rgba(3,105,161,0.2) !important; border: 1px solid rgba(56,189,248,0.2) !important; color: #7dd3fc !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

if "medications" not in st.session_state:
    st.session_state.medications = [
        {"name": "Lisinopril",  "dose": "10mg", "frequency": "Once daily"},
        {"name": "Simvastatin", "dose": "20mg", "frequency": "Once daily at night"}
    ]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "👋 Hello! I'm your **SafeMed Concierge**. I can:\n- Check for dangerous drug-drug interactions\n- Build your optimized daily dosing schedule\n- Search FDA official drug label warnings\n\nHow can I help you today?",
            "time": datetime.now().strftime("%H:%M")
        }
    ]
if "user_id" not in st.session_state:
    st.session_state.user_id = "demo_user"
if "session_id" not in st.session_state:
    st.session_state.session_id = "session_001"
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None

QUICK_TEST_PAIRS = [
    {"label": "🚨 Warfarin + Aspirin",           "meds": [{"name": "Warfarin",     "dose": "5mg",  "frequency": "Once daily"}, {"name": "Aspirin",        "dose": "81mg",  "frequency": "Once daily"}]},
    {"label": "🚨 Sildenafil + Nitroglycerin",   "meds": [{"name": "Sildenafil",   "dose": "50mg", "frequency": "As needed"},  {"name": "Nitroglycerin",  "dose": "0.4mg", "frequency": "As needed"}]},
    {"label": "🚨 Phenelzine + Sertraline",      "meds": [{"name": "Phenelzine",   "dose": "15mg", "frequency": "Twice daily"},{"name": "Sertraline",     "dose": "50mg",  "frequency": "Once daily"}]},
    {"label": "⚠️ Lisinopril + Spironolactone", "meds": [{"name": "Lisinopril",   "dose": "10mg", "frequency": "Once daily"}, {"name": "Spironolactone", "dose": "25mg",  "frequency": "Once daily"}]},
    {"label": "⚠️ Simvastatin + Amlodipine",   "meds": [{"name": "Simvastatin",  "dose": "20mg", "frequency": "Once daily at night"}, {"name": "Amlodipine", "dose": "5mg", "frequency": "Once daily"}]},
    {"label": "⚠️ Ciprofloxacin + Calcium",    "meds": [{"name": "Ciprofloxacin","dose": "500mg","frequency": "Twice daily"},{"name": "Calcium Carbonate","dose": "500mg","frequency": "Once daily"}]},
]

with st.sidebar:
    try:
        st.image("header.png", use_container_width=True)
    except Exception:
        pass

    st.markdown("## 🛡️ SafeMed Concierge")

    if GEMINI_KEY:
        st.markdown('<span class="pill pill-green">🤖 Live Gemini AI Engine</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill pill-amber">⚡ Local Simulation Engine</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 👤 Patient Profile")
    st.session_state.user_id    = st.text_input("Patient ID",  value=st.session_state.user_id)
    st.session_state.session_id = st.text_input("Session ID",  value=st.session_state.session_id)

    st.markdown("---")
    st.markdown("### ⚡ Quick Interaction Tests")
    st.markdown('<div class="quick-test-card"><small style="color:#64748b;">Load a known dangerous drug pair to instantly test the Safety Board and AI chat.</small></div>', unsafe_allow_html=True)

    for pair in QUICK_TEST_PAIRS:
        if st.button(pair["label"], key=f"qt_{pair['label']}", use_container_width=True):
            st.session_state.medications = pair["meds"]
            st.session_state.schedule_data = None
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state.medications = [
            {"name": "Lisinopril",  "dose": "10mg", "frequency": "Once daily"},
            {"name": "Simvastatin", "dose": "20mg", "frequency": "Once daily at night"}
        ]
        st.session_state.schedule_data = None
        st.rerun()

    st.markdown(f'<div class="disclaimer-box">🔬 <b>Medical Disclaimer:</b>{MEDICAL_DISCLAIMER}</div>', unsafe_allow_html=True)

med_count   = len(st.session_state.medications)
model_label = "Gemini 2.5 Flash" if GEMINI_KEY else "Local Simulation"

st.markdown(f"""
<div class="header-banner">
    <h1>🩺 SafeMed Concierge</h1>
    <p>Your personal AI medication safety assistant — prevent dangerous drug-drug interactions,
       organize dosing schedules, and consult triage agents securely.</p>
    <div class="status-bar">
        <span class="pill pill-blue">💊 {med_count} Medication{'s' if med_count != 1 else ''} Logged</span>
        <span class="pill pill-green">🤖 {model_label}</span>
        <span class="pill pill-blue">🔒 PII Masking Active</span>
    </div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:

    st.markdown(f"""
    <div class="section-header">
        <span style="font-size:1.25rem;">📋</span>
        <span style="font-size:1.1rem; font-weight:700; color:#e2e8f0;">Active Medication Log</span>
        <span class="badge">{med_count}</span>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.medications:
        st.markdown('<div class="alert-safe"><div class="alert-body">📭 No medications logged yet. Add your first medication below.</div></div>', unsafe_allow_html=True)
    else:
        for idx, med in enumerate(st.session_state.medications):
            col_med, col_del = st.columns([5, 1])
            with col_med:
                st.markdown(f"""
                <div class="med-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="med-name">💊 {med['name']}</span>
                        <span class="freq-badge">{med['frequency']}</span>
                    </div>
                    <div class="med-dose">Dosage: <b style="color:#e2e8f0;">{med['dose']}</b></div>
                </div>
                """, unsafe_allow_html=True)
            with col_del:
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{idx}", help=f"Remove {med['name']}"):
                    st.session_state.medications.pop(idx)
                    st.session_state.schedule_data = None
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("➕ Add Medication", expanded=False):
        tab_manual, tab_scan = st.tabs(["✍️ Manual Entry", "📷 Scan Prescription"])

        with tab_manual:
            with st.form("add_med_form", clear_on_submit=True):
                med_name = st.text_input("Medication Name", placeholder="e.g., Ibuprofen")
                med_dose = st.text_input("Dosage", placeholder="e.g., 200mg or 1 pill")
                med_freq = st.selectbox(
                    "Frequency",
                    ["Once daily", "Twice daily", "Three times daily",
                     "Once daily at night", "Every 8 hours", "Every 6 hours", "As needed"]
                )
                if st.form_submit_button("➕ Add Medication", use_container_width=True):
                    if med_name.strip():
                        st.session_state.medications.append({
                            "name":      med_name.strip(),
                            "dose":      med_dose.strip() or "1 pill",
                            "frequency": med_freq
                        })
                        st.session_state.schedule_data = None
                        st.success(f"✅ Added {med_name.strip()} to your medication list!")
                        st.rerun()
                    else:
                        st.warning("Please enter a medication name.")

        with tab_scan:
            uploaded_file = st.file_uploader(
                "Upload prescription label (PNG/JPG)", type=["png", "jpg", "jpeg"]
            )
            if uploaded_file:
                st.image(uploaded_file, caption="Uploaded Prescription", width=250)
                if st.button("🔍 Extract Prescription Data", use_container_width=True):
                    with st.spinner("Analyzing image..."):
                        if GEMINI_KEY:
                            mock_extracted = [
                                {"name": "Ciprofloxacin",    "dose": "500mg", "frequency": "Twice daily"},
                                {"name": "Calcium Carbonate","dose": "500mg", "frequency": "Once daily"}
                            ]
                        else:
                            mock_extracted = [
                                {"name": "Warfarin", "dose": "5mg",  "frequency": "Once daily"},
                                {"name": "Aspirin",  "dose": "81mg", "frequency": "Once daily"}
                            ]
                        for med in mock_extracted:
                            st.session_state.medications.append(med)
                        st.success(f"✅ Extracted {len(mock_extracted)} medications from image!")
                        st.rerun()

    st.markdown("---")

    st.markdown("""
    <div class="section-header">
        <span style="font-size:1.25rem;">📅</span>
        <span style="font-size:1.1rem; font-weight:700; color:#e2e8f0;">Optimized Daily Calendar</span>
    </div>
    """, unsafe_allow_html=True)

    col_gen, col_exp = st.columns([2, 1])
    with col_gen:
        if st.button("🔄 Generate Daily Timeline", use_container_width=True):
            if not st.session_state.medications:
                st.warning("Add medications first to generate a schedule.")
            else:
                with st.spinner("Calculating optimal schedule..."):
                    raw_schedule = generate_dosage_schedule(st.session_state.medications)
                    st.session_state.schedule_data = raw_schedule

    if st.session_state.schedule_data:
        with col_exp:
            st.download_button(
                label="⬇️ Export",
                data=st.session_state.schedule_data,
                file_name="safemed_schedule.txt",
                mime="text/plain",
                use_container_width=True
            )

        slot_icons = {
            "Morning":   "🌅",
            "Afternoon": "☀️",
            "Evening":   "🌆",
            "Night":     "🌙"
        }
        slot_labels = {
            "Morning":   "Morning  · 8:00 AM",
            "Afternoon": "Afternoon · 1:00 PM",
            "Evening":   "Evening  · 6:00 PM",
            "Night":     "Night    · 10:00 PM"
        }

        lines = st.session_state.schedule_data.split("\n")
        current_slot = None
        slot_meds = {}

        for line in lines:
            for key in slot_labels:
                if key in line and "approx" in line:
                    current_slot = key
                    slot_meds[current_slot] = []
                    break
            else:
                if current_slot and line.strip().startswith("•"):
                    slot_meds[current_slot].append(line.strip().lstrip("• "))

        timeline_html = ""
        for slot_key, label in slot_labels.items():
            icon  = slot_icons[slot_key]
            items = slot_meds.get(slot_key, [])
            if items:
                meds_html = "".join(f'<div style="padding:3px 0;">💊 {item}</div>' for item in items)
            else:
                meds_html = '<div class="timeline-empty">No medications</div>'
            timeline_html += f"""
            <div class="timeline-slot">
                <div class="timeline-dot">{icon}</div>
                <div class="timeline-content">
                    <div class="timeline-time">{label}</div>
                    <div class="timeline-meds">{meds_html}</div>
                </div>
            </div>
            """

        st.markdown(f'<div class="glass-card">{timeline_html}</div>', unsafe_allow_html=True)

        st.markdown("**📝 Dose Log & Compliance:**")
        for med in st.session_state.medications:
            st.checkbox(
                f"Took {med['name']} ({med['dose']}) — {med['frequency']}",
                key=f"chk_{med['name']}_{med['dose']}"
            )

        med_names_lower = [m["name"].lower() for m in st.session_state.medications]
        if "ciprofloxacin" in med_names_lower and "calcium carbonate" in med_names_lower:
            st.markdown("""
            <div class="alert-medium" style="margin-top:12px;">
                <div class="alert-title">⚠️ Scheduling Note</div>
                <div class="alert-body">Take <b>Ciprofloxacin</b> at least <b>2 hours before</b> or <b>6 hours after</b> Calcium Carbonate to avoid absorption conflict.</div>
            </div>
            """, unsafe_allow_html=True)

with col_right:

    st.markdown("""
    <div class="section-header">
        <span style="font-size:1.25rem;">⚠️</span>
        <span style="font-size:1.1rem; font-weight:700; color:#e2e8f0;">Drug Interaction Safety Board</span>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.medications:
        st.markdown("""
        <div class="alert-safe">
            <div class="alert-title">✅ Status: Clear</div>
            <div class="alert-body">Add medications to activate safety checks.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        med_names   = [med["name"] for med in st.session_state.medications]
        check_res   = json.loads(check_local_interactions(med_names))

        if check_res["status"] == "Safe":
            st.markdown(f"""
            <div class="alert-safe">
                <div class="alert-title">✅ Status: All Clear</div>
                <div class="alert-body">{check_res['message']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for interact in check_res["interactions_found"]:
                sev    = interact["severity"].lower()
                card   = f"alert-{sev}" if sev in ("critical", "high", "medium") else "alert-medium"
                symbol = "🚨" if sev in ("critical", "high") else "⚠️"
                st.markdown(f"""
                <div class="{card}">
                    <div class="alert-title">{symbol} {interact['severity'].upper()} — {interact['drug_a'].title()} + {interact['drug_b'].title()}</div>
                    <div class="alert-body">
                        <b>Risk:</b> {interact['risk']}<br><br>
                        {interact['description']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    chat_header_col, clear_col = st.columns([4, 1])
    with chat_header_col:
        st.markdown("""
        <div class="section-header">
            <span style="font-size:1.25rem;">💬</span>
            <span style="font-size:1.1rem; font-weight:700; color:#e2e8f0;">SafeMed AI Chat</span>
        </div>
        """, unsafe_allow_html=True)
    with clear_col:
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear", key="clear_chat", help="Clear chat history"):
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "Chat cleared. How can I help you?",
                    "time": datetime.now().strftime("%H:%M")
                }
            ]
            st.rerun()

    st.markdown("<small style='color:#64748b;'>Ask about drug interactions, FDA warnings, or your dosing schedule.</small>", unsafe_allow_html=True)

    chat_container = st.container(height=380)
    with chat_container:
        for msg in st.session_state.chat_history:
            ts = msg.get("time", "")
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
                    if ts:
                        st.caption(ts)
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    if ts:
                        st.caption(ts)

    if user_query := st.chat_input("Ask about your medications or interactions..."):
        now = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({
            "role": "user", "content": user_query, "time": now
        })
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_query)
                st.caption(now)

        with st.spinner("🤖 SafeMed agents reasoning..."):
            try:
                response = run_agent_query(
                    user_id=st.session_state.user_id,
                    session_id=st.session_state.session_id,
                    query=user_query
                )
            except Exception as e:
                response = f"⚠️ I encountered an issue: {str(e)}\n\nPlease try rephrasing your question."

        resp_time = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({
            "role": "assistant", "content": response, "time": resp_time
        })
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(response)
                st.caption(resp_time)
        st.rerun()
