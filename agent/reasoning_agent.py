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
    def fmt_metric(label, val, avg, unit=""):
        if val is None:
            return None
        note = ""
        if avg:
            diff_pct = round((val - avg) / avg * 100)
            note = f" (avg: {avg}{unit}, {'+' if diff_pct >= 0 else ''}{diff_pct}%)"
        return f"{label}: {val}{unit}{note}"

    bio_parts = list(filter(None, [
        fmt_metric("HRV", bio.get("hrv"), bio.get("hrv_phase_avg")),
        fmt_metric("Sleep score", bio.get("sleep_score"), bio.get("sleep_avg"), "/100"),
        fmt_metric("Sleep hours", bio.get("sleep_hours"), None, "h"),
        fmt_metric("Readiness", bio.get("readiness_score"), bio.get("readiness_avg"), "/100"),
        fmt_metric("Stress", bio.get("stress_score"), bio.get("stress_avg"), "/100"),
        fmt_metric("BBT", bio.get("bbt"), None, "°F") if bio.get("bbt") else None,
        fmt_metric("Steps yesterday", bio.get("steps"), bio.get("steps_avg")),
        fmt_metric("Resting HR", bio.get("resting_hr"), None, "bpm"),
    ]))
    bio_str = "\n".join(bio_parts) if bio_parts else "No biometric data available"

    # Recent feedback — phase-specific first, then cross-phase
    feedback_lines = []
    for f in ctx.get("recent_feedback", [])[:12]:
        icon = "👍" if f["liked"] else "👎"
        phase_tag = f"  [{f['phase']} day {f['cycle_day']}]" if f.get("phase") else ""
        note_tag = f" — \"{f['note']}\"" if f.get("note") else ""
        feedback_lines.append(f"  {icon} {f['workout_type']}{phase_tag}{note_tag}")
    feedback_str = "\n".join(feedback_lines) if feedback_lines else "  No feedback yet"

    # Phase fallback baselines
    phase = cycle.get("phase") or "follicular"
    fallback = ", ".join(PHASE_BASELINES.get(phase, []))

    dislikes_str = ", ".join(user["dislikes"]) if user["dislikes"] else "none"

    return f"""You are an expert in female physiology and cycle-synced fitness coaching.

Spark gives personalized workout recommendations that learn your cycle, not just the textbook one.
Most cycle apps give generic phase advice. Spark learns that everyone's cycle is different —
because it tracks personal patterns, not population averages.

Your job is to suggest the 3 best workouts for this user TODAY based on where she is in her cycle and her personal patterns.
Personal history and patterns ALWAYS override generic phase guidelines.
Never suggest workouts the user dislikes.
Use feedback patterns to infer preferences — if she consistently skips or rates something poorly across phases, treat it as a general dislike even if not listed explicitly.

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
