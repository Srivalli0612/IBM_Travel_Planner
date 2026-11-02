"""
Travel Tools — helper functions for the Travel Planner Agent.
Each function provides one capability: weather, geocoding, destinations, etc.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Weather ──────────────────────────────────────────────────────────────────

def get_weather(city: str) -> dict:
    """
    Fetch current weather + 5-day forecast for a city using OpenWeatherMap.
    Falls back to a descriptive mock if the API key is not configured.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key or api_key == "your_openweather_api_key_here":
        return _mock_weather(city)

    base = "https://api.openweathermap.org/data/2.5"
    try:
        current_resp = requests.get(
            f"{base}/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=8,
        )
        forecast_resp = requests.get(
            f"{base}/forecast",
            params={"q": city, "appid": api_key, "units": "metric", "cnt": 5},
            timeout=8,
        )
        if current_resp.status_code == 200 and forecast_resp.status_code == 200:
            cur  = current_resp.json()
            fore = forecast_resp.json()
            return {
                "city":        cur["name"],
                "country":     cur["sys"]["country"],
                "temperature": round(cur["main"]["temp"]),
                "feels_like":  round(cur["main"]["feels_like"]),
                "humidity":    cur["main"]["humidity"],
                "description": cur["weather"][0]["description"].title(),
                "wind_speed":  cur["wind"]["speed"],
                "forecast": [
                    {
                        "datetime":    item["dt_txt"],
                        "temp":        round(item["main"]["temp"]),
                        "description": item["weather"][0]["description"].title(),
                    }
                    for item in fore["list"]
                ],
                "source": "OpenWeatherMap",
            }
    except requests.RequestException:
        pass

    return _mock_weather(city)


def _mock_weather(city: str) -> dict:
    return {
        "city":        city.title(),
        "country":     "N/A",
        "temperature": 22,
        "feels_like":  21,
        "humidity":    60,
        "description": "Partly Cloudy",
        "wind_speed":  3.5,
        "forecast":    [],
        "source":      "Mock (configure OPENWEATHER_API_KEY for real data)",
    }


# ─── Destinations ─────────────────────────────────────────────────────────────

DESTINATIONS = {
    "beach":       ["Maldives", "Bali, Indonesia", "Santorini, Greece", "Phuket, Thailand", "Cancún, Mexico"],
    "mountain":    ["Swiss Alps, Switzerland", "Banff, Canada", "Patagonia, Argentina", "Himalayas, Nepal", "Dolomites, Italy"],
    "city":        ["Paris, France", "Tokyo, Japan", "New York, USA", "Dubai, UAE", "Barcelona, Spain"],
    "cultural":    ["Rome, Italy", "Kyoto, Japan", "Istanbul, Turkey", "Cairo, Egypt", "Marrakech, Morocco"],
    "adventure":   ["Queenstown, New Zealand", "Costa Rica", "Iceland", "Patagonia, Chile", "Borneo, Malaysia"],
    "budget":      ["Vietnam", "Thailand", "Portugal", "Colombia", "Mexico City, Mexico"],
    "luxury":      ["Maldives", "Monaco", "Seychelles", "Bora Bora, French Polynesia", "Dubai, UAE"],
    "family":      ["Orlando, USA", "Singapore", "London, UK", "Barcelona, Spain", "Gold Coast, Australia"],
    "romantic":    ["Paris, France", "Venice, Italy", "Bali, Indonesia", "Santorini, Greece", "Kyoto, Japan"],
    "wildlife":    ["Kenya (Safari)", "Galápagos Islands", "Borneo, Malaysia", "Serengeti, Tanzania", "Amazon, Brazil"],
}


def suggest_destinations(travel_type: str = "city", budget: str = "mid-range") -> dict:
    """Return destination suggestions based on travel type and budget preference."""
    key = travel_type.lower()
    if budget.lower() in ("budget", "cheap", "low"):
        key = "budget"
    elif budget.lower() in ("luxury", "premium", "high"):
        key = "luxury"

    suggestions = DESTINATIONS.get(key, DESTINATIONS["city"])
    return {
        "travel_type":  travel_type,
        "budget":       budget,
        "destinations": suggestions,
        "tip": f"Top picks for a {travel_type} trip on a {budget} budget.",
    }


# ─── Itinerary Builder ────────────────────────────────────────────────────────

def build_itinerary_context(destination: str, days: int, interests: list[str]) -> dict:
    """
    Return structured context that is injected into the Granite prompt so the
    model can produce a personalised itinerary.
    """
    interest_str = ", ".join(interests) if interests else "general sightseeing"
    return {
        "destination": destination,
        "days":        days,
        "interests":   interest_str,
        "prompt_hint": (
            f"Create a detailed {days}-day itinerary for {destination}. "
            f"The traveller is interested in: {interest_str}. "
            "Include morning, afternoon, and evening activities for each day. "
            "Add restaurant recommendations, estimated travel times, and costs in USD."
        ),
    }


