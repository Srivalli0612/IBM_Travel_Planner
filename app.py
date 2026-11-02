"""
Travel Planner Agent — Flask Backend
Powered by IBM watsonx.ai (Granite model).
"""

import json
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

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

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="static")
CORS(app)

# In-memory session store  { session_id: [messages] }
sessions: dict[str, list[dict]] = {}

# ─── Utility ──────────────────────────────────────────────────────────────────

def _detect_intent(text: str) -> str:
    """Very lightweight intent detection to enrich the Granite context."""
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


def _extract_city(text: str) -> str:
    """Heuristic city extractor — good enough for demo; Granite handles the rest."""
    words = text.replace(",", "").split()
    common_stops = {"weather", "in", "for", "at", "the", "of", "forecast", "what", "is", "temperature"}
    candidates = [w for w in words if w.lower() not in common_stops and len(w) > 2 and w[0].isupper()]
    return " ".join(candidates[:2]) if candidates else "New York"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": os.getenv("IBM_GRANITE_MODEL_ID", "ibm/granite-4-h-small")})


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    POST /api/chat
    Body: { "session_id": str, "message": str }
    Returns: { "reply": str, "tools_used": [...], "session_id": str }
    """
    data       = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    user_msg   = (data.get("message") or "").strip()

    if not user_msg:
        return jsonify({"error": "message is required"}), 400

    # Retrieve or initialise conversation history
    history = sessions.setdefault(session_id, [])

    # ── Tool enrichment ──────────────────────────────────────────────────────
    intent     = _detect_intent(user_msg)
    tool_data  = {}
    tools_used = []

    if intent == "weather":
        city      = _extract_city(user_msg)
        tool_data = get_weather(city)
        tools_used.append("weather")

    elif intent == "destinations":
        # Try to infer type & budget from message
        msg_lower = user_msg.lower()
        t_type = next((k for k in ["beach", "mountain", "city", "cultural", "adventure",
                                    "family", "romantic", "wildlife"] if k in msg_lower), "city")
        budget = "luxury" if any(w in msg_lower for w in ["luxury", "premium"]) else \
                 "budget"  if any(w in msg_lower for w in ["budget", "cheap"]) else "mid-range"
        tool_data = suggest_destinations(t_type, budget)
        tools_used.append("destinations")

    elif intent == "itinerary":
        # Extract destination and days
        import re
        days_match = re.search(r"(\d+)\s*day", user_msg, re.IGNORECASE)
        days  = int(days_match.group(1)) if days_match else 3
        city  = _extract_city(user_msg)
        tool_data = build_itinerary_context(city, days, [])
        tools_used.append("itinerary")

    elif intent == "transport":
        msg_lower  = user_msg.lower()
        dist_type  = "long" if any(w in msg_lower for w in ["international", "flight", "overseas"]) else \
                     "short" if any(w in msg_lower for w in ["city", "local", "metro"]) else "medium"
        tool_data  = get_transport_options(dist_type)
        tools_used.append("transport")

    elif intent == "accommodation":
        msg_lower = user_msg.lower()
        budget    = "luxury" if any(w in msg_lower for w in ["luxury", "5-star", "resort"]) else \
                    "budget" if any(w in msg_lower for w in ["budget", "hostel", "cheap"]) else "mid-range"
        tool_data = get_accommodation_options(budget)
        tools_used.append("accommodation")

    elif intent == "packing":
        msg_lower = user_msg.lower()
        trip_type = next((k for k in ["beach", "mountain", "city"] if k in msg_lower), "general")
        tool_data = get_packing_list(trip_type)
        tools_used.append("packing")

    elif intent == "budget":
        import re
        days_match   = re.search(r"(\d+)\s*day", user_msg, re.IGNORECASE)
        people_match = re.search(r"(\d+)\s*(person|people|travell)", user_msg, re.IGNORECASE)
        days    = int(days_match.group(1))   if days_match   else 7
        people  = int(people_match.group(1)) if people_match else 1
        msg_lower = user_msg.lower()
        tier   = "luxury" if "luxury" in msg_lower else "budget" if "budget" in msg_lower else "mid-range"
        tool_data = estimate_budget(days, tier, people)
        tools_used.append("budget_estimator")

    # ── Build enriched user message ──────────────────────────────────────────
    enriched_content = user_msg
    if tool_data:
        enriched_content = (
            f"{user_msg}\n\n"
            f"[Tool data — use this to give accurate, structured information]\n"
            f"{json.dumps(tool_data, indent=2)}"
        )

    history.append({"role": "user", "content": enriched_content})

    # ── Call IBM Granite ─────────────────────────────────────────────────────
    try:
        reply = chat(history)
    except EnvironmentError as e:
        return jsonify({"error": str(e), "setup_required": True}), 503
    except Exception as e:
        return jsonify({"error": f"LLM error: {str(e)}"}), 500

    history.append({"role": "assistant", "content": reply})

    # Keep context window manageable (last 20 turns)
    if len(history) > 40:
        sessions[session_id] = history[-40:]

    return jsonify({
        "reply":      reply,
        "tools_used": tools_used,
        "session_id": session_id,
    })


@app.route("/api/weather", methods=["GET"])
def weather_endpoint():
    city = request.args.get("city", "Paris")
    return jsonify(get_weather(city))


@app.route("/api/destinations", methods=["GET"])
def destinations_endpoint():
    t_type = request.args.get("type", "city")
    budget = request.args.get("budget", "mid-range")
    return jsonify(suggest_destinations(t_type, budget))


@app.route("/api/budget", methods=["GET"])
def budget_endpoint():
    days    = int(request.args.get("days", 7))
    tier    = request.args.get("tier", "mid-range")
    people  = int(request.args.get("people", 1))
    return jsonify(estimate_budget(days, tier, people))


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    data       = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    sessions.pop(session_id, None)
    return jsonify({"cleared": True, "session_id": session_id})


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"\n[Travel Planner Agent] Running on http://localhost:{port}")
    print(f"   Model : {os.getenv('IBM_GRANITE_MODEL_ID', 'ibm/granite-4-h-small')}")
    print(f"   Debug : {debug}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
