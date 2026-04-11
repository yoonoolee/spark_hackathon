import sqlite3
import json
import os
from pathlib import Path

DB_PATH = "spark.db"
DATA_DIR = Path("data")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            cycle_length_avg INTEGER DEFAULT 28,
            fitness_level TEXT DEFAULT 'intermediate',
            workout_preferences TEXT DEFAULT '{"likes": [], "dislikes": []}',
            profile_summary TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            energy INTEGER,
            soreness INTEGER,
            mood TEXT,
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS cycle_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            period_start_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS biometric_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hrv REAL,
            resting_hr REAL,
            sleep_score REAL,
            sleep_hours REAL,
            bbt REAL,
            stress_score REAL,
            readiness_score REAL,
            steps INTEGER,
            UNIQUE(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS workout_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            context_snapshot TEXT,
            suggestions TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suggestion_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            workout_type TEXT,
            liked INTEGER NOT NULL,
            phase TEXT,
            cycle_day INTEGER,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (suggestion_id) REFERENCES workout_suggestions(id)
        );
    """)

    conn.commit()
    conn.close()


def seed_from_json():
    if not DATA_DIR.exists():
        print("No data/ directory found — skipping seed. Run generate_mock_data.py first.")
        return

    conn = get_db()
    c = conn.cursor()

    # Users
    users_path = DATA_DIR / "users.json"
    if users_path.exists():
        users = json.loads(users_path.read_text())
        for u in users:
            c.execute("""
                INSERT OR REPLACE INTO users (id, name, cycle_length_avg, fitness_level, workout_preferences, profile_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                u["id"], u["name"], u["cycle_length_avg"],
                u["fitness_level"],
                json.dumps(u["workout_preferences"]),
                u.get("profile_summary", "")
            ))

    # Per-user data
    for username in ["alex", "jordan"]:
        user_id = 1 if username == "alex" else 2

        for table, file_key, columns, values_fn in [
            (
                "checkins",
                f"{username}_checkins.json",
                "(user_id, date, energy, soreness, mood)",
                lambda r, uid=user_id: (uid, r["date"], r["energy"], r["soreness"], r["mood"])
            ),
            (
                "cycle_logs",
                f"{username}_cycle_logs.json",
                "(user_id, period_start_date)",
                lambda r, uid=user_id: (uid, r["period_start_date"])
            ),
            (
                "biometric_snapshots",
                f"{username}_biometrics.json",
                "(user_id, date, hrv, resting_hr, sleep_score, sleep_hours, bbt, stress_score, readiness_score, steps)",
                lambda r, uid=user_id: (uid, r["date"], r["hrv"], r["resting_hr"], r["sleep_score"], r["sleep_hours"], r.get("bbt"), r.get("stress_score"), r.get("readiness_score"), r.get("steps"))
            ),
        ]:
            path = DATA_DIR / file_key
            if path.exists():
                rows = json.loads(path.read_text())
                placeholders = ",".join(["?"] * len(values_fn(rows[0])))
                for row in rows:
                    try:
                        c.execute(
                            f"INSERT OR IGNORE INTO {table} {columns} VALUES ({placeholders})",
                            values_fn(row)
                        )
                    except Exception:
                        pass

        # Workout history → suggestions + feedback tables
        history_path = DATA_DIR / f"{username}_workout_history.json"
        if history_path.exists():
            history = json.loads(history_path.read_text())
            for entry in history:
                c.execute("""
                    INSERT INTO workout_suggestions (user_id, date, suggestions)
                    VALUES (?, ?, ?)
                """, (user_id, entry["date"], json.dumps([entry["suggestion"]])))
                suggestion_id = c.lastrowid
                if "liked" in entry:
                    c.execute("""
                        INSERT INTO feedback (suggestion_id, user_id, workout_type, liked, phase, cycle_day)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (suggestion_id, user_id, entry["suggestion"].get("type"), 1 if entry["liked"] else 0,
                          entry.get("phase"), entry.get("cycle_day")))

    conn.commit()
    conn.close()
    print("Database seeded from JSON.")


def get_user(user_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["workout_preferences"] = json.loads(d["workout_preferences"])
        return d
    return None


def get_latest_checkin(user_id: int, date: str = None):
    conn = get_db()
    if date:
        row = conn.execute(
            "SELECT * FROM checkins WHERE user_id = ? AND date = ?", (user_id, date)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM checkins WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_biometrics(user_id: int, date: str = None):
    conn = get_db()
    if date:
        row = conn.execute(
            "SELECT * FROM biometric_snapshots WHERE user_id = ? AND date <= ? ORDER BY date DESC LIMIT 1",
            (user_id, date)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM biometric_snapshots WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_phase_biometric_avg(user_id: int, phase: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT hrv, sleep_score, stress_score, readiness_score, steps
        FROM biometric_snapshots
        WHERE user_id = ? ORDER BY date DESC LIMIT 90
    """, (user_id,)).fetchall()
    conn.close()
    if not rows:
        return {}

    def avg(vals): return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "hrv_avg":       avg([r["hrv"] for r in rows if r["hrv"]]),
        "sleep_avg":     avg([r["sleep_score"] for r in rows if r["sleep_score"]]),
        "stress_avg":    avg([r["stress_score"] for r in rows if r["stress_score"]]),
        "readiness_avg": avg([r["readiness_score"] for r in rows if r["readiness_score"]]),
        "steps_avg":     avg([r["steps"] for r in rows if r["steps"]]),
    }