# ─── Transport Options ────────────────────────────────────────────────────────

TRANSPORT_OPTIONS = {
    "short":   ["Taxi / Ride-share (Uber/Lyft)", "Public Bus", "Metro / Subway", "Walking", "Bicycle Rental"],
    "medium":  ["Train (high-speed / intercity)", "Bus (long-distance)", "Domestic Flight", "Car Rental", "Ferry"],
    "long":    ["International Flight", "Train (overnight sleeper)", "Cruise Ship", "Bus (overnight)"],
}


def get_transport_options(distance_type: str = "medium") -> dict:
    """Return transport recommendations based on journey distance."""
    options = TRANSPORT_OPTIONS.get(distance_type.lower(), TRANSPORT_OPTIONS["medium"])
    tips = {
        "short":  "For city travel, public transport is cheapest. Grab a day pass.",
        "medium": "Trains offer the best comfort/price ratio for 100–800 km journeys.",
        "long":   "Book flights 6–8 weeks ahead for the best prices.",
    }
    return {
        "distance_type": distance_type,
        "options":       options,
        "tip":           tips.get(distance_type.lower(), tips["medium"]),
    }


# ─── Accommodation ────────────────────────────────────────────────────────────

ACCOMMODATION_TYPES = {
    "budget":    ["Hostel (dorm bed ~$15–30/night)", "Budget guesthouse (~$30–60/night)", "Airbnb shared room (~$25–50/night)"],
    "mid-range": ["3-star hotel (~$80–150/night)", "Boutique B&B (~$70–130/night)", "Airbnb private apartment (~$60–120/night)"],
    "luxury":    ["5-star resort (~$300+/night)", "Boutique luxury hotel (~$250–500/night)", "Private villa rental (~$400+/night)"],
}


def get_accommodation_options(budget: str = "mid-range") -> dict:
    """Return accommodation recommendations based on budget tier."""
    key  = budget.lower()
    if key in ("cheap", "low", "hostel"):
        key = "budget"
    elif key in ("premium", "high", "5-star"):
        key = "luxury"
    elif key not in ACCOMMODATION_TYPES:
        key = "mid-range"

    options = ACCOMMODATION_TYPES[key]
    tips = {
        "budget":    "Book hostels on Hostelworld. Look for free breakfast deals.",
        "mid-range": "Booking.com and Hotels.com often have loyalty discounts.",
        "luxury":    "Preferred rates via Amex Travel or direct hotel booking.",
    }
    return {
        "budget":  budget,
        "options": options,
        "tip":     tips.get(key, tips["mid-range"]),
    }


# ─── Packing List ─────────────────────────────────────────────────────────────

PACKING_LISTS = {
    "beach":    ["Sunscreen SPF 50+", "Swimwear", "Flip-flops", "Sunglasses", "Beach towel", "Insect repellent", "Light breathable clothing"],
    "mountain": ["Layered clothing", "Waterproof jacket", "Hiking boots", "Gloves & beanie", "Trekking poles", "First-aid kit", "High-energy snacks"],
    "city":     ["Comfortable walking shoes", "Day pack", "Portable charger", "Travel adapter", "Light rain jacket", "Smart casual outfit"],
    "general":  ["Passport & visa docs", "Travel insurance", "Phone + charger", "Medications", "Toiletries", "Local currency", "Copies of key documents"],
}


def get_packing_list(trip_type: str = "general") -> dict:
    """Return a packing list tailored to trip type."""
    key   = trip_type.lower()
    items = PACKING_LISTS.get(key, PACKING_LISTS["general"])
    # Always include general essentials
    if key != "general":
        items = items + PACKING_LISTS["general"]
    return {"trip_type": trip_type, "items": list(dict.fromkeys(items))}  # deduplicate


# ─── Budget Estimator ─────────────────────────────────────────────────────────

DAILY_BUDGETS = {
    "budget":    {"accommodation": 40,  "food": 20,  "transport": 10, "activities": 15},
    "mid-range": {"accommodation": 120, "food": 50,  "transport": 25, "activities": 40},
    "luxury":    {"accommodation": 400, "food": 150, "transport": 80, "activities": 120},
}


def estimate_budget(days: int, tier: str = "mid-range", num_people: int = 1) -> dict:
    """Estimate total trip cost."""
    key    = tier.lower() if tier.lower() in DAILY_BUDGETS else "mid-range"
    daily  = DAILY_BUDGETS[key]
    per_day_total = sum(daily.values())
    total  = per_day_total * days * num_people
    return {
        "days":        days,
        "tier":        tier,
        "people":      num_people,
        "daily_breakdown": daily,
        "per_day_per_person": per_day_total,
        "estimated_total_usd": total,
        "note": "Flights not included. Prices are approximate USD estimates.",
    }
