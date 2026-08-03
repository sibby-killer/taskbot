"""
Main entry point. Run with: python bot.py

Runs two things concurrently:
1. The Discord bot itself (persistent WebSocket connection).
2. A minimal HTTP server on $PORT, purely so Render has something to health-
   check and UptimeRobot has something to ping — this is what keeps a free
   Render Web Service from spinning down from inactivity. It does nothing
   else; the actual bot logic never touches HTTP.
"""

import os
import asyncio
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web

import db
from cogs.onboarding import RefreshTierButton

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("taskbridge")

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
PORT = int(os.environ.get("PORT", 8080))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # needed for the moderation keyword filter

bot = commands.Bot(command_prefix="!", intents=intents)

EXTENSIONS = [
    "cogs.onboarding",
    "cogs.tasks",
    "cogs.payments",
    "cogs.moderation",
    "cogs.admin",
]


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (id: {bot.user.id})")

    await db.init_db()
    log.info("Database ready.")

    # Persistent views survive bot restarts as long as they're re-registered
    # here with the same custom_ids used when they were first sent.
    bot.add_view(RefreshTierButton())

    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    log.info(f"Synced {len(synced)} slash commands to guild {GUILD_ID}.")


async def load_extensions():
    for ext in EXTENSIONS:
        await bot.load_extension(ext)
        log.info(f"Loaded extension: {ext}")


# --- Minimal health-check server (Render + UptimeRobot) -----------------------

async def health(request):
    return web.Response(text="OK")


async def run_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Health check server listening on port {PORT}")


async def main():
    await load_extensions()
    await run_health_server()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