def get_feedback_for_phase(user_id: int, phase: str, cycle_day: int):
    conn = get_db()
    # Phase-specific feedback first, then fall back to all recent
    phase_rows = conn.execute("""
        SELECT workout_type, liked, phase, cycle_day, note, created_at
        FROM feedback
        WHERE user_id = ? AND phase = ?
        ORDER BY created_at DESC
        LIMIT 30
    """, (user_id, phase)).fetchall()

    # Also grab a few from other phases so LLM can spot cross-phase patterns
    other_rows = conn.execute("""
        SELECT workout_type, liked, phase, cycle_day, note, created_at
        FROM feedback
        WHERE user_id = ? AND (phase != ? OR phase IS NULL)
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id, phase)).fetchall()

    conn.close()
    return [dict(r) for r in phase_rows] + [dict(r) for r in other_rows]


def save_suggestion(user_id: int, date: str, context_snapshot: dict, suggestions: list):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO workout_suggestions (user_id, date, context_snapshot, suggestions)
        VALUES (?, ?, ?, ?)
    """, (user_id, date, json.dumps(context_snapshot), json.dumps(suggestions)))
    suggestion_id = c.lastrowid
    conn.commit()
    conn.close()
    return suggestion_id


def save_feedback(suggestion_id: int, user_id: int, workout_type: str, liked: bool,
                  phase: str = None, cycle_day: int = None, note: str = None):
    conn = get_db()
    conn.execute("""
        INSERT INTO feedback (suggestion_id, user_id, workout_type, liked, phase, cycle_day, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (suggestion_id, user_id, workout_type, 1 if liked else 0, phase, cycle_day, note))
    conn.commit()
    conn.close()


def update_profile_summary(user_id: int, profile_summary: str):
    conn = get_db()
    conn.execute("UPDATE users SET profile_summary = ? WHERE id = ?", (profile_summary, user_id))
    conn.commit()
    conn.close()


def get_checkin_streak(user_id: int) -> int:
    """Returns number of consecutive days the user has submitted a check-in up to today."""
    from datetime import date, timedelta
    conn = get_db()
    rows = conn.execute("""
        SELECT date FROM checkins WHERE user_id = ?
        ORDER BY date DESC
    """, (user_id,)).fetchall()
    conn.close()

    if not rows:
        return 0

    dates = {r["date"] for r in rows}
    streak = 0
    current = date.today()

    while current.isoformat() in dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


def get_user_history(user_id: int, limit: int = 30):
    conn = get_db()
    rows = conn.execute("""
        SELECT ws.id, ws.date, ws.suggestions,
               f.liked, f.workout_type
        FROM workout_suggestions ws
        LEFT JOIN feedback f ON f.suggestion_id = ws.id
        WHERE ws.user_id = ?
        ORDER BY ws.date DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["suggestions"] = json.loads(d["suggestions"]) if d["suggestions"] else []
        results.append(d)
    return results
