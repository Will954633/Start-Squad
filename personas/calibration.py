"""
Adjusts persona fitness baselines to match the human user's fitness level.
The human should always feel like they're in the middle of the pack.
Separate scales for male and female teams since baselines differ.
"""

CALIBRATION_SCALES = {
    "beginner": {
        # Male team
        "damo": 0.65, "sam": 0.75, "jake": 1.00, "ryan": 0.80, "tom": 0.75,
        # Female team
        "tash": 0.80, "bree": 0.65, "priya": 0.75, "jess": 1.00, "mel": 0.75,
    },
    "intermediate": {
        "damo": 1.00, "sam": 1.00, "jake": 1.00, "ryan": 1.00, "tom": 1.00,
        "tash": 1.00, "bree": 1.00, "priya": 1.00, "jess": 1.00, "mel": 1.00,
    },
    "advanced": {
        "damo": 1.60, "sam": 1.40, "jake": 1.20, "ryan": 1.30, "tom": 1.35,
        "tash": 1.30, "bree": 1.50, "priya": 1.40, "jess": 1.20, "mel": 1.35,
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
