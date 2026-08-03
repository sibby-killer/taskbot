"""
Server blueprint (Section 3). Country channels aren't pre-listed here since
they're created on demand the first time someone from a new country
verifies (see cogs/onboarding.py get_or_create_country_channel) — you don't
know every country in advance.
"""

ROLES = [
    {"key": "ADMIN", "name": "Admin", "color": 0xE74C3C, "hoist": True, "permissions": "administrator"},
    {"key": "MODERATOR", "name": "Moderator", "color": 0x3498DB, "hoist": True, "permissions": "moderator"},
    {"key": "TASKER", "name": "Tasker", "color": 0x95A5A6, "hoist": False, "permissions": None},
    {"key": "TIER_1", "name": "Tier 1", "color": 0xB0B0B0, "hoist": True, "permissions": None},
    {"key": "TIER_2", "name": "Tier 2", "color": 0x2ECC71, "hoist": True, "permissions": None},
    {"key": "TIER_3", "name": "Tier 3", "color": 0xF1C40F, "hoist": True, "permissions": None},
]

# Static categories/channels built once by setup.py. Per-country chat
# channels are created dynamically at onboarding time, not listed here.
CATEGORIES = [
    {
        "name": "👋 WELCOME",
        "channels": [
            {"name": "announcements", "topic": "Official updates.", "view": ["@everyone"], "send": ["ADMIN"]},
            {"name": "guide-rules", "topic": "How tasks work and what you earn.", "view": ["@everyone"], "send": ["ADMIN"]},
            {"name": "start-here", "topic": "Welcome! Run /verify with Redwire to link your Reddit account, then use /profile to see your stats.", "view": ["@everyone"], "send": ["@everyone"]},
        ],
    },
    {
        "name": "💬 COMMUNITY",
        "channels": [
            {"name": "english-chat", "topic": "General chat, English only.", "view": ["TASKER"], "send": ["TASKER"]},
        ],
    },
    {
        "name": "🔒 STAFF ONLY",
        "admin_only": True,
        "channels": [
            {"name": "admin-dashboard", "topic": "Bot commands live here.", "view": ["ADMIN"], "send": ["ADMIN"]},
            {"name": "onboarding-log", "topic": "Every verification result.", "view": ["ADMIN"], "send": ["ADMIN"]},
            {"name": "withdrawals-log", "topic": "Withdrawal requests + payment proof.", "view": ["ADMIN"], "send": ["ADMIN"]},
            {"name": "announcement-queue", "topic": "Provider bot posts awaiting approval.", "view": ["ADMIN"], "send": ["ADMIN"]},
            {"name": "mod-log", "topic": "Auto-blocked messages, warnings.", "view": ["ADMIN"], "send": ["ADMIN"]},
        ],
    },
    {
        "name": "🎫 TICKETS",
        "admin_only": True,
        "channels": [],  # created per-ticket by /ticket
    },
]
