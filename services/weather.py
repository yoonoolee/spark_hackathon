"""
Mocked weather service. Returns realistic seasonal weather for a given date.
Structure mirrors a real weather API so it's easy to swap in later.
"""

from datetime import date
import random

SEASONS = {
    (3, 4, 5):  ("spring", 58, ["sunny", "partly cloudy", "rainy"]),
    (6, 7, 8):  ("summer", 78, ["sunny", "sunny", "partly cloudy"]),
    (9, 10, 11):("fall",   55, ["partly cloudy", "rainy", "sunny"]),
    (12, 1, 2): ("winter", 40, ["cloudy", "rainy", "sunny"]),
}


def get_weather(target_date: str = None) -> dict:
    d = date.fromisoformat(target_date) if target_date else date.today()
    rng = random.Random(d.toordinal())  # deterministic per date

    for months, (season, base_temp, conditions) in SEASONS.items():
        if d.month in months:
            temp = base_temp + rng.randint(-8, 8)
            condition = rng.choice(conditions)
            return {
                "temp_f": temp,
                "condition": condition,
                "season": season,
                "outdoor_friendly": condition in ("sunny", "partly cloudy") and temp > 40,
            }

    return {"temp_f": 65, "condition": "sunny", "season": "spring", "outdoor_friendly": True}
