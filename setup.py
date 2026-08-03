"""
One-time server builder. Run with: python setup.py
Safe to re-run — skips anything that already exists by name.
"""

import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from config import ROLES, CATEGORIES

load_dotenv()

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ["DISCORD_GUILD_ID"]
BASE = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {TOKEN}"}


async def api(method, path, data=None):
    async with aiohttp.ClientSession() as s:
        async with s.request(method, f"{BASE}{path}", headers=HEADERS, json=data) as r:
            return r.status, await r.json()


async def main():
    status, guild = await api("GET", f"/guilds/{GUILD_ID}?with_counts=true")
    if status != 200:
        print(f"Bot is not in guild {GUILD_ID} — invite it first (see README Part 2).")
        return

    print(f"Connected to guild: {guild['name']}\n")

    # --- 1. Roles ---
    print("Creating roles...")
    status, roles = await api("GET", f"/guilds/{GUILD_ID}/roles")
    existing_roles = {r["name"]: r for r in roles}

    role_ids = {}
    for role_def in ROLES:
        if role_def["name"] in existing_roles:
            print(f"  Role already exists: {role_def['name']}")
            role_ids[role_def["key"]] = existing_roles[role_def["name"]]["id"]
        else:
            perms = 0
            if role_def["permissions"] == "administrator":
                perms = 8
            elif role_def["permissions"] == "moderator":
                perms = 0x200000004 | 0x1000000 | 0x2000000 | 0x4000000
            status, r = await api("POST", f"/guilds/{GUILD_ID}/roles", {
                "name": role_def["name"],
                "color": role_def["color"],
                "hoist": role_def["hoist"],
                "permissions": str(perms),
            })
            role_ids[role_def["key"]] = r["id"]
            print(f"  + Created role: {role_def['name']}")

    # --- 2. Categories & channels ---
    print("\nCreating categories & channels...")
    status, channels = await api("GET", f"/guilds/{GUILD_ID}/channels")
    existing_cats = {c["name"]: c for c in channels if c["type"] == 4}
    existing_chs = {c["name"]: c for c in channels if c["type"] == 0}

    everyone_id = next(r["id"] for r in roles if r["name"] == "@everyone")

    for cat_def in CATEGORIES:
        if cat_def["name"] in existing_cats:
            cat_id = existing_cats[cat_def["name"]]["id"]
            print(f"  Category already exists: {cat_def['name']}")
        else:
            cat_overwrites = []
            if cat_def.get("admin_only"):
                cat_overwrites = [
                    {"id": everyone_id, "type": 0, "allow": "0", "deny": "1024"},
                    {"id": role_ids["ADMIN"], "type": 0, "allow": "1024", "deny": "0"},
                ]
            status, cat = await api("POST", f"/guilds/{GUILD_ID}/channels", {
                "name": cat_def["name"],
                "type": 4,
                "permission_overwrites": cat_overwrites,
            })
            cat_id = cat["id"]
            print(f"  + Created category: {cat_def['name']}")

        for ch_def in cat_def["channels"]:
            if ch_def["name"] in existing_chs:
                print(f"    #{ch_def['name']} already exists")
                continue

            if cat_def.get("admin_only"):
                ch_overwrites = [
                    {"id": everyone_id, "type": 0, "allow": "0", "deny": "1024"},
                    {"id": role_ids["ADMIN"], "type": 0, "allow": "1024", "deny": "0"},
                ]
            else:
                ch_overwrites = [{"id": everyone_id, "type": 0, "allow": "0", "deny": "1024"}]
                for vk in (ch_def.get("view") or []):
                    if vk == "@everyone":
                        continue
                    if vk in role_ids:
                        ch_overwrites.append({"id": role_ids[vk], "type": 0, "allow": "1024", "deny": "0"})
                for sk in (ch_def.get("send") or []):
                    if sk == "@everyone":
                        ch_overwrites.append({"id": everyone_id, "type": 0, "allow": "1024", "deny": "0"})
                        continue
                    if sk in role_ids:
                        ch_overwrites.append({"id": role_ids[sk], "type": 0, "allow": "2048", "deny": "0"})

            status, ch = await api("POST", f"/guilds/{GUILD_ID}/channels", {
                "name": ch_def["name"],
                "type": 0,
                "parent_id": cat_id,
                "topic": ch_def.get("topic", ""),
                "permission_overwrites": ch_overwrites,
            })
            print(f"    + Created #{ch_def['name']}")

    print("\nServer setup complete.")
    print("Next: run `py bot.py`.")


asyncio.run(main())
