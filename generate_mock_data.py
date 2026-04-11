"""
Generates 1 year of realistic mock data for two users and writes to data/ as JSON.
Alex: standard cycle pattern — energy drops in luteal, loves yoga/pilates
Jordan: non-standard — high intensity even in luteal, dislikes yoga
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

START_DATE = date(2024, 4, 11)
END_DATE = date(2025, 4, 10)

PHASE_BASELINES = {
    "menstrual":  ["walking", "yin yoga", "mat pilates", "foam rolling"],
    "follicular": ["running", "cardio", "power vinyasa", "swimming"],
    "ovulatory":  ["cycling", "cardio", "HIIT", "crossfit", "bootcamp"],
    "luteal":     ["strength training", "low incline walking", "yoga", "barre", "pilates"],
}

MOODS = ["energized", "calm", "motivated", "tired", "anxious", "happy", "neutral", "sluggish"]


def get_phase(cycle_day: int, cycle_length: int = 28) -> str:
    ratio = cycle_length / 28
    if cycle_day <= round(5 * ratio):
        return "menstrual"
    elif cycle_day <= round(13 * ratio):
        return "follicular"
    elif cycle_day <= round(16 * ratio):
        return "ovulatory"
    else:
        return "luteal"


def generate_cycle_logs(start: date, end: date, cycle_length_avg: int, jitter: int = 1) -> list[dict]:
    logs = []
    current = start
    while current <= end:
        logs.append({"period_start_date": current.isoformat()})
        offset = random.randint(-jitter, jitter)
        current += timedelta(days=cycle_length_avg + offset)
    return logs


def get_cycle_day(d: date, cycle_logs: list[dict], cycle_length: int) -> tuple[int, str]:
    starts = sorted([date.fromisoformat(l["period_start_date"]) for l in cycle_logs])
    last_start = None
    for s in starts:
        if s <= d:
            last_start = s
        else:
            break
    if last_start is None:
        return 1, "follicular"
    cycle_day = (d - last_start).days + 1
    if cycle_day > cycle_length + 7:
        cycle_day = cycle_day % cycle_length or cycle_length
    return cycle_day, get_phase(cycle_day, cycle_length)


# ── Alex ───────────────────────────────────────────────────────────────────────
# Standard pattern: low energy in luteal, loves yoga/pilates, dislikes HIIT/swimming

def alex_energy(phase: str, cycle_day: int) -> int:
    base = {"menstrual": 2, "follicular": 4, "ovulatory": 5, "luteal": 3}[phase]
    if phase == "luteal" and cycle_day >= 20:
        base = 2
    return max(1, min(5, base + random.randint(-1, 1)))


def alex_soreness(phase: str) -> int:
    base = {"menstrual": 3, "follicular": 2, "ovulatory": 2, "luteal": 3}[phase]
    return max(1, min(5, base + random.randint(-1, 1)))


def alex_hrv(phase: str) -> float:
    base = {"menstrual": 48, "follicular": 58, "ovulatory": 62, "luteal": 50}[phase]
    return round(base + random.uniform(-5, 5), 1)


def alex_sleep(phase: str) -> tuple[float, float]:
    base = {"menstrual": 72, "follicular": 80, "ovulatory": 82, "luteal": 74}[phase]
    score = round(max(50, min(100, base + random.uniform(-8, 8))), 1)
    hours = round(random.uniform(6.0, 8.5), 1)
    return score, hours


def alex_workout_and_liked(phase: str, cycle_day: int, energy: int) -> tuple[dict, bool]:
    candidates = {
        "menstrual":  ["walking", "yin yoga", "mat pilates", "foam rolling"],
        "follicular": ["running", "power vinyasa", "cardio", "pilates"],
        "ovulatory":  ["cycling", "cardio", "crossfit", "bootcamp"],
        "luteal":     ["yoga", "pilates", "low incline walking", "barre", "strength training"],
    }[phase]

    # Alex dislikes HIIT and swimming — never appear
    workout = random.choice(candidates)
    intensity_map = {
        "menstrual": "low", "follicular": "medium", "ovulatory": "high",
        "luteal": "low" if cycle_day >= 20 else "low-medium"
    }
    intensity = intensity_map[phase]
    duration = random.choice([25, 30, 35, 40])

    # Liked: high probability for yoga/pilates in luteal, low for strength in late luteal
    if phase == "luteal" and cycle_day >= 20:
        liked = workout in ["yoga", "yin yoga", "pilates", "walking", "low incline walking"]
        if workout == "strength training":
            liked = random.random() < 0.2
    elif phase == "luteal":
        liked = random.random() < 0.6
    else:
        liked = random.random() < 0.75

    suggestion = {
        "type": workout,
        "description": f"{intensity} {workout}",
        "duration_mins": duration,
        "intensity": intensity,
        "specific_suggestion": f"{workout.capitalize()} session focusing on how you feel today",
    }
    return suggestion, liked


# ── Jordan ─────────────────────────────────────────────────────────────────────
# Non-standard: stays high intensity even in luteal, dislikes yoga/barre

def jordan_energy(phase: str, cycle_day: int) -> int:
    # Jordan's energy stays higher even in luteal
    base = {"menstrual": 3, "follicular": 4, "ovulatory": 5, "luteal": 4}[phase]
    return max(1, min(5, base + random.randint(-1, 1)))


def jordan_hrv(phase: str) -> float:
    # Jordan's HRV stays higher in luteal — she's an outlier
    base = {"menstrual": 52, "follicular": 60, "ovulatory": 65, "luteal": 58}[phase]
    return round(base + random.uniform(-4, 4), 1)


def jordan_sleep(phase: str) -> tuple[float, float]:
    base = {"menstrual": 75, "follicular": 82, "ovulatory": 84, "luteal": 79}[phase]
    score = round(max(55, min(100, base + random.uniform(-6, 6))), 1)
    hours = round(random.uniform(6.5, 8.5), 1)
    return score, hours


def jordan_workout_and_liked(phase: str, cycle_day: int, energy: int) -> tuple[dict, bool]:
    # Jordan loves HIIT/strength/cycling even in luteal — her personal pattern
    candidates = {
        "menstrual":  ["strength training", "cycling", "low incline walking", "pilates"],
        "follicular": ["HIIT", "strength training", "cycling", "running"],
        "ovulatory":  ["HIIT", "crossfit", "bootcamp", "cycling", "strength training"],
        "luteal":     ["strength training", "HIIT", "cycling", "running"],  # overrides defaults
    }[phase]

    # Jordan dislikes yoga and barre
    workout = random.choice(candidates)
    intensity = "high" if phase in ["ovulatory", "luteal"] else "medium"
    duration = random.choice([30, 40, 45, 50])

    # Jordan rates her preferred workouts highly across all phases
    liked = workout in ["HIIT", "strength training", "cycling", "crossfit"]
    if not liked:
        liked = random.random() < 0.5

    suggestion = {
        "type": workout,
        "description": f"{intensity} {workout}",
        "duration_mins": duration,
        "intensity": intensity,
        "specific_suggestion": f"{workout.capitalize()} session at full effort",
    }
    return suggestion, liked


# ── Alex profile summary (pre-built to show rich data) ────────────────────────
ALEX_PROFILE = """GENERAL
- Fitness level: intermediate
- Preferred session length: 30 min
- Always avoid: swimming, HIIT
- Loves: yoga, pilates, walking

