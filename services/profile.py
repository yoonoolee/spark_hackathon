import anthropic
import os
from database import get_user, update_profile_summary
from services.cycle import PHASE_BASELINES

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def build_cold_start_profile(user: dict) -> str:
    prefs = user.get("workout_preferences", {})
    likes = ", ".join(prefs.get("likes", [])) or "not specified"
    dislikes = ", ".join(prefs.get("dislikes", [])) or "none"
    fitness = user.get("fitness_level", "intermediate")

    return f"""GENERAL
- Fitness level: {fitness}
- Preferred session length: 60 min (default — updates from your history)
- Always avoid: {dislikes}
- Loves: {likes}

MENSTRUAL PHASE (days ~1–5)
- Typical energy: low
- Default workouts: {", ".join(PHASE_BASELINES["menstrual"])}
- Personal notes: [no data yet — using science baseline]

FOLLICULAR PHASE (days ~6–13)
- Typical energy: rising
- Default workouts: {", ".join(PHASE_BASELINES["follicular"])}
- Personal notes: [no data yet — using science baseline]

OVULATORY PHASE (days ~14–16)
- Typical energy: peak
- Default workouts: {", ".join(PHASE_BASELINES["ovulatory"])}
- Personal notes: [no data yet — using science baseline]

LUTEAL PHASE (days ~17–28)
- Typical energy: declining
- Default workouts: {", ".join(PHASE_BASELINES["luteal"])}
- Personal notes: [no data yet — using science baseline]

RECENT FEEDBACK
- No feedback yet"""


def update_profile(user_id: int, trigger: str, new_data: dict):
    """
    Trigger: 'checkin' or 'feedback'
    new_data: the new checkin or feedback dict
    """
    user = get_user(user_id)
    if not user:
        return

    current_summary = user.get("profile_summary", "").strip()
    if not current_summary:
        current_summary = build_cold_start_profile(user)

    if trigger == "checkin":
        update_context = (
            f"New daily check-in:\n"
            f"- Energy: {new_data.get('energy')}/5\n"
            f"- Soreness: {new_data.get('soreness')}/5\n"
            f"- Mood: {new_data.get('mood')}\n"
            f"- Date: {new_data.get('date')}\n"
            f"- Cycle phase at time of check-in: {new_data.get('phase', 'unknown')}"
        )
    else:  # feedback
        liked_str = "👍 thumbs up" if new_data.get("liked") else "👎 thumbs down"
        update_context = (
            f"New workout feedback:\n"
            f"- Workout: {new_data.get('workout_type')}\n"
            f"- Feedback: {liked_str}\n"
            f"- Cycle phase: {new_data.get('phase', 'unknown')}\n"
            f"- Cycle day: {new_data.get('cycle_day', 'unknown')}\n"
            f"- Note: {new_data.get('note', 'none')}"
        )

    prompt = f"""You maintain a structured fitness profile for a user of a cycle-synced workout app.

Here is the current profile:
{current_summary}

New data point to incorporate:
{update_context}

Update the profile by:
1. Updating the relevant PHASE section's "Personal notes" with any new patterns or insights
2. Updating the RECENT FEEDBACK section (keep the last 5 feedback items max)
3. Updating GENERAL if any general preferences become clearer

Rules:
- Keep the exact same structure (GENERAL, four PHASE sections, RECENT FEEDBACK)
- Be concise — each personal notes line should be one sentence max
- Replace [no data yet] notes once there is real data
- Do not invent data — only reflect what the user has actually reported
- Return ONLY the updated profile text, no explanation"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    updated_summary = response.content[0].text.strip()
    update_profile_summary(user_id, updated_summary)
    return updated_summary
