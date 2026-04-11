# Spark — Cycle-Synced Fitness Agent

Personalized workout recommendations that learn your cycle, not just the textbook one.

Most cycle apps give generic phase advice ("it's your luteal phase, do yoga"). Spark learns that everyone's cycle is different — because it tracks your personal patterns, not population averages.

---

## Architecture

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                           FastAPI Backend                                │
  │  GET /suggest  POST /checkin  POST /cycle  POST /biometrics              │
  │  POST /suggestions/{id}/feedback  GET /users/{id}  GET /users/{id}/history│
  └────────┬─────────────────────────────────────────────┬───────────────────┘
           │ GET /suggest                                 │ POST /checkin
           │                                             │ POST /feedback
           ▼                                             ▼
  ┌──────────────────────┐                 ┌─────────────────────────────────┐
  │      SQLite DB       │                 │        Profile Updater          │
  │                      │                 │      (small Claude call)        │
  │  users               │                 │                                 │
  │  ┌────────────────┐  │◄────────────────│  current profile_summary        │
  │  │profile_summary │  │  writes updated │  + new check-in data  OR        │
  │  │ (NL, by phase) │  │  NL profile     │  + new feedback (phase-tagged)  │
  │  └────────────────┘  │                 │  → rewrites relevant phase      │
  │  checkins            │                 │    section + recent feedback     │
  │  cycle_logs          │                 └─────────────────────────────────┘
  │  biometric_snapshots │
  │  workout_suggestions │
  │  feedback            │
  │  (phase + cycle_day) │
  └──────────┬───────────┘
             │ reads all context
             ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │               Step 1: Context Preparation  (Python, no LLM)             │
  │                                                                          │
  │   cycle day + phase + days until period                                  │
  │   check-in: energy / soreness / mood                                    │
  │   biometrics: HRV, sleep, BBT, stress, readiness, steps (vs phase avgs) │
  │   weather: temp, condition, outdoor-friendly (mocked, seasonal)          │
  │   avg workout duration (from liked history, default 60 min)              │
  │   checkin streak (consecutive days)                                      │
  │   recent feedback (phase-tagged, 1=liked / 0=not liked)                 │
  │   NL profile summary (structured by phase)  ──────────────┐             │
  └──────────────────────────────────┬───────────────────────┼─────────────┘
                                     │                        │
                                     ▼                        │
  ┌──────────────────────────────────────────────────────────────────────────┐
  │               Step 2: Pattern Analysis  (Python, no LLM)                │
  │                                                                          │
  │   computed from full personal feedback history only                      │
  │   • like rate per workout type overall                                   │
  │   • like rate per workout type per phase                                 │
  │   • like rate vs energy level (high / low)                               │
  │   • like rate vs mood (positive / negative)                              │
  │   • late luteal avoidance patterns (day 20+)                             │
  │                                                                          │
  │   e.g. "yoga: liked 88% overall — 100% when energy low,                 │
  │          100% when negative mood"                                        │
  │         "barre: liked 21% — late luteal (day 20+): 0%"                  │
  └──────────────────────────────────┬───────────────────────────────────────┘
                                     │ PatternSummary
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │               Step 3: Reasoning Agent  (Claude sonnet-4-6)               │
  │                                                                          │
  │  USER PROFILE (structured NL, by phase) ◄─────────────────────────────┘ │
  │    GENERAL: intermediate, avg 46 min, avoid: swimming/HIIT               │
  │    LUTEAL: energy low days 20+, yoga 88% liked, barre 0% late luteal     │
  │    RECENT: 0 strength training [luteal day 22] · 1 yin yoga [luteal 18]  │
  │                                                                          │
  │  WHERE SHE IS TODAY                                                      │
  │    Cycle day 22 · LUTEAL · 6 days until period                           │
  │    Energy 2/5 · Soreness 3/5 · Mood: anxious                            │
  │    HRV: 42 (avg: 50, -16%) · Sleep: 71/100 · Readiness: 62/100          │
  │    Stress: 55/100 · BBT: 98.3°F · Steps: 5200 (avg: 6500, -20%)         │
  │    Weather: 57°F, sunny (good for outdoor)                               │
  │                                                                          │
  │  PATTERN ANALYSIS                                                        │
  │    yoga: 88% liked — 100% when energy low, 100% negative mood           │
  │    barre: 21% liked — late luteal: 0%, low energy: 0%                   │
  │    ...                                                                   │
  │                                                                          │
  │  HARD CONSTRAINTS: never suggest → ["swimming", "HIIT"]                 │
  │                                                                          │
  │  → returns 5 ranked suggestions                                          │
  └──────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                         API Response                                     │
  │                                                                          │
  │  top          → rank 1 only  (main page)                                │
  │  suggestions  → all 5        (full list page)                            │
  │  checkin_streak, cycle, weather included                                 │
  │                                                                          │
  │  each suggestion:                                                        │
  │  {                                                                       │
  │    rank, type, description, duration_mins (15-min increments),           │
  │    intensity (low/medium/high), specific_suggestion,                     │
  │    reasoning: {                                                          │
  │      energy:  "low (2/5)",                                               │
  │      hrv:     "below average (-16%)",                                    │
  │      weather: "sunny, outdoors ok"                                       │
  │    }                                                                     │
  │  }                                                                       │
  └──────────────────────────────────┬───────────────────────────────────────┘
                                     │ user thumbs up / down (1 or 0)
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                          Feedback Loop                                   │
  │                                                                          │
  │  POST /suggestions/{id}/feedback  { liked: 0 or 1 }                     │
  │  stored with phase + cycle_day                                           │
  │       +                                                                  │
  │  POST /users/{id}/checkin  { energy, soreness, mood }                   │
  │       │                                                                  │
  │       ▼                                                                  │
  │  Profile Updater (Claude call)                                           │
  │  → rewrites relevant phase section of profile_summary                   │
  │  → updates RECENT FEEDBACK block                                         │
  │  → richer context on next /suggest                                       │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## User Profile (NL, structured by phase)