MENSTRUAL PHASE (days ~1–5)
- Typical energy: low
- Default workouts: yin yoga, walking, mat pilates, foam rolling
- Personal notes: prefers rest or very light movement on day 1; short walks work well from day 2 onward

FOLLICULAR PHASE (days ~6–13)
- Typical energy: rising
- Default workouts: running, cardio, power vinyasa, pilates
- Personal notes: enjoys increasing intensity through the week; vinyasa rated consistently well here

OVULATORY PHASE (days ~14–16)
- Typical energy: peak
- Default workouts: cycling, cardio, crossfit, bootcamp
- Personal notes: peak performance window; prefers structured classes over solo cardio

LUTEAL PHASE (days ~17–28)
- Typical energy: declining, especially days 20–28
- Default workouts: yoga, pilates, low incline walking, barre
- Personal notes: energy drops noticeably from day 20; consistently rates strength training and cardio below 3/5 in this window; yoga and pilates rated 4.5+/5 here; prefers shorter sessions (25–30 min)

RECENT FEEDBACK
- 👍 yin yoga (luteal day 24)
- 👍 walking (luteal day 21)
- 👎 strength training (luteal day 22) — felt too heavy
- 👍 power vinyasa (follicular day 10)
- 👎 cardio (luteal day 19) — low energy"""

# ── Jordan profile summary ─────────────────────────────────────────────────────
JORDAN_PROFILE = """GENERAL
- Fitness level: advanced
- Preferred session length: 40 min
- Always avoid: yoga, barre
- Loves: strength training, HIIT, cycling

MENSTRUAL PHASE (days ~1–5)
- Typical energy: moderate
- Default workouts: strength training, cycling, low incline walking
- Personal notes: can handle moderate intensity even during period; prefers strength over cardio on day 1–2

