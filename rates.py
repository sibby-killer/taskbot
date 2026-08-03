"""
Section 8 (Rates) + Section 6 (Limits) — single source of truth for every
number that matters, so nothing is hardcoded twice.

RATES_CENTS[task_type][tier] = (company_pays_you_cents, you_pay_tasker_cents)
The first number is admin-only, never shown anywhere a tasker can see it.
The second number ("Your earnings") is what /profile and the guide show.
"""

RATES_CENTS = {
    "post": {
        1: {"company": 300, "tasker": 150},
        2: {"company": 750, "tasker": 350},
        3: {"company": 1875, "tasker": 700},
    },
    "comment": {
        1: {"company": 100, "tasker": 50},
        2: {"company": 250, "tasker": 150},
        3: {"company": 625, "tasker": 300},
    },
}

# Flat rate lookups for /profile display (tasker rates only, in cents)
POST_RATE_CENTS = {1: 150, 2: 350, 3: 700}
COMMENT_RATE_CENTS = {1: 50, 2: 150, 3: 300}

LIMITS = {
    "post": {"minutes_to_complete": 90, "cooldown_minutes": 150, "daily_max": 3},
    "comment": {"minutes_to_complete": 120, "cooldown_minutes": 30, "daily_max": 10},
}

MIN_WITHDRAWAL_CENTS = 1200  # $12

PAYMENT_METHODS = ["Binance UID", "USDT", "USDC"]

VERIFICATION_FEE_RANGE = (1, 21)  # percent, 0-7 day window — exact formula pending from provider


def tasker_rate_cents(task_type: str, tier: int) -> int:
    return RATES_CENTS[task_type][tier]["tasker"]


def company_rate_cents(task_type: str, tier: int) -> int:
    return RATES_CENTS[task_type][tier]["company"]


def margin_cents(task_type: str, tier: int) -> int:
    return company_rate_cents(task_type, tier) - tasker_rate_cents(task_type, tier)
