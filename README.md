# Spark — Cycle-Synced Fitness Agent

Personalized workout recommendations that learn *your* cycle, not just the textbook one.

Most cycle apps give generic phase advice ("it's your luteal phase, do yoga"). Spark learns that one woman's luteal is another woman's high-energy week — because it tracks your personal patterns, not population averages.

---

## How It Works

Every day the app asks three questions (energy, soreness, mood) and returns your **top 3 workout suggestions**, ranked and explained. Each time you give feedback (👍 / 👎), your profile gets smarter. After a few cycles, suggestions reflect *you* — not just your phase.

---

## Architecture

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          FastAPI Backend                                │
  │   GET /suggest   POST /checkin   POST /cycle   POST /feedback           │
  └────────┬──────────────────────────────────────────────┬────────────────┘
           │ GET /suggest                                  │ POST /checkin
           │                                              │ POST /feedback
           ▼                                              ▼
  ┌─────────────────────┐                    ┌────────────────────────────┐
  │      SQLite DB      │                    │      Profile Updater       │
  │                     │                    │    (small Claude call)     │
  │  users              │                    │                            │
  │  ┌───────────────┐  │◄───────────────────│  current profile_summary   │
  │  │profile_summary│  │  writes updated NL │  + today's check-in  OR   │
  │  │  (NL text)    │  │  profile to DB     │  + new thumbs up/down      │
  │  └───────────────┘  │                    │  → rewritten NL summary    │
  │  checkins           │                    └────────────────────────────┘
  │  cycle_logs         │
  │  biometrics         │
  │  suggestions        │
  │  feedback           │
  └──────────┬──────────┘
             │ reads all context
             ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                    Step 1: Context Preparation  (Python, no LLM)        │
  │                                                                         │
  │   cycle day + phase + days until period                                 │
  │   today's check-in:  energy / soreness / mood                          │
  │   today's biometrics: HRV, sleep score vs personal phase averages      │
  │   recent feedback history for this phase window                        │
  │   hard constraints: workout dislikes                                    │
  │   NL profile summary  ──────────────────────────────────┐              │
  └───────────────────────────────────────────┬─────────────┼──────────────┘
                                              │             │
                                              ▼             │
  ┌─────────────────────────────────────────────────────────────────────────┐
  │               Step 2: Reasoning Agent  (Claude sonnet-4-6)              │
  │                                                                         │
  │  SYSTEM: expert in female physiology + cycle-synced fitness             │
  │                                                                         │
  │  USER PROFILE (structured NL) ◄────────────────────────────────────┘   │
  │    GENERAL: intermediate, 30 min, avoid: swimming/HIIT                  │
  │    MENSTRUAL: prefers rest day 1, short walks from day 2                │
  │    FOLLICULAR: rising energy, enjoys vinyasa + moderate cardio          │
  │    OVULATORY: peak energy, prefers structured classes                   │
  │    LUTEAL: energy low days 20+, yoga 4.8/5, cardio rated poorly         │
  │    RECENT: 👎 strength training day 22 · 👍 yin yoga day 24            │
  │                                                                         │
  │  WHERE SHE IS TODAY                                                     │
  │    Cycle day 22 · luteal phase · 6 days until period                   │
  │    Energy 2/5 · Soreness 3/5 · Mood: anxious                           │
  │    HRV 42 (luteal avg: 48) · Sleep 71/100                              │
  │                                                                         │
  │  HARD CONSTRAINTS:  never suggest → ["swimming", "HIIT"]               │
  │  PHASE FALLBACK:    luteal defaults if no personal history              │
  │                                                                         │
  │  → returns top 3 ranked suggestions                                     │
  └───────────────────────────────┬─────────────────────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │         Top 3 Suggestions             │
              │                                       │
              │  #1  yin yoga · restorative flow      │
              │      30 min · low intensity           │
              │      "HRV below luteal avg + low      │
              │       energy — yoga rated 4.8/5       │
              │       in this window for you"         │
              │                                       │
              │  #2  walking · easy flat walk         │
              │      25 min · low intensity           │
              │                                       │
              │  #3  pilates · mat core focus         │
              │      30 min · low-medium              │
              │                                       │
              │  👍 / 👎  per suggestion              │
              └───────────────────────────────────────┘
                              │ feedback
                              ▼
                   triggers Profile Updater
                   NL profile gets smarter
                   next /suggest is better
