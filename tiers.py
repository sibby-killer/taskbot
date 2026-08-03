"""
Tier calculation — Section 7 of the plan.

Tier | Karma (post+comment) | Account age | Extra rule
1 Starter | 100   | —          | min 100 comment karma
2 Pro     | 1,500 | >= 2 months | min 100 comment karma
3 Elite   | 5,000 | >= 5 months | min 100 comment karma

Rule confirmed by the operator: if the karma threshold is met but the
account isn't old enough yet, the account stays Tier 1 until it ages in —
it does NOT get bumped to an in-between tier.
"""

from dataclasses import dataclass

MIN_COMMENT_KARMA = 100

TIER_REQUIREMENTS = {
    3: {"karma": 5000, "age_days": 150},  # ~5 months
    2: {"karma": 1500, "age_days": 60},  # ~2 months
    1: {"karma": 100, "age_days": 0},
}


@dataclass
class TierResult:
    tier: int
    reason: str


def calculate_tier(total_karma: int, comment_karma: int, account_age_days: int) -> TierResult:
    """Returns the tier an account currently qualifies for, and why."""
    if comment_karma < MIN_COMMENT_KARMA:
        return TierResult(1, f"Comment karma ({comment_karma}) is below the {MIN_COMMENT_KARMA} minimum required at every tier.")

    # Check highest tiers first so a karma-qualified-but-too-young account gets
    # the accurate "aging in" explanation instead of silently matching Tier 1.
    for tier in (3, 2):
        req = TIER_REQUIREMENTS[tier]
        if total_karma >= req["karma"] and account_age_days < req["age_days"]:
            days_left = req["age_days"] - account_age_days
            return TierResult(
                1,
                f"Karma qualifies for Tier {tier}, but account needs {days_left} more day(s) to age in. Staying Tier 1 until then.",
            )

    for tier in (3, 2, 1):
        req = TIER_REQUIREMENTS[tier]
        if total_karma >= req["karma"] and account_age_days >= req["age_days"]:
            return TierResult(tier, f"Meets Tier {tier}: karma {total_karma} >= {req['karma']}, age {account_age_days}d >= {req['age_days']}d.")

    return TierResult(1, "Default Tier 1.")
