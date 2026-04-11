from datetime import date
import database as db
from services.cycle import get_cycle_info, get_cycle_logs_for_user
from services.profile import build_cold_start_profile
from services.analytics import analyze_feedback_patterns, get_avg_duration
from services.weather import get_weather


def assemble_context(user_id: int, target_date: str = None) -> dict:
    today = target_date or date.today().isoformat()

    user = db.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Cycle info
    period_dates = get_cycle_logs_for_user(user_id)
    cycle_info = get_cycle_info(period_dates, user["cycle_length_avg"], date.fromisoformat(today))

    # Check-in (today or most recent)
    checkin = db.get_latest_checkin(user_id, today) or db.get_latest_checkin(user_id)

    # Biometrics
    biometrics = db.get_latest_biometrics(user_id, today)
    phase_avgs = db.get_phase_biometric_avg(user_id, cycle_info.get("phase"))

    # Recent feedback
    feedback_history = db.get_feedback_for_phase(user_id, cycle_info.get("phase"), cycle_info.get("cycle_day"))

    # Weather + streak
    weather = get_weather(today)
    streak = db.get_checkin_streak(user_id)

    # NL profile
    profile_summary = user.get("profile_summary", "").strip()
    if not profile_summary:
        profile_summary = build_cold_start_profile(user)

    prefs = user.get("workout_preferences", {})

    return {
        "user": {
            "id": user_id,
            "name": user["name"],
            "fitness_level": user["fitness_level"],
            "dislikes": prefs.get("dislikes", []),
            "likes": prefs.get("likes", []),
            "profile_summary": profile_summary,
        },
        "cycle": cycle_info,
        "checkin": {
            "energy": checkin["energy"] if checkin else None,
            "soreness": checkin["soreness"] if checkin else None,
            "mood": checkin["mood"] if checkin else None,
            "date": checkin["date"] if checkin else None,
        },
        "biometrics": {
            "hrv":             biometrics["hrv"] if biometrics else None,
            "resting_hr":      biometrics["resting_hr"] if biometrics else None,
            "sleep_score":     biometrics["sleep_score"] if biometrics else None,
            "sleep_hours":     biometrics["sleep_hours"] if biometrics else None,
            "bbt":             biometrics["bbt"] if biometrics else None,
            "stress_score":    biometrics["stress_score"] if biometrics else None,
            "readiness_score": biometrics["readiness_score"] if biometrics else None,
            "steps":           biometrics["steps"] if biometrics else None,
            "hrv_phase_avg":      phase_avgs.get("hrv_avg"),
            "sleep_avg":          phase_avgs.get("sleep_avg"),
            "stress_avg":         phase_avgs.get("stress_avg"),
            "readiness_avg":      phase_avgs.get("readiness_avg"),
            "steps_avg":          phase_avgs.get("steps_avg"),
        },
        "recent_feedback": feedback_history[:12],
        "pattern_analysis": analyze_feedback_patterns(user_id),
        "avg_duration_mins": get_avg_duration(user_id),
        "weather": weather,
        "streak": streak,
        "date": today,
    }
