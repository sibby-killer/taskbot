"""
Reddit verification for onboarding (Section 2, step 4).

Deliberately uses Reddit's public `/user/<name>/about.json` endpoint instead
of the full OAuth API. This is read-only public profile data (karma, account
age, suspended status) — no Reddit "app" registration, client ID, or secret
needed. One less credential to set up.

Tradeoff: this endpoint is more aggressively rate-limited than the
authenticated API and requires a descriptive User-Agent or Reddit will 429
you. Fine for onboarding volume (a few requests per new member); if this
ever needs to scale to hundreds of verifications a minute, switch to
asyncpraw with a registered app instead — the call sites in cogs/onboarding.py
would only need this module's `verify_reddit_account` return shape to stay
the same.
"""

import time
import aiohttp
from dataclasses import dataclass
from typing import Optional

USER_AGENT = "TaskBridgeBot/1.0 (by /u/your-reddit-username-here)"


@dataclass
class RedditProfile:
    exists: bool
    username: str = ""
    total_karma: int = 0
    comment_karma: int = 0
    link_karma: int = 0
    account_age_days: int = 0
    is_suspended: bool = False
    error: Optional[str] = None


def _parse_profile(username: str, payload: dict) -> RedditProfile:
    """Pure function: turns Reddit's raw JSON payload into a RedditProfile. Split
    out from the network call so it's testable without hitting Reddit."""
    data = payload.get("data")
    if not data:
        return RedditProfile(exists=False, username=username, error="Unexpected response from Reddit.")

    if data.get("is_suspended"):
        return RedditProfile(exists=True, username=username, is_suspended=True, error="This account is suspended.")

    created_utc = data.get("created_utc", time.time())
    account_age_days = int((time.time() - created_utc) / 86400)

    return RedditProfile(
        exists=True,
        username=data.get("name", username),
        total_karma=int(data.get("total_karma", 0)),
        comment_karma=int(data.get("comment_karma", 0)),
        link_karma=int(data.get("link_karma", 0)),
        account_age_days=account_age_days,
        is_suspended=False,
    )


async def verify_reddit_account(username: str) -> RedditProfile:
    username = username.strip().lstrip("u/").lstrip("/u/")
    url = f"https://www.reddit.com/user/{username}/about.json"

    try:
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    return RedditProfile(exists=False, username=username, error="Account not found.")
                if resp.status == 429:
                    return RedditProfile(exists=False, username=username, error="Reddit is rate-limiting us — try again in a minute.")
                if resp.status != 200:
                    return RedditProfile(exists=False, username=username, error=f"Reddit returned an unexpected status ({resp.status}).")

                payload = await resp.json()
    except Exception as e:  # noqa: BLE001 — surfaced to the user as a generic retry message
        return RedditProfile(exists=False, username=username, error=f"Couldn't reach Reddit: {e}")

    return _parse_profile(username, payload)