```

---

## User Profile (NL, structured by phase)

Each user has a `profile_summary` — a natural language snapshot updated after every check-in and feedback. Starts from science-based defaults, gets personal over time.

```
GENERAL
- Fitness level: intermediate
- Preferred session length: 30 min
- Always avoid: swimming, HIIT
- Loves: yoga, pilates, walking

MENSTRUAL PHASE (days ~1–5)
- Typical energy: low
- Default workouts: yin yoga, walking, mat pilates, foam rolling
- Personal notes: prefers rest on day 1, short walks from day 2

FOLLICULAR PHASE (days ~6–13)
- Typical energy: rising
- Default workouts: running, cardio, power vinyasa
- Personal notes: [building up — not enough data yet]

OVULATORY PHASE (days ~14–16)
- Typical energy: peak
- Default workouts: cycling, HIIT, crossfit, bootcamp
- Personal notes: tends to prefer structured classes over open cardio

LUTEAL PHASE (days ~17–28)
- Typical energy: low, especially days 20+
- Default workouts: strength training, low incline walking, yoga, barre, pilates
- Personal notes: energy drops noticeably days 20–28; consistently rates
  cardio poorly here; yoga rated 4.8/5 in this window

RECENT FEEDBACK
- 👎 strength training (luteal day 22) — "felt awful"
- 👍 yin yoga (luteal day 24)
- 👍 walking (luteal day 20)
```

---

## Phase Science Baseline

Used as defaults for new users (cold start). Personal patterns override these once data builds up.

| Phase | Days | Energy | Recommended Workouts |
|-------|------|--------|----------------------|
| Menstrual | ~1–5 | Low | Walking, yin yoga, mat pilates, foam rolling |
| Follicular | ~6–13 | Rising | Running, cardio, power vinyasa, swimming |
| Ovulatory | ~14–16 | Peak | Cycling, HIIT, crossfit, bootcamp |
| Luteal | ~17–28 | Declining | Strength training, low incline walking, yoga, barre, pilates |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Profile + pattern summary |
| PATCH | `/users/{id}/preferences` | Update workout likes/dislikes |
| POST | `/users/{id}/checkin` | Log today's energy (1–5), soreness (1–5), mood |
| POST | `/users/{id}/cycle` | Log period start date |
| POST | `/users/{id}/biometrics` | Log today's HRV/sleep |
| GET | `/users/{id}/suggest` | Run agent → top 3 suggestions |
| POST | `/suggestions/{id}/feedback` | Thumbs up/down (`{"liked": true/false}`) |
| GET | `/users/{id}/history` | Past suggestions + feedback |

---

## Demo Users

Two pre-seeded users with 1 year of history showing contrasting patterns:

**Alex** (user id: 1) — standard cycle pattern
- Loves yoga, pilates, walking. Dislikes HIIT and swimming.
- Energy drops in late luteal. High-intensity workouts rated poorly in that window.

**Jordan** (user id: 2) — non-standard pattern
- Loves strength training, HIIT, cycling. Dislikes yoga and barre.
- Stays high-intensity even in luteal — her data shows she performs well regardless.
- Demonstrates the app overriding phase defaults based on personal history.

---

## Setup

### Requirements
- Python 3.10+
- An Anthropic API key

### Install

```bash
git clone https://github.com/yoonoolee/spark_hackathon.git
cd spark_hackathon

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

### Generate mock data + run

```bash
python generate_mock_data.py   # creates data/ JSON files
uvicorn main:app --reload      # seeds DB on startup, serves on :8000
```

### Try it

```bash
# Get top 3 suggestions for Alex today
curl http://localhost:8000/users/1/suggest

# Submit a daily check-in
curl -X POST http://localhost:8000/users/1/checkin \
  -H "Content-Type: application/json" \
  -d '{"energy": 3, "soreness": 2, "mood": "motivated"}'

# Thumbs up the first suggestion
curl -X POST http://localhost:8000/suggestions/1/feedback \
  -H "Content-Type: application/json" \
  -d '{"liked": true}'

# Compare — Jordan gets different suggestions for the same cycle day
curl http://localhost:8000/users/2/suggest
```

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Backend | Python + FastAPI |
| LLM | Claude API (claude-sonnet-4-6) |
| Database | SQLite (runtime, seeded from JSON) |
| Mock data | JSON files in `data/` (committed to repo) |
| Biometrics | Mocked (mirrors HealthKit structure) |
