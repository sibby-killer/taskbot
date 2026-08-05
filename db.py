"""
Database layer. Talks to Turso in production (TURSO_DATABASE_URL +
TURSO_AUTH_TOKEN in .env); falls back to a local file (./local.db) if those
aren't set, so the bot runs for local testing without a Turso account.
"""

import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
import libsql_client

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    discord_id TEXT PRIMARY KEY,
    reddit_username TEXT,
    country TEXT,
    full_name TEXT,
    whatsapp_contact TEXT,
    tier INTEGER DEFAULT 1,
    total_karma INTEGER DEFAULT 0,
    comment_karma INTEGER DEFAULT 0,
    account_age_days INTEGER DEFAULT 0,
    verification_status TEXT DEFAULT 'unverified',
    payment_method TEXT,
    payment_details TEXT,
    balance_cents INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cooldowns (
    discord_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    cooldown_ends_at TEXT,
    tasks_completed_today INTEGER DEFAULT 0,
    day_reset_date TEXT,
    PRIMARY KEY (discord_id, task_type)
);

CREATE TABLE IF NOT EXISTS task_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    title TEXT,
    body TEXT,
    destination_url TEXT,
    min_tier INTEGER DEFAULT 1,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    discord_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    tier_at_request INTEGER,
    claimed_at TEXT DEFAULT (datetime('now')),
    deadline_at TEXT NOT NULL,
    status TEXT DEFAULT 'claimed',
    submitted_link TEXT,
    submitted_at TEXT
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    payment_method TEXT,
    payment_details TEXT,
    status TEXT DEFAULT 'pending',
    requested_at TEXT DEFAULT (datetime('now')),
    paid_at TEXT,
    proof_url TEXT
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_discord_id TEXT NOT NULL,
    referred_discord_id TEXT NOT NULL UNIQUE,
    qualified INTEGER DEFAULT 0,
    rewarded INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    qualified_at TEXT
);
"""

_client: Optional[libsql_client.Client] = None


def get_client() -> libsql_client.Client:
    global _client
    if _client is None:
        url = os.environ.get("TURSO_DATABASE_URL", "file:local.db")
        token = os.environ.get("TURSO_AUTH_TOKEN")
        _client = libsql_client.create_client(url, auth_token=token)
    return _client


async def init_db():
    client = get_client()
    for statement in SCHEMA.strip().split(";\n\n"):
        statement = statement.strip()
        if statement:
            await client.execute(statement)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --- Users -------------------------------------------------------------------

@dataclass
class User:
    discord_id: str
    reddit_username: Optional[str]
    country: Optional[str]
    full_name: Optional[str]
    whatsapp_contact: Optional[str]
    tier: int
    total_karma: int
    comment_karma: int
    account_age_days: int
    verification_status: str
    payment_method: Optional[str]
    payment_details: Optional[str]
    balance_cents: int


def _row_to_user(row) -> User:
    d = row.asdict()
    return User(
        discord_id=d["discord_id"],
        reddit_username=d["reddit_username"],
        country=d["country"],
        full_name=d["full_name"],
        whatsapp_contact=d["whatsapp_contact"],
        tier=d["tier"],
        total_karma=d["total_karma"],
        comment_karma=d["comment_karma"],
        account_age_days=d["account_age_days"],
        verification_status=d["verification_status"],
        payment_method=d["payment_method"],
        payment_details=d["payment_details"],
        balance_cents=d["balance_cents"],
    )


async def get_user(discord_id: str) -> Optional[User]:
    client = get_client()
    rs = await client.execute("SELECT * FROM users WHERE discord_id = ?", [discord_id])
    if not rs.rows:
        return None
    return _row_to_user(rs.rows[0])


async def upsert_verified_user(
    discord_id: str,
    reddit_username: str,
    country: str,
    full_name: str,
    whatsapp_contact: str,
    tier: int,
    total_karma: int,
    comment_karma: int,
    account_age_days: int,
):
    client = get_client()
    await client.execute(
        """
        INSERT INTO users (discord_id, reddit_username, country, full_name, whatsapp_contact, tier, total_karma, comment_karma, account_age_days, verification_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified', datetime('now'))
        ON CONFLICT(discord_id) DO UPDATE SET
            reddit_username = excluded.reddit_username,
            country = excluded.country,
            full_name = excluded.full_name,
            whatsapp_contact = excluded.whatsapp_contact,
            tier = excluded.tier,
            total_karma = excluded.total_karma,
            comment_karma = excluded.comment_karma,
            account_age_days = excluded.account_age_days,
            verification_status = 'verified',
            updated_at = datetime('now')
        """,
        [discord_id, reddit_username, country, full_name, whatsapp_contact, tier, total_karma, comment_karma, account_age_days],
    )


async def list_users_by_country(country: str):
    client = get_client()
    rs = await client.execute("SELECT * FROM users WHERE country LIKE ? ORDER BY created_at DESC", [f"%{country}%"])
    return [_row_to_user(row) for row in rs.rows]


async def set_verification_status(discord_id: str, status: str):
    client = get_client()
    await client.execute(
        "UPDATE users SET verification_status = ?, updated_at = datetime('now') WHERE discord_id = ?", [status, discord_id]
    )


async def add_balance(discord_id: str, amount_cents: int):
    client = get_client()
    await client.execute(
        "UPDATE users SET balance_cents = balance_cents + ?, updated_at = datetime('now') WHERE discord_id = ?",
        [amount_cents, discord_id],
    )


async def deduct_balance(discord_id: str, amount_cents: int):
    client = get_client()
    await client.execute(
        "UPDATE users SET balance_cents = balance_cents - ?, updated_at = datetime('now') WHERE discord_id = ?",
        [amount_cents, discord_id],
    )


# --- Cooldowns / daily limits --------------------------------------------------

@dataclass
class CooldownState:
    cooldown_ends_at: Optional[datetime]
    tasks_completed_today: int


async def get_cooldown_state(discord_id: str, task_type: str) -> CooldownState:
    client = get_client()
    rs = await client.execute(
        "SELECT * FROM cooldowns WHERE discord_id = ? AND task_type = ?", [discord_id, task_type]
    )
    if not rs.rows:
        return CooldownState(cooldown_ends_at=None, tasks_completed_today=0)

    d = rs.rows[0].asdict()
    completed_today = d["tasks_completed_today"] if d["day_reset_date"] == _today() else 0
    ends_at = datetime.fromisoformat(d["cooldown_ends_at"]) if d["cooldown_ends_at"] else None
    return CooldownState(cooldown_ends_at=ends_at, tasks_completed_today=completed_today)


async def record_task_completion(discord_id: str, task_type: str, cooldown_ends_at: datetime):
    client = get_client()
    existing = await get_cooldown_state(discord_id, task_type)
    new_count = existing.tasks_completed_today + 1
    await client.execute(
        """
        INSERT INTO cooldowns (discord_id, task_type, cooldown_ends_at, tasks_completed_today, day_reset_date)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(discord_id, task_type) DO UPDATE SET
            cooldown_ends_at = excluded.cooldown_ends_at,
            tasks_completed_today = excluded.tasks_completed_today,
            day_reset_date = excluded.day_reset_date
        """,
        [discord_id, task_type, cooldown_ends_at.isoformat(), new_count, _today()],
    )


# --- Task pool (fallback if Redwire's bot doesn't cover this) -----------------

async def add_pool_task(task_type: str, title: str, body: str, destination_url: str, min_tier: int = 1) -> int:
    client = get_client()
    rs = await client.execute(
        "INSERT INTO task_pool (task_type, title, body, destination_url, min_tier) VALUES (?, ?, ?, ?, ?)",
        [task_type, title, body, destination_url, min_tier],
    )
    return rs.last_insert_rowid


# --- Referrals -----------------------------------------------------------------

REFERRAL_REWARD_CENTS = 100  # $1 per qualified referral


@dataclass
class Referral:
    id: int
    referrer_discord_id: str
    referred_discord_id: str
    qualified: bool
    rewarded: bool
    created_at: str
    qualified_at: Optional[str]


async def create_referral(referrer_discord_id: str, referred_discord_id: str) -> bool:
    if referrer_discord_id == referred_discord_id:
        return False
    client = get_client()
    try:
        await client.execute(
            "INSERT INTO referrals (referrer_discord_id, referred_discord_id) VALUES (?, ?)",
            [referrer_discord_id, referred_discord_id],
        )
        return True
    except Exception:
        return False


async def get_referral_by_referred(referred_discord_id: str) -> Optional[Referral]:
    client = get_client()
    rs = await client.execute("SELECT * FROM referrals WHERE referred_discord_id = ?", [referred_discord_id])
    if not rs.rows:
        return None
    d = rs.rows[0].asdict()
    return Referral(
        id=d["id"],
        referrer_discord_id=d["referrer_discord_id"],
        referred_discord_id=d["referred_discord_id"],
        qualified=bool(d["qualified"]),
        rewarded=bool(d["rewarded"]),
        created_at=d["created_at"],
        qualified_at=d.get("qualified_at"),
    )


async def qualify_referral(referred_discord_id: str) -> Optional[Referral]:
    """Mark a referral as qualified (1 post + 1 comment done). Returns the referral if newly qualified."""
    client = get_client()
    rs = await client.execute("SELECT * FROM referrals WHERE referred_discord_id = ? AND qualified = 0", [referred_discord_id])
    if not rs.rows:
        return None
    d = rs.rows[0].asdict()
    await client.execute(
        "UPDATE referrals SET qualified = 1, qualified_at = datetime('now') WHERE id = ?",
        [d["id"]],
    )
    return Referral(
        id=d["id"],
        referrer_discord_id=d["referrer_discord_id"],
        referred_discord_id=d["referred_discord_id"],
        qualified=True,
        rewarded=False,
        created_at=d["created_at"],
        qualified_at=datetime.now(timezone.utc).isoformat(),
    )


async def reward_referral(referred_discord_id: str) -> bool:
    """Credit $1 to referrer's balance. Returns True if rewarded."""
    client = get_client()
    referral = await get_referral_by_referred(referred_discord_id)
    if not referral or referral.qualified or referral.rewarded:
        return False
    await add_balance(referral.referrer_discord_id, REFERRAL_REWARD_CENTS)
    await client.execute("UPDATE referrals SET rewarded = 1 WHERE id = ?", [referral.id])
    return True


async def get_pending_withdrawals():
    client = get_client()
    rs = await client.execute("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY requested_at")
    return [row.asdict() for row in rs.rows]


async def create_withdrawal(discord_id: str, amount_cents: int, payment_method: str, payment_details: str) -> int:
    client = get_client()
    rs = await client.execute(
        "INSERT INTO withdrawals (discord_id, amount_cents, payment_method, payment_details) VALUES (?, ?, ?, ?)",
        [discord_id, amount_cents, payment_method, payment_details],
    )
    await deduct_balance(discord_id, amount_cents)
    return rs.last_insert_rowid


async def get_user_withdrawals(discord_id: str):
    client = get_client()
    rs = await client.execute("SELECT * FROM withdrawals WHERE discord_id = ? ORDER BY requested_at DESC", [discord_id])
    return [row.asdict() for row in rs.rows]


async def mark_withdrawal_paid(withdrawal_id: int, proof_url: str):
    client = get_client()
    await client.execute(
        "UPDATE withdrawals SET status = 'paid', paid_at = datetime('now'), proof_url = ? WHERE id = ?",
        [proof_url, withdrawal_id],
    )
