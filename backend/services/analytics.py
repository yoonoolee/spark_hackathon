"""
Analyzes feedback history to surface cross-dimensional patterns:
- Like rate per workout type overall
- Like rate per workout type per phase
- Like rate per workout type vs energy level
- Like rate per workout type vs mood (positive/negative)
- Phase-specific avoidance patterns

Output is a natural language summary injected into the Claude prompt.
"""

from database import get_db

POSITIVE_MOODS = {"energized", "motivated", "happy", "calm"}
NEGATIVE_MOODS = {"tired", "anxious", "sluggish"}

MIN_SAMPLES = 3  # minimum feedback entries needed before reporting a pattern
DEFAULT_DURATION = 60  # fallback if no history


def get_avg_duration(user_id: int) -> int:
    """Returns avg duration from liked workouts. Falls back to DEFAULT_DURATION."""
    conn = get_db()
    rows = conn.execute("""
        SELECT ws.suggestions
        FROM feedback f
        JOIN workout_suggestions ws ON f.suggestion_id = ws.id
        WHERE f.user_id = ? AND f.liked = 1
        ORDER BY f.created_at DESC
        LIMIT 50
    """, (user_id,)).fetchall()
    conn.close()

    import json
    durations = []
    for row in rows:
        try:
            suggestions = json.loads(row["suggestions"])
            for s in suggestions:
                if s.get("duration_mins"):
                    durations.append(s["duration_mins"])
        except Exception:
            pass

    if not durations:
        return DEFAULT_DURATION
    return round(sum(durations) / len(durations))


def _pct(liked, total):
    if total == 0:
        return None
    return round(liked / total * 100)


def analyze_feedback_patterns(user_id: int) -> str:
    conn = get_db()

    # Fetch all feedback joined with checkins (for energy/mood context)
    rows = conn.execute("""
        SELECT
            f.workout_type,
            f.liked,
            f.phase,
            f.cycle_day,
            c.energy,
            c.mood
        FROM feedback f
        JOIN workout_suggestions ws ON f.suggestion_id = ws.id
        LEFT JOIN checkins c ON (c.user_id = f.user_id AND c.date = ws.date)
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    """, (user_id,)).fetchall()

    conn.close()

    if not rows:
        return "No feedback history yet."

    # Group all data by workout type
    from collections import defaultdict
    data = defaultdict(lambda: {
        "total": 0, "liked": 0,
        "by_phase": defaultdict(lambda: {"total": 0, "liked": 0}),
        "high_energy": {"total": 0, "liked": 0},   # energy >= 4
        "low_energy":  {"total": 0, "liked": 0},   # energy <= 2
        "positive_mood": {"total": 0, "liked": 0},
        "negative_mood": {"total": 0, "liked": 0},
        "late_luteal":  {"total": 0, "liked": 0},  # cycle day 20+
    })

    for row in rows:
        wt = row["workout_type"]
        if not wt:
            continue

        liked = bool(row["liked"])
        phase = row["phase"]
        cycle_day = row["cycle_day"]
        energy = row["energy"]
        mood = (row["mood"] or "").lower()

        d = data[wt]
        d["total"] += 1
        if liked:
            d["liked"] += 1

        if phase:
            d["by_phase"][phase]["total"] += 1
            if liked:
                d["by_phase"][phase]["liked"] += 1

        if energy is not None:
            if energy >= 4:
                d["high_energy"]["total"] += 1
                if liked: d["high_energy"]["liked"] += 1
            elif energy <= 2:
                d["low_energy"]["total"] += 1
                if liked: d["low_energy"]["liked"] += 1

        if mood in POSITIVE_MOODS:
            d["positive_mood"]["total"] += 1
            if liked: d["positive_mood"]["liked"] += 1
        elif mood in NEGATIVE_MOODS:
            d["negative_mood"]["total"] += 1
            if liked: d["negative_mood"]["liked"] += 1

        if phase == "luteal" and cycle_day and cycle_day >= 20:
            d["late_luteal"]["total"] += 1
            if liked: d["late_luteal"]["liked"] += 1

    lines = []

    for wt, d in sorted(data.items(), key=lambda x: -x[1]["total"]):
        if d["total"] < MIN_SAMPLES:
            continue

        overall = _pct(d["liked"], d["total"])
        parts = [f"{wt}: liked {overall}% overall ({d['liked']}/{d['total']})"]

        # Phase breakdown — only mention phases with enough data and notable patterns
        phase_notes = []
        for phase in ["menstrual", "follicular", "ovulatory", "luteal"]:
            pd = d["by_phase"].get(phase, {"total": 0, "liked": 0})
            if pd["total"] >= MIN_SAMPLES:
                p = _pct(pd["liked"], pd["total"])
                if p is not None and abs(p - overall) >= 15:
                    direction = "higher" if p > overall else "lower"
                    phase_notes.append(f"{phase} {p}% ({direction})")
        if phase_notes:
            parts.append("by phase: " + ", ".join(phase_notes))

        # Late luteal specifically
        ll = d["late_luteal"]
        if ll["total"] >= MIN_SAMPLES:
            p = _pct(ll["liked"], ll["total"])
            if p is not None and abs(p - overall) >= 15:
                parts.append(f"late luteal (day 20+): {p}%")

        # Energy correlation
        hi = d["high_energy"]
        lo = d["low_energy"]
        if hi["total"] >= MIN_SAMPLES and lo["total"] >= MIN_SAMPLES:
            hi_p = _pct(hi["liked"], hi["total"])
            lo_p = _pct(lo["liked"], lo["total"])
            if hi_p is not None and lo_p is not None and abs(hi_p - lo_p) >= 20:
                parts.append(f"energy: liked {hi_p}% when energy high vs {lo_p}% when low")

        # Mood correlation
        pos = d["positive_mood"]
        neg = d["negative_mood"]
        if pos["total"] >= MIN_SAMPLES and neg["total"] >= MIN_SAMPLES:
            pos_p = _pct(pos["liked"], pos["total"])
            neg_p = _pct(neg["liked"], neg["total"])
            if pos_p is not None and neg_p is not None and abs(pos_p - neg_p) >= 20:
                parts.append(f"mood: liked {pos_p}% when positive mood vs {neg_p}% when negative")

        lines.append("- " + " — ".join(parts))

    if not lines:
        return "Not enough feedback history to identify patterns yet."

    return "\n".join(lines)
