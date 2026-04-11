import anthropic
import json
import os
from services.cycle import PHASE_BASELINES

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def build_prompt(ctx: dict) -> str:
    user = ctx["user"]
    cycle = ctx["cycle"]
    checkin = ctx["checkin"]
    bio = ctx["biometrics"]

    # Cycle section
    if cycle["cycle_day"]:
        cycle_str = (
            f"Cycle day {cycle['cycle_day']} of ~{cycle['cycle_length_avg']} days | "
            f"Phase: {cycle['phase'].upper()} | "
            f"{cycle['days_until_period']} days until next period"
        )
    else:
        cycle_str = "Cycle data not available yet"

    # Check-in section
    if checkin["energy"] is not None:
        checkin_str = (
            f"Energy: {checkin['energy']}/5 | "
            f"Soreness: {checkin['soreness']}/5 | "
            f"Mood: {checkin['mood']}"
        )
    else:
        checkin_str = "No check-in logged today"

    # Biometrics section
    bio_parts = []
    if bio["hrv"] is not None:
        hrv_note = ""
        if bio["hrv_phase_avg"]:
            diff_pct = round((bio["hrv"] - bio["hrv_phase_avg"]) / bio["hrv_phase_avg"] * 100)
            hrv_note = f" (phase avg: {bio['hrv_phase_avg']}, {'+' if diff_pct >= 0 else ''}{diff_pct}%)"
        bio_parts.append(f"HRV: {bio['hrv']}{hrv_note}")
    if bio["sleep_score"] is not None:
        sleep_note = f" (avg: {bio['sleep_avg']})" if bio["sleep_avg"] else ""
        bio_parts.append(f"Sleep: {bio['sleep_score']}/100{sleep_note}")
    if bio["sleep_hours"] is not None:
        bio_parts.append(f"Sleep hours: {bio['sleep_hours']}")
    bio_str = " | ".join(bio_parts) if bio_parts else "No biometric data available"

    # Recent feedback
    feedback_lines = []
    for f in ctx.get("recent_feedback", [])[:8]:
        icon = "👍" if f["liked"] else "👎"
        feedback_lines.append(f"  {icon} {f['workout_type']}")
    feedback_str = "\n".join(feedback_lines) if feedback_lines else "  No feedback yet"

    # Phase fallback baselines
    phase = cycle.get("phase") or "follicular"
    fallback = ", ".join(PHASE_BASELINES.get(phase, []))

    dislikes_str = ", ".join(user["dislikes"]) if user["dislikes"] else "none"

    return f"""You are an expert in female physiology and cycle-synced fitness coaching.
Your job is to suggest the 3 best workouts for this user TODAY based on where she is in her cycle and her personal patterns.

Personal history and patterns ALWAYS override generic phase guidelines.
Never suggest workouts the user dislikes.

---
USER PROFILE:
{user['profile_summary']}

---
WHERE SHE IS TODAY ({ctx['date']}):
{cycle_str}
{checkin_str}
{bio_str}

RECENT FEEDBACK:
{feedback_str}

HARD CONSTRAINTS — never suggest these: {dislikes_str}

PHASE SCIENCE FALLBACK (use only if personal history is absent for this phase):
{phase.upper()} defaults: {fallback}

---
Return ONLY a JSON array of exactly 3 workout suggestions, ranked best to worst fit for today.
Each suggestion must follow this exact structure:
{{
  "rank": 1,
  "type": "<workout category>",
  "description": "<3-6 word style descriptor>",
  "duration_mins": <number>,
  "intensity": "<low | low-medium | medium | medium-high | high>",
  "specific_suggestion": "<one concrete sentence of what to do>",
  "reasoning": "<1-2 sentences referencing her specific data, not generic advice>"
}}

Return only the JSON array, no explanation or markdown."""


def get_suggestions(ctx: dict) -> list:
    prompt = build_prompt(ctx)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    suggestions = json.loads(raw)
    return suggestions
