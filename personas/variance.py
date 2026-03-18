"""
Adds human-like variance to persona workouts.
Good days, bad days, rest days, and random rep variation.
"""

import random
from datetime import date


# Mood weights: most days are good, occasionally great or struggling
MOOD_WEIGHTS = {
    "great": 0.10,
    "good": 0.60,
    "ok": 0.15,
    "tired": 0.10,
    "struggling": 0.05,
}

MOOD_MULTIPLIERS = {
    "great": 1.15,
    "good": 1.00,
    "ok": 0.90,
    "tired": 0.80,
    "struggling": 0.65,
}


def assign_daily_mood() -> str:
    """Weighted random mood for the day."""
    moods = list(MOOD_WEIGHTS.keys())
    weights = list(MOOD_WEIGHTS.values())
    return random.choices(moods, weights=weights, k=1)[0]


def is_rest_day(off_day_frequency: int) -> bool:
    """Determine if today is a rest day for this persona."""
    return random.randint(1, off_day_frequency) == 1


def calculate_reps(
    base_reps: int,
    mood: str,
    variance_factor: float,
    is_off_day: bool = False,
    off_day_penalty: float = 0.30,
) -> int:
    """
    Calculate actual reps for a workout post.

    base_reps: calibrated baseline for this persona + user combo
    mood: today's mood
    variance_factor: persona-specific variance (e.g., 0.15 = ±15%)
    is_off_day: if True, apply off_day_penalty
    off_day_penalty: percentage reduction on off days
    """
    mood_mult = MOOD_MULTIPLIERS.get(mood, 1.0)
    random_variance = random.uniform(1 - variance_factor, 1 + variance_factor)

    reps = base_reps * mood_mult * random_variance

    if is_off_day:
        reps *= (1 - off_day_penalty)

    return max(1, round(reps))


def generate_workout_numbers(
    adjusted_baseline: dict,
    mood: str,
    variance_factor: float,
    is_off_day: bool = False,
    off_day_penalty: float = 0.30,
) -> dict:
    """
    Generate a full workout (squats, pushups, situps) with variance.
    Returns dict like {"squats": 32, "pushups": 14, "situps": 28}
    """
    return {
        exercise: calculate_reps(
            base_reps, mood, variance_factor, is_off_day, off_day_penalty
        )
        for exercise, base_reps in adjusted_baseline.items()
    }


def random_sets(mood: str) -> int:
    """Generate number of sets based on mood."""
    if mood in ("great", "good"):
        return random.choice([2, 3, 3, 3, 4])
    elif mood == "ok":
        return random.choice([2, 2, 3])
    else:
        return random.choice([1, 2, 2])