FOLLICULAR PHASE (days ~6–12)
- Typical energy: high
- Default workouts: HIIT, strength training, cycling, running
- Personal notes: strong performance; responds well to progressive overload this week

OVULATORY PHASE (days ~13–15)
- Typical energy: peak
- Default workouts: HIIT, crossfit, bootcamp, cycling
- Personal notes: best performance of the cycle; PRs often happen here

LUTEAL PHASE (days ~16–26)
- Typical energy: high (unlike typical patterns)
- Default workouts: strength training, HIIT, cycling
- Personal notes: maintains high intensity throughout luteal — rated HIIT and strength 4+/5 even in late luteal; this is atypical but consistent across her history

RECENT FEEDBACK
- 👍 HIIT (luteal day 20)
- 👍 strength training (luteal day 23)
- 👍 cycling (luteal day 18)
- 👎 walking (follicular day 8) — too easy
- 👍 crossfit (ovulatory day 14)"""


# ── Main generator ─────────────────────────────────────────────────────────────

def generate_user_data(
    user_id, name, cycle_length_avg, jitter,
    energy_fn, hrv_fn, sleep_fn, workout_fn, soreness_fn=None
):
    cycle_logs = generate_cycle_logs(START_DATE, END_DATE, cycle_length_avg, jitter)
    checkins, biometrics, history = [], [], []

    d = START_DATE
    while d <= END_DATE:
        cycle_day, phase = get_cycle_day(d, cycle_logs, cycle_length_avg)
        energy = energy_fn(phase, cycle_day)
        soreness = soreness_fn(phase) if soreness_fn else max(1, min(5, 3 + random.randint(-1, 1)))
        mood = random.choice(MOODS)
        hrv = hrv_fn(phase)
        sleep_score, sleep_hours = sleep_fn(phase)
        resting_hr = round(random.uniform(58, 72), 1)

        checkins.append({
            "date": d.isoformat(),
            "energy": energy,
            "soreness": soreness,
            "mood": mood,
        })

        biometrics.append({
            "date": d.isoformat(),
            "hrv": hrv,
            "resting_hr": resting_hr,
            "sleep_score": sleep_score,
            "sleep_hours": sleep_hours,
        })

        # ~80% of days have a workout
        if random.random() < 0.8:
            suggestion, liked = workout_fn(phase, cycle_day, energy)
            history.append({
                "date": d.isoformat(),
                "suggestion": suggestion,
                "liked": liked,
            })

        d += timedelta(days=1)

    return cycle_logs, checkins, biometrics, history


def main():
    print("Generating mock data...")

    alex_cycles, alex_checkins, alex_bio, alex_history = generate_user_data(
        1, "Alex", 28, 1,
        energy_fn=alex_energy,
        hrv_fn=alex_hrv,
        sleep_fn=alex_sleep,
        workout_fn=alex_workout_and_liked,
        soreness_fn=alex_soreness,
    )

    jordan_cycles, jordan_checkins, jordan_bio, jordan_history = generate_user_data(
        2, "Jordan", 26, 2,
        energy_fn=jordan_energy,
        hrv_fn=jordan_hrv,
        sleep_fn=jordan_sleep,
        workout_fn=jordan_workout_and_liked,
    )

    users = [
        {
            "id": 1,
            "name": "Alex",
            "cycle_length_avg": 28,
            "fitness_level": "intermediate",
            "workout_preferences": {
                "likes": ["yoga", "pilates", "walking"],
                "dislikes": ["swimming", "HIIT"]
            },
            "profile_summary": ALEX_PROFILE,
        },
        {
            "id": 2,
            "name": "Jordan",
            "cycle_length_avg": 26,
            "fitness_level": "advanced",
            "workout_preferences": {
                "likes": ["strength training", "HIIT", "cycling"],
                "dislikes": ["yoga", "barre"]
            },
            "profile_summary": JORDAN_PROFILE,
        },
    ]

    files = {
        "users.json": users,
        "alex_cycle_logs.json": alex_cycles,
        "alex_checkins.json": alex_checkins,
        "alex_biometrics.json": alex_bio,
        "alex_workout_history.json": alex_history,
        "jordan_cycle_logs.json": jordan_cycles,
        "jordan_checkins.json": jordan_checkins,
        "jordan_biometrics.json": jordan_bio,
        "jordan_workout_history.json": jordan_history,
    }

    for filename, data in files.items():
        path = DATA_DIR / filename
        path.write_text(json.dumps(data, indent=2))
        print(f"  wrote {path} ({len(data)} records)")

    print(f"\nDone. {sum(len(v) for v in files.values())} total records across {len(files)} files.")


if __name__ == "__main__":
    main()
