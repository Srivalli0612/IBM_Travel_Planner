"""
Travel Planner Agent — Streamlit Frontend
Powered by IBM Granite (ibm/granite-3-8b-instruct) via IBM watsonx.ai
"""

import streamlit as st
import json
import os
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

from granite_client import chat
from travel_tools import (
    get_weather,
    suggest_destinations,
    build_itinerary_context,
    get_transport_options,
    get_accommodation_options,
    get_packing_list,
    estimate_budget,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Travel Planner Agent — IBM Granite",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Main background */
  .stApp { background-color: #0f1117; color: #e8eaf0; }

  /* Sidebar */
  [data-testid="stSidebar"] { background-color: #1a1d27; border-right: 1px solid #2e3248; }

  /* Chat messages */
  [data-testid="stChatMessage"] { background-color: #1e2235; border-radius: 12px; margin-bottom: 8px; }

  /* Input box */
  [data-testid="stChatInput"] textarea {
    background-color: #1a1d27 !important;
    color: #e8eaf0 !important;
    border: 1px solid #2e3248 !important;
    border-radius: 12px !important;
  }

  /* Buttons */
  .stButton > button {
    background-color: #4f8ef7;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
  }
  .stButton > button:hover { background-color: #3a7de8; }

  /* Metric cards */
  [data-testid="stMetric"] {
    background-color: #22263a;
    border: 1px solid #2e3248;
    border-radius: 10px;
    padding: 12px;
  }

  /* Headers */
  h1, h2, h3 { color: #e8eaf0 !important; }

  /* Selectbox & inputs */
  .stSelectbox > div > div, .stNumberInput > div > div > input {
    background-color: #1a1d27 !important;
    color: #e8eaf0 !important;
    border-color: #2e3248 !important;
  }

  /* Success/info boxes */
  .stSuccess { background-color: #1e3a2e; border-color: #34d399; }
  .stInfo    { background-color: #1e2a42; border-color: #4f8ef7; }
  .stWarning { background-color: #3a2a1e; border-color: #fb923c; }
  .stError   { background-color: #3a1e1e; border-color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ── Intent detection (same as app.py) ─────────────────────────────────────────
def detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["weather", "rain", "temperature", "forecast", "climate"]):
        return "weather"
    if any(w in t for w in ["destination", "where should", "suggest", "recommend place", "where to go"]):
        return "destinations"
    if any(w in t for w in ["itinerary", "day plan", "schedule", "what to do in", "days in"]):
        return "itinerary"
    if any(w in t for w in ["transport", "flight", "train", "bus", "how to travel", "getting there"]):
        return "transport"
    if any(w in t for w in ["hotel", "stay", "accommodation", "hostel", "resort", "airbnb"]):
        return "accommodation"
    if any(w in t for w in ["pack", "luggage", "what to bring", "clothes"]):
        return "packing"
    if any(w in t for w in ["budget", "cost", "price", "how much", "expensive", "cheap"]):
        return "budget"
    return "general"

def extract_city(text: str) -> str:
    words = text.replace(",", "").split()
    stops = {"weather", "in", "for", "at", "the", "of", "forecast", "what", "is", "temperature"}
    candidates = [w for w in words if w.lower() not in stops and len(w) > 2 and w[0].isupper()]
    return " ".join(candidates[:2]) if candidates else "Paris"

def enrich_message(user_msg: str) -> tuple[str, list[str]]:
    """Return (enriched_content, tools_used)"""
    import re
    intent    = detect_intent(user_msg)
    tool_data = {}
    tools     = []

    if intent == "weather":
        city      = extract_city(user_msg)
        tool_data = get_weather(city)
        tools.append("weather")
    elif intent == "destinations":
        msg = user_msg.lower()
        t   = next((k for k in ["beach","mountain","city","cultural","adventure","family","romantic","wildlife"] if k in msg), "city")
        b   = "luxury" if "luxury" in msg else "budget" if "budget" in msg else "mid-range"
        tool_data = suggest_destinations(t, b)
        tools.append("destinations")
    elif intent == "itinerary":
        days_m = re.search(r"(\d+)\s*day", user_msg, re.I)
        days   = int(days_m.group(1)) if days_m else 3
        city   = extract_city(user_msg)
        tool_data = build_itinerary_context(city, days, [])
        tools.append("itinerary")
    elif intent == "transport":
        msg  = user_msg.lower()
        dist = "long" if any(w in msg for w in ["international","flight","overseas"]) else \
               "short" if any(w in msg for w in ["city","local","metro"]) else "medium"
        tool_data = get_transport_options(dist)
        tools.append("transport")
    elif intent == "accommodation":
        msg = user_msg.lower()
        b   = "luxury" if any(w in msg for w in ["luxury","5-star","resort"]) else \
              "budget" if any(w in msg for w in ["budget","hostel","cheap"]) else "mid-range"
        tool_data = get_accommodation_options(b)
        tools.append("accommodation")
    elif intent == "packing":
        msg = user_msg.lower()
        t   = next((k for k in ["beach","mountain","city"] if k in msg), "general")
        tool_data = get_packing_list(t)
        tools.append("packing")
    elif intent == "budget":
        days_m   = re.search(r"(\d+)\s*day", user_msg, re.I)
        people_m = re.search(r"(\d+)\s*(person|people|travell)", user_msg, re.I)
        days     = int(days_m.group(1))   if days_m   else 7
        people   = int(people_m.group(1)) if people_m else 1
        msg      = user_msg.lower()
        tier     = "luxury" if "luxury" in msg else "budget" if "budget" in msg else "mid-range"
        tool_data = estimate_budget(days, tier, people)
        tools.append("budget_estimator")

    enriched = user_msg
    if tool_data:
        enriched = (
            f"{user_msg}\n\n"
            f"[Tool data — use this to give accurate, structured information]\n"
            f"{json.dumps(tool_data, indent=2)}"
        )
    return enriched, tools

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tools_used" not in st.session_state:
    st.session_state.tools_used = {}   # {message_index: [tools]}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✈ Travel Planner Agent")
    st.caption("Powered by IBM Granite · watsonx.ai")
    st.divider()

    # ── Quick prompts ──────────────────────────────────────────────────────
    st.markdown("### ⚡ Quick Actions")
    quick_prompts = {
        "🏖 Beach Destinations":    "Suggest top beach destinations for a budget trip",
        "🗾 Japan Itinerary":       "Plan a 5-day cultural trip to Japan",
        "🏨 Accommodation Tips":   "Best budget accommodation options for backpackers",
        "🚀 Transport Guide":      "What transport options are available for international travel?",
        "🎒 Packing List":         "Give me a packing list for a tropical beach vacation",
        "🗼 Paris in 7 Days":      "Plan a romantic 7-day trip to Paris for 2 people",
    }
    for label, prompt in quick_prompts.items():
        if st.button(label, use_container_width=True, key=f"quick_{label}"):
            st.session_state["pending_prompt"] = prompt

    st.divider()

    # ── Weather widget ─────────────────────────────────────────────────────
    st.markdown("### 🌤 Live Weather")
    weather_city = st.text_input("City", value="Paris", key="weather_city", label_visibility="collapsed",
                                  placeholder="Enter city name…")
    if st.button("Get Weather", use_container_width=True):
        with st.spinner("Fetching weather…"):
            w = get_weather(weather_city)
        st.metric(label=f"{w['city']}, {w['country']}", value=f"{w['temperature']}°C", delta=w['description'])
        col1, col2 = st.columns(2)
        col1.metric("💧 Humidity", f"{w['humidity']}%")
        col2.metric("💨 Wind", f"{w['wind_speed']} m/s")
        if w.get("source","").startswith("Mock"):
            st.caption("⚠ Mock data — add OPENWEATHER_API_KEY for live data")

    st.divider()

    # ── Budget estimator ───────────────────────────────────────────────────
    st.markdown("### 💰 Budget Estimator")
    days    = st.number_input("Days", min_value=1, max_value=365, value=7)
    people  = st.number_input("Travellers", min_value=1, max_value=20, value=2)
    tier    = st.selectbox("Budget tier", ["budget", "mid-range", "luxury"], index=1)
    if st.button("Estimate Cost", use_container_width=True):
        b  = estimate_budget(days, tier, people)
        bd = b["daily_breakdown"]
        st.success(f"**Total: ${b['estimated_total_usd']:,}**")
        st.caption(f"{days} days · {people} person(s) · {tier}")
        st.markdown(f"""
        - 🏨 Accommodation: **${bd['accommodation']}/day**
        - 🍽 Food: **${bd['food']}/day**
        - 🚌 Transport: **${bd['transport']}/day**
        - 🎟 Activities: **${bd['activities']}/day**
        """)
        st.caption(b["note"])

    st.divider()

    # ── Clear chat ─────────────────────────────────────────────────────────
    if st.button("🗑 New Trip", use_container_width=True):
        st.session_state.messages  = []
        st.session_state.tools_used = {}
        st.rerun()

# ── Main chat area ─────────────────────────────────────────────────────────────
st.markdown("# 🌍 Travel Planner Agent")
st.caption("Ask me about destinations, itineraries, hotels, transport, packing, budgets, and more.")

# Welcome message
if not st.session_state.messages:
    st.info(
        "👋 **Welcome!** I'm your AI Travel Planner powered by IBM Granite.\n\n"
        "Try asking:\n"
        "- *Plan a 5-day trip to Tokyo*\n"
        "- *Best beach destinations for a budget traveller*\n"
        "- *How much does a 7-day Bali trip cost for 2 people?*\n"
        "- *Give me a packing list for a mountain trek*"
    )

# Display chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="✈" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])
        tools = st.session_state.tools_used.get(i, [])
        if tools:
            st.caption("🔧 Tools used: " + " · ".join(tools))

# Handle quick prompt injection
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state["chat_input_value"] = prompt

# ── Chat input ─────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask about destinations, itineraries, hotels, packing…")

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Enrich + call IBM Granite
    with st.chat_message("assistant", avatar="✈"):
        with st.spinner("Planning your trip…"):
            try:
                enriched, tools = enrich_message(user_input)

                # Build history for Granite (use enriched last message)
                history = st.session_state.messages[:-1].copy()
                history.append({"role": "user", "content": enriched})

                reply = chat(history)
                st.markdown(reply)
                if tools:
                    st.caption("🔧 Tools used: " + " · ".join(tools))

                # Save to session
                idx = len(st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.session_state.tools_used[idx] = tools

            except EnvironmentError as e:
                err = str(e)
                st.error(
                    f"⚠️ **IBM credentials not configured.**\n\n"
                    f"Please set the following in your Streamlit secrets or `.env`:\n"
                    f"```\nIBM_API_KEY=your_key\nIBM_PROJECT_ID=your_project_id\n```\n\n"
                    f"Details: {err}"
                )
            except Exception as e:
                st.error(f"⚠️ LLM error: {str(e)}")
