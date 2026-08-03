"""
Section 6 — cooldowns and daily limits. Posts and comments run on
INDEPENDENT timers (a tasker can do both in the same day if each type's
cooldown allows it).

This module is deliberately pure — it takes plain data in, returns plain
data out, no DB or Discord calls — so the rules can be tested in isolation.
db.py wires these to actual stored rows.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from rates import LIMITS


@dataclass
class LimitCheck:
    allowed: bool
    reason: str = ""


def _now():
    return datetime.now(timezone.utc)


def check_can_request(
    task_type: str,
    cooldown_ends_at: datetime | None,
    tasks_completed_today: int,
) -> LimitCheck:
    """Given a worker's stored cooldown timestamp and today's completed count
    for this task_type, decides whether they can request another one right now."""
    limits = LIMITS[task_type]

    if cooldown_ends_at is not None and _now() < cooldown_ends_at:
        remaining = cooldown_ends_at - _now()
        minutes = max(1, int(remaining.total_seconds() // 60))
        return LimitCheck(False, f"On cooldown for {minutes} more minute(s).")

    if tasks_completed_today >= limits["daily_max"]:
        return LimitCheck(False, f"Daily limit reached ({limits['daily_max']} {task_type}s/day). Resets at midnight UTC.")

    return LimitCheck(True)


def deadline_for(task_type: str, claimed_at: datetime) -> datetime:
    """When a claimed task's submission window expires."""
    from datetime import timedelta

    return claimed_at + timedelta(minutes=LIMITS[task_type]["minutes_to_complete"])


def cooldown_ends_at(task_type: str, submitted_at: datetime) -> datetime:
    """When the next request for this task_type becomes allowed, counted from submission."""
    from datetime import timedelta

    return submitted_at + timedelta(minutes=LIMITS[task_type]["cooldown_minutes"])
