"""
Adjusts persona fitness baselines to match the human user's fitness level.
The human should always feel like they're in the middle of the pack.
"""


# Scale factors per persona per fitness level
# Each persona gets a multiplier applied to their base reps
CALIBRATION_SCALES = {
    "beginner": {
        "mia": 0.80,    # Slightly above beginner
        "damo": 0.65,   # Scaled down significantly (normally strongest)
        "priya": 0.75,  # Moderate
        "jake": 1.00,   # Stays at base (already lowest)
        "lena": 0.75,   # Moderate
    },
    "intermediate": {
        "mia": 1.00,
        "damo": 1.00,
        "priya": 1.00,
        "jake": 1.00,
        "lena": 1.00,
    },
    "advanced": {
        "mia": 1.30,
        "damo": 1.60,   # Scales up the most
        "priya": 1.40,
        "jake": 1.20,   # Stays relatively lower
        "lena": 1.35,
    },
}


def calculate_adjusted_baseline(
    persona_slug: str,
    base_fitness: dict,
    user_fitness_level: str,
) -> dict:
    """
    Calculate adjusted baseline reps for a persona based on user's fitness level.

    Returns dict like {"squats": 28, "pushups": 12, "situps": 24}
    """
    scale = CALIBRATION_SCALES.get(user_fitness_level, CALIBRATION_SCALES["intermediate"])
    factor = scale.get(persona_slug, 1.0)

    return {
        exercise: round(reps * factor)
        for exercise, reps in base_fitness.items()
    }
