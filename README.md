# Travel Planner Agent — IBM Granite / watsonx.ai

An AI-powered travel planning assistant built with **IBM Granite** (via **IBM watsonx.ai**) and **Flask**.  
The agent helps users plan personalised trips with real-time weather, itinerary generation, budget estimation, destination suggestions, transport options, accommodation recommendations, and packing lists.

---

## Tech Stack

| Layer        | Technology                                      |
|-------------|--------------------------------------------------|
| AI / LLM     | **IBM Granite 3 8B Instruct** (ibm-watsonx-ai)  |
| Backend      | **Python 3.11+ / Flask 3**                      |
| Frontend     | Vanilla HTML + CSS + JS (zero dependencies)     |
| Weather API  | OpenWeatherMap (free tier, optional)            |

---

## Quick Start

### 1. Clone / Download

```bash
git clone <repo-url>
cd Travel_Planner
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure IBM Credentials

Copy `env.example` to `.env` and fill in your IBM credentials:

```bash
cp env.example .env   # Windows: copy env.example .env
```

Edit `.env`:

```env
IBM_API_KEY=<your IBM Cloud API key>
IBM_PROJECT_ID=<your watsonx.ai project ID>
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_GRANITE_MODEL_ID=ibm/granite-4-h-small
```

> **How to get IBM credentials (free)**
> 1. Sign up at [IBM Cloud](https://cloud.ibm.com) — no credit card needed for Lite tier
> 2. Go to **Manage → Access (IAM) → API Keys** → Create an API key
> 3. Open [watsonx.ai](https://dataplatform.cloud.ibm.com) → Create a project → Copy the Project ID from project settings

### 4. (Optional) Add OpenWeatherMap Key

```env
OPENWEATHER_API_KEY=<your free API key from openweathermap.org>
```

If not set, the weather widget uses mock data.

### 5. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Features

| Feature                  | Description                                                       |
|--------------------------|-------------------------------------------------------------------|
| 🤖 AI Chat               | Conversational itinerary planning powered by IBM Granite          |
| 🌍 Destination Suggester | Recommends destinations by travel type & budget                   |
| 📅 Itinerary Builder     | Day-by-day schedules with activities, restaurants, and costs      |
| 🌤 Live Weather           | Current weather + forecast via OpenWeatherMap                     |
| 💰 Budget Estimator      | Per-person cost estimates by tier (budget / mid-range / luxury)   |
| 🚀 Transport Advisor     | Flight, train, bus recommendations based on journey distance      |
| 🏨 Accommodation Finder  | Hotel, hostel, and Airbnb options by budget                       |
| 🎒 Packing Lists         | Tailored checklists for beach, mountain, city, and general trips  |
| 🔒 Session Memory        | Multi-turn conversation context per browser session               |

---

## Project Structure

```
Travel_Planner/
├── app.py              # Flask backend — routes, intent detection, tool orchestration
├── granite_client.py   # IBM watsonx.ai Granite LLM client (singleton)
├── travel_tools.py     # Travel helper tools (weather, destinations, budget, …)
├── requirements.txt    # Python dependencies
├── env.example         # Environment variable template
├── .env                # Your credentials (never commit this)
└── static/
    └── index.html      # Full-featured chat UI
```

---

## API Endpoints

| Method | Endpoint             | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/`                  | Serve the chat UI                        |
| GET    | `/api/health`        | Health check + model name                |
| POST   | `/api/chat`          | Main chat endpoint (IBM Granite)         |
| GET    | `/api/weather?city=` | Live weather for a city                  |
| GET    | `/api/destinations`  | Destination suggestions                  |
| GET    | `/api/budget`        | Budget estimate                          |
| POST   | `/api/session/clear` | Reset conversation history               |

### POST `/api/chat`

**Request:**
```json
{ "session_id": "my-session", "message": "Plan a 5-day trip to Tokyo" }
```

**Response:**
```json
{
  "reply":      "Day 1: Arrive at Narita…",
  "tools_used": ["itinerary"],
  "session_id": "my-session"
}
```

---

## IBM Granite Models (Lite Tier)

| Model ID                          | Notes                               |
|-----------------------------------|-------------------------------------|
| `ibm/granite-4-h-small`       | ✅ Recommended — fast & capable     |
| `ibm/granite-13b-chat-v2`         | Stronger reasoning, higher latency  |
| `ibm/granite-3-2b-instruct`       | Ultra-fast, minimal footprint       |

Change model in `.env` via `IBM_GRANITE_MODEL_ID`.

---

## License

MIT — free to use, modify, and distribute.