Stored in `users.profile_summary`. Starts from science defaults, updated after every check-in and feedback via a small Claude call. Each phase is independent.

```
GENERAL
- Fitness level: intermediate
- Preferred session length: 46 min (from history)
- Always avoid: swimming, HIIT
- Loves: yoga, pilates, walking

MENSTRUAL PHASE (days ~1–5)
- Typical energy: low
- Default workouts: yin yoga, walking, mat pilates, foam rolling
- Personal notes: prefers rest day 1, short walks from day 2

FOLLICULAR PHASE (days ~6–13)
- Typical energy: rising
- Default workouts: running, cardio, power vinyasa
- Personal notes: enjoys vinyasa + moderate cardio, energy builds mid-week

OVULATORY PHASE (days ~14–16)
- Typical energy: peak
- Default workouts: cycling, HIIT, crossfit, bootcamp
- Personal notes: prefers structured classes over solo cardio

LUTEAL PHASE (days ~17–28)
- Typical energy: declining, especially days 20+
- Default workouts: yoga, pilates, low incline walking, barre
- Personal notes: yoga and pilates rated highest; barre and strength
  rated poorly, especially late luteal (day 20+)

RECENT FEEDBACK
- 1  yin yoga [luteal day 18]
- 1  low incline walking [luteal day 21]
- 0  strength training [luteal day 22]
- 0  barre [luteal day 20]
```

---

## Phase Science Baseline

Used as defaults at cold start. Personal patterns override once data builds up.

| Phase | Days | Energy | Default Workouts |
|-------|------|--------|-----------------|
| Menstrual | ~1–5 | Low | Walking, yin yoga, mat pilates, foam rolling |
| Follicular | ~6–13 | Rising | Running, cardio, power vinyasa, swimming |
| Ovulatory | ~14–16 | Peak | Cycling, HIIT, crossfit, bootcamp |
| Luteal | ~17–28 | Declining | Strength training, low incline walking, yoga, barre, pilates |

---

## Biometrics Tracked

| Metric | Description |
|--------|-------------|
| HRV | Heart rate variability — recovery signal |
| Resting HR | Baseline heart rate |
| Sleep score | 0–100 composite |
| Sleep hours | Total sleep |
| BBT | Basal body temperature — rises after ovulation |
| Stress score | 0–100 (lower = less stressed) |
| Readiness score | 0–100 Oura/Whoop-style composite |
| Steps | Previous day activity level |

All compared to personal phase averages, not population norms.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Profile + cycle info + checkin streak |
| PATCH | `/users/{id}/preferences` | Update workout likes/dislikes |
| POST | `/users/{id}/checkin` | Log energy (1–5), soreness (1–5), mood |
| POST | `/users/{id}/cycle` | Log period start date |
| POST | `/users/{id}/biometrics` | Log today's biometrics |
| GET | `/users/{id}/suggest` | Run agent → top + all 5 suggestions |
| POST | `/suggestions/{id}/feedback` | Thumbs up/down `{"liked": true/false}` |
| GET | `/users/{id}/history` | Past suggestions + feedback |

---

## Demo Users

**Alex** (user id: 1) — standard cycle pattern
- Loves yoga, pilates, walking. Dislikes HIIT and swimming.
- Energy drops in late luteal. High-intensity workouts rated poorly in that window.
- Average session: ~46 min.

**Jordan** (user id: 2) — non-standard pattern
- Loves strength training, HIIT, cycling. Dislikes yoga and barre.
- Maintains high intensity even in luteal — her data overrides phase defaults.
- Average session: ~49 min.

Both seeded with 1 year of history (~365 check-ins, biometrics, ~300 workout ratings).

---

## Setup

```bash
git clone https://github.com/yoonoolee/spark_hackathon.git
cd spark_hackathon

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# add ANTHROPIC_API_KEY to .env

python generate_mock_data.py
uvicorn main:app --reload
```

### Try it

```bash
# Top suggestion + all 5 for Alex
curl http://localhost:8000/users/1/suggest

# Daily check-in
curl -X POST http://localhost:8000/users/1/checkin \
  -H "Content-Type: application/json" \
  -d '{"energy": 2, "soreness": 3, "mood": "anxious"}'

# Thumbs down a suggestion
curl -X POST http://localhost:8000/suggestions/1/feedback \
  -H "Content-Type: application/json" \
  -d '{"liked": false, "workout_type": "strength training"}'

# Jordan — different suggestions same cycle day (personal history overrides phase defaults)
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
| Weather | Mocked, seasonal + deterministic per date |
| Biometrics | Mocked (mirrors HealthKit structure) |
