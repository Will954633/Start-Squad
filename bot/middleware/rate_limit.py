"""Simple in-memory rate limiter for workout commands."""

import time
from collections import defaultdict

# Max workout logs per user per day
MAX_WORKOUTS_PER_DAY = 20

# {user_id: [(timestamp, ...),]}
_user_logs: dict[int, list[float]] = defaultdict(list)


def check_rate_limit(user_id: int) -> bool:
    """Return True if user is within rate limits."""
    now = time.time()
    day_ago = now - 86400

    # Clean old entries
    _user_logs[user_id] = [t for t in _user_logs[user_id] if t > day_ago]

    if len(_user_logs[user_id]) >= MAX_WORKOUTS_PER_DAY:
        return False

    _user_logs[user_id].append(now)
    return True
