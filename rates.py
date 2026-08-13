"""
Rates and limits — single source of truth for every number.

RATES_CENTS[task_type][tier] = (company_pays_you_cents, you_pay_tasker_cents)
The first number is admin-only, never shown anywhere a tasker can see it.
The second number ("Your earnings") is what /profile and the guide show.
"""

RATES_CENTS = {
    "post": {
        1: {"company": 200, "tasker": 100},
        2: {"company": 400, "tasker": 200},
        3: {"company": 800, "tasker": 400},
    },
    "comment": {
        1: {"company": 100, "tasker": 50},
        2: {"company": 150, "tasker": 75},
        3: {"company": 300, "tasker": 150},
    },
}

# Flat rate lookups for /profile display (tasker rates only, in cents)
POST_RATE_CENTS = {1: 100, 2: 200, 3: 400}
COMMENT_RATE_CENTS = {1: 50, 2: 75, 3: 150}

LIMITS = {
    "post": {"minutes_to_complete": 90, "cooldown_minutes": 150, "daily_max": 3},
    "comment": {"minutes_to_complete": 120, "cooldown_minutes": 30, "daily_max": 10},
}

MIN_WITHDRAWAL_CENTS = 1200  # $12

PAYMENT_METHODS = ["Binance UID", "USDT", "USDC"]

REFERRAL_REWARD_CENTS = 100  # $1 per referral


def tasker_rate_cents(task_type: str, tier: int) -> int:
    return RATES_CENTS[task_type][tier]["tasker"]


def company_rate_cents(task_type: str, tier: int) -> int:
    return RATES_CENTS[task_type][tier]["company"]


def margin_cents(task_type: str, tier: int) -> int:
    return company_rate_cents(task_type, tier) - tasker_rate_cents(task_type, tier)
