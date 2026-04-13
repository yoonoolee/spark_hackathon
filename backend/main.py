from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from typing import Optional
import json
from dotenv import load_dotenv

load_dotenv()

import database as db
from database import init_db, seed_from_json
from agent.context_assembler import assemble_context
from agent.reasoning_agent import get_suggestions
from services.cycle import get_cycle_info, get_cycle_logs_for_user
from services.profile import update_profile, build_cold_start_profile

app = FastAPI(title="Spark — Cycle-Synced Fitness Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    seed_from_json()


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    name: str
    cycle_length_avg: int = 28
    fitness_level: str = "intermediate"
    likes: list[str] = []
    dislikes: list[str] = []

class UpdatePreferencesRequest(BaseModel):
    likes: Optional[list[str]] = None
    dislikes: Optional[list[str]] = None

class CheckinRequest(BaseModel):
    energy: int       # 1–5
    soreness: int     # 1–5
    mood: str
    date: Optional[str] = None

class CycleLogRequest(BaseModel):
    period_start_date: str

class BiometricsRequest(BaseModel):
    hrv: Optional[float] = None
    resting_hr: Optional[float] = None
    sleep_score: Optional[float] = None
    sleep_hours: Optional[float] = None
    bbt: Optional[float] = None             # basal body temperature (°F)
    stress_score: Optional[float] = None   # 0–100, lower is better
    readiness_score: Optional[float] = None # 0–100 composite (Oura/Whoop style)
    steps: Optional[int] = None            # steps from previous day
    date: Optional[str] = None

class FeedbackRequest(BaseModel):
    liked: bool
    workout_type: Optional[str] = None
    note: Optional[str] = None


# ── Users ──────────────────────────────────────────────────────────────────────

@app.get("/users")
def list_users():
    conn = db.get_db()
    rows = conn.execute("SELECT id, name, fitness_level, cycle_length_avg FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/users", status_code=201)
def create_user(req: CreateUserRequest):
    conn = db.get_db()
    prefs = json.dumps({"likes": req.likes, "dislikes": req.dislikes})

    # Build cold start profile
    user_dict = {
        "fitness_level": req.fitness_level,
        "workout_preferences": {"likes": req.likes, "dislikes": req.dislikes},
    }
    profile = build_cold_start_profile(user_dict)

    c = conn.cursor()
    c.execute("""
        INSERT INTO users (name, cycle_length_avg, fitness_level, workout_preferences, profile_summary)
        VALUES (?, ?, ?, ?, ?)
    """, (req.name, req.cycle_length_avg, req.fitness_level, prefs, profile))
    user_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": user_id, "name": req.name}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    cycle_logs = get_cycle_logs_for_user(user_id)
    cycle_info = get_cycle_info(cycle_logs, user["cycle_length_avg"])
    streak = db.get_checkin_streak(user_id)
    return {**user, "cycle": cycle_info, "checkin_streak": streak}


@app.patch("/users/{user_id}/preferences")
def update_preferences(user_id: int, req: UpdatePreferencesRequest):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    prefs = user["workout_preferences"]
    if req.likes is not None:
        prefs["likes"] = req.likes
    if req.dislikes is not None:
        prefs["dislikes"] = req.dislikes
    conn = db.get_db()
    conn.execute("UPDATE users SET workout_preferences = ? WHERE id = ?", (json.dumps(prefs), user_id))
    conn.commit()
    conn.close()
    return {"updated": True, "preferences": prefs}


# ── Check-in ───────────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/checkin")
def checkin(user_id: int, req: CheckinRequest):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    checkin_date = req.date or date.today().isoformat()

    conn = db.get_db()
    conn.execute("""
        INSERT OR REPLACE INTO checkins (user_id, date, energy, soreness, mood)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, checkin_date, req.energy, req.soreness, req.mood))
    conn.commit()
    conn.close()

    # Update NL profile async-style (in-process for now)
    cycle_logs = get_cycle_logs_for_user(user_id)
    cycle_info = get_cycle_info(cycle_logs, user["cycle_length_avg"])
    update_profile(user_id, "checkin", {
        "date": checkin_date,
        "energy": req.energy,
        "soreness": req.soreness,
        "mood": req.mood,
        "phase": cycle_info.get("phase"),
    })

    return {"logged": True, "date": checkin_date}


# ── Cycle log ──────────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/cycle")
def log_cycle(user_id: int, req: CycleLogRequest):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    conn = db.get_db()
    conn.execute("INSERT INTO cycle_logs (user_id, period_start_date) VALUES (?, ?)",
                 (user_id, req.period_start_date))
    conn.commit()
    conn.close()
    return {"logged": True, "period_start_date": req.period_start_date}


# ── Biometrics ─────────────────────────────────────────────────────────────────

@app.post("/users/{user_id}/biometrics")
def log_biometrics(user_id: int, req: BiometricsRequest):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    bio_date = req.date or date.today().isoformat()
    conn = db.get_db()
    conn.execute("""
        INSERT OR REPLACE INTO biometric_snapshots
        (user_id, date, hrv, resting_hr, sleep_score, sleep_hours, bbt, stress_score, readiness_score, steps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, bio_date, req.hrv, req.resting_hr, req.sleep_score, req.sleep_hours,
          req.bbt, req.stress_score, req.readiness_score, req.steps))
    conn.commit()
    conn.close()
    return {"logged": True, "date": bio_date}


# ── Suggest ────────────────────────────────────────────────────────────────────

@app.get("/users/{user_id}/suggest")
def suggest(user_id: int, target_date: Optional[str] = None):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    try:
        ctx = assemble_context(user_id, target_date)
        suggestions = get_suggestions(ctx)
        suggestion_id = db.save_suggestion(user_id, ctx["date"], ctx, suggestions)
        return {
            "suggestion_id": suggestion_id,
            "date": ctx["date"],
            "cycle": ctx["cycle"],
            "weather": ctx["weather"],
            "checkin_streak": ctx["streak"],
            "top": suggestions[0],
            "suggestions": suggestions,
        }
    except Exception as e:
        raise HTTPException(500, f"Agent error: {str(e)}")


# ── Feedback ───────────────────────────────────────────────────────────────────

@app.post("/suggestions/{suggestion_id}/feedback")
def feedback(suggestion_id: int, req: FeedbackRequest):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM workout_suggestions WHERE id = ?", (suggestion_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Suggestion not found")

    suggestion_row = dict(row)
    user_id = suggestion_row["user_id"]

    user = db.get_user(user_id)
    cycle_logs = get_cycle_logs_for_user(user_id)
    cycle_info = get_cycle_info(cycle_logs, user["cycle_length_avg"])

    db.save_feedback(
        suggestion_id, user_id, req.workout_type, req.liked,
        phase=cycle_info.get("phase"),
        cycle_day=cycle_info.get("cycle_day"),
        note=req.note,
    )

    update_profile(user_id, "feedback", {
        "workout_type": req.workout_type,
        "liked": req.liked,
        "note": req.note,
        "phase": cycle_info.get("phase"),
        "cycle_day": cycle_info.get("cycle_day"),
    })

    return {"logged": True, "liked": req.liked}


# ── History ────────────────────────────────────────────────────────────────────

@app.get("/users/{user_id}/profile-history")
def profile_history(user_id: int, limit: int = 30):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    return db.get_profile_history(user_id, limit)


@app.get("/users/{user_id}/history")
def history(user_id: int, limit: int = 30):
    if not db.get_user(user_id):
        raise HTTPException(404, "User not found")
    return db.get_user_history(user_id, limit)
