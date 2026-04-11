from datetime import date, timedelta
from typing import Optional

PHASE_DAYS = {
    "menstrual":  (1, 5),
    "follicular": (6, 13),
    "ovulatory":  (14, 16),
    "luteal":     (17, 28),
}

PHASE_BASELINES = {
    "menstrual":  ["walking", "yin yoga", "mat pilates", "foam rolling"],
    "follicular": ["running", "cardio", "power vinyasa", "swimming"],
    "ovulatory":  ["cycling", "cardio", "HIIT", "crossfit", "bootcamp"],
    "luteal":     ["strength training", "low incline walking", "yoga", "barre", "pilates"],
}

PHASE_ENERGY = {
    "menstrual":  "low",
    "follicular": "rising",
    "ovulatory":  "peak",
    "luteal":     "declining",
}


def get_phase(cycle_day: int, cycle_length: int = 28) -> str:
    # Scale phase boundaries to actual cycle length
    ratio = cycle_length / 28
    if cycle_day <= round(5 * ratio):
        return "menstrual"
    elif cycle_day <= round(13 * ratio):
        return "follicular"
    elif cycle_day <= round(16 * ratio):
        return "ovulatory"
    else:
        return "luteal"


def get_cycle_info(period_start_dates: list[str], cycle_length_avg: int = 28, today: Optional[date] = None) -> dict:
    if today is None:
        today = date.today()

    if not period_start_dates:
        return {
            "cycle_day": None,
            "phase": None,
            "days_until_period": None,
            "cycle_length_avg": cycle_length_avg,
            "last_period_start": None,
        }

    # Most recent period start
    sorted_dates = sorted(period_start_dates, reverse=True)
    last_start = date.fromisoformat(sorted_dates[0])

    cycle_day = (today - last_start).days + 1

    # If cycle_day exceeds avg length, we're likely in a new cycle with no log yet
    if cycle_day > cycle_length_avg + 7:
        # Estimate based on avg — mark as uncertain
        cycle_day = cycle_day % cycle_length_avg or cycle_length_avg

    phase = get_phase(cycle_day, cycle_length_avg)
    days_until_period = cycle_length_avg - cycle_day + 1

    return {
        "cycle_day": cycle_day,
        "phase": phase,
        "days_until_period": max(0, days_until_period),
        "cycle_length_avg": cycle_length_avg,
        "last_period_start": sorted_dates[0],
    }


def get_cycle_logs_for_user(user_id: int) -> list[str]:
    from database import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT period_start_date FROM cycle_logs WHERE user_id = ? ORDER BY period_start_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [r["period_start_date"] for r in rows]
