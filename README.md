# Spark — Cycle-Synced Fitness Agent

Personalized workout recommendations that learn *your* cycle, not just the textbook one.

Most cycle apps give generic phase advice ("it's your luteal phase, do yoga"). Spark learns that everyone's cycle is different — tracking your personal patterns, not population averages.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ and [pnpm](https://pnpm.io/installation)
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone the repo

```bash
git clone https://github.com/yoonoolee/spark_hackathon.git
cd spark_hackathon
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Add your API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Seed the database with mock users (Alex + Jordan, ~1 year of history each)
python generate_mock_data.py

# Start the API server
uvicorn main:app --reload
# → running at http://localhost:8000
```

### 3. Frontend setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
# → running at http://localhost:5173
```

The frontend proxies all `/api` requests to `http://localhost:8000`, so both servers need to be running.

---

## Try it out

```bash
# Top suggestion for Alex (user 1)
curl http://localhost:8000/users/1/suggest

# Daily check-in
curl -X POST http://localhost:8000/users/1/checkin \
  -H "Content-Type: application/json" \
  -d '{"energy": 2, "soreness": 3, "mood": "anxious"}'

# Thumbs down a suggestion
curl -X POST http://localhost:8000/suggestions/1/feedback \
  -H "Content-Type: application/json" \
  -d '{"liked": false, "workout_type": "strength training"}'

# Jordan — different suggestions on the same cycle day (personal history overrides phase defaults)
curl http://localhost:8000/users/2/suggest
```

Interactive API docs: `http://localhost:8000/docs`

---

## Demo Users

| User | ID | Profile |
|------|----|---------|
| **Alex** | 1 | Loves yoga, pilates, walking. Dislikes HIIT and swimming. Energy drops late luteal. |
| **Jordan** | 2 | Loves strength training, HIIT, cycling. Dislikes yoga and barre. Maintains intensity even in luteal. |

Both are seeded with ~1 year of check-ins, biometrics, and ~300 workout ratings.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Profile + cycle info + check-in streak |
| PATCH | `/users/{id}/preferences` | Update workout likes/dislikes |
| POST | `/users/{id}/checkin` | Log energy (1–5), soreness (1–5), mood |
| POST | `/users/{id}/cycle` | Log period start date |
| POST | `/users/{id}/biometrics` | Log today's biometrics |
| GET | `/users/{id}/suggest` | Run agent → top + all 5 suggestions |
| POST | `/suggestions/{id}/feedback` | Thumbs up/down `{"liked": true/false}` |
| GET | `/users/{id}/history` | Past suggestions + feedback |

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Frontend | React + Vite + Tailwind + shadcn/ui |
| Backend | Python + FastAPI |
| LLM | Claude API (`claude-sonnet-4-6`) |
| Database | SQLite (seeded from mock data) |
| Weather | Mocked — seasonal + deterministic per date |
| Biometrics | Mocked (mirrors HealthKit structure) |

---

## How It Works

1. **Context assembly** (no LLM) — cycle day/phase, today's check-in, biometrics vs personal phase averages, weather, streak, recent feedback
2. **Pattern analysis** (no LLM) — like rates per workout type, per phase, vs energy/mood
3. **Reasoning agent** (Claude) — combines profile + context + patterns → 5 ranked suggestions with reasoning
4. **Feedback loop** — thumbs up/down + check-ins trigger a small Claude call that rewrites the relevant phase section of the user's natural-language profile

The profile starts from science-based phase defaults and drifts toward the user's personal patterns as data accumulates.

---

## Project Structure

```
spark_hackathon/
├── backend/
│   ├── main.py              # FastAPI app + all routes
│   ├── database.py          # SQLite schema + helpers
│   ├── generate_mock_data.py# Seeds DB with demo users
│   ├── requirements.txt
│   ├── agent/
│   │   ├── context_assembler.py   # Step 1: build context dict
│   │   └── reasoning_agent.py     # Step 3: Claude call → suggestions
│   └── services/
│       ├── analytics.py     # Step 2: pattern analysis
│       ├── cycle.py         # Phase calculation
│       ├── profile.py       # Profile updater (Claude call)
│       └── weather.py       # Mocked weather
└── frontend/
    ├── src/
    │   ├── app/             # Page components
    │   ├── api/             # API client
    │   └── main.tsx
    └── package.json
```
