"""Admin dashboard — taskers-by-country, stats, verification override, add-task."""

import discord
from discord import app_commands
from discord.ext import commands

import db


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="taskers-by-country", description="[Admin] Look up taskers by location.")
    @app_commands.describe(country="Country name (partial match ok, e.g. 'Kenya')")
    @app_commands.checks.has_role("Admin")
    async def taskers_by_country(self, interaction: discord.Interaction, country: str):
        users = await db.list_users_by_country(country)
        if not users:
            await interaction.response.send_message(f"No taskers found for '{country}'.", ephemeral=True)
            return
        lines = [
            f"**{u.full_name}** (<@{u.discord_id}>) — u/{u.reddit_username} | Tier {u.tier} | "
            f"{u.whatsapp_contact} | {u.verification_status} | ${u.balance_cents/100:.2f}"
            for u in users[:25]
        ]
        header = f"**{len(users)} tasker(s) matching '{country}'{' (showing first 25)' if len(users) > 25 else ''}:**\n"
        await interaction.response.send_message(header + "\n".join(lines), ephemeral=True)

    @app_commands.command(name="set-verification-status", description="[Admin] Manually flag/verify/unverify an account.")
    @app_commands.choices(
        status=[
            app_commands.Choice(name="verified", value="verified"),
            app_commands.Choice(name="unverified", value="unverified"),
            app_commands.Choice(name="flagged", value="flagged"),
        ]
    )
    @app_commands.checks.has_role("Admin")
    async def set_verification_status(self, interaction: discord.Interaction, user: discord.User, status: app_commands.Choice[str]):
        await db.set_verification_status(str(user.id), status.value)
        await interaction.response.send_message(f"{user.mention} is now **{status.value}**.", ephemeral=True)

    @app_commands.command(name="stats", description="[Admin] Quick platform overview.")
    @app_commands.checks.has_role("Admin")
    async def stats(self, interaction: discord.Interaction):
        client = db.get_client()
        total_users = (await client.execute("SELECT COUNT(*) as c FROM users")).rows[0].asdict()["c"]
        verified = (await client.execute("SELECT COUNT(*) as c FROM users WHERE verification_status = 'verified'")).rows[0].asdict()["c"]
        open_tasks = (await client.execute("SELECT COUNT(*) as c FROM task_pool WHERE status = 'open'")).rows[0].asdict()["c"]

        await interaction.response.send_message(
            f"**Total signups:** {total_users}\n"
            f"**Verified:** {verified}\n"
            f"**Open tasks in pool:** {open_tasks}\n",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
