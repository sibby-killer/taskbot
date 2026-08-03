"""
Profile — shows YOUR rates (from rates.py), not Redwire's.
Payment/withdrawal handled by Redwire. Referrals handled by Invite Tracker.
"""

import discord
from discord import app_commands
from discord.ext import commands

import db
from rates import POST_RATE_CENTS, COMMENT_RATE_CENTS
from limits import check_can_request


class Payments(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="See your tier, balance, cooldowns, and rates.")
    async def profile(self, interaction: discord.Interaction):
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You haven't verified yet. Use Redwire's `/verify` command first to link your Reddit account.", ephemeral=True)
            return

        post_cd = await db.get_cooldown_state(user.discord_id, "post")
        comment_cd = await db.get_cooldown_state(user.discord_id, "comment")
        post_check = check_can_request("post", post_cd.cooldown_ends_at, post_cd.tasks_completed_today)
        comment_check = check_can_request("comment", comment_cd.cooldown_ends_at, comment_cd.tasks_completed_today)

        embed = discord.Embed(title=f"Profile — u/{user.reddit_username}", color=discord.Color.blurple())
        embed.add_field(name="Tier", value=f"Tier {user.tier}", inline=True)
        embed.add_field(name="Karma", value=str(user.total_karma), inline=True)
        embed.add_field(name="Account Age", value=f"{user.account_age_days}d", inline=True)
        embed.add_field(name="Verification", value=user.verification_status, inline=True)
        embed.add_field(name="Balance", value=f"${user.balance_cents / 100:.2f}", inline=True)

        post_rate = POST_RATE_CENTS.get(user.tier, POST_RATE_CENTS[1])
        comment_rate = COMMENT_RATE_CENTS.get(user.tier, COMMENT_RATE_CENTS[1])
        embed.add_field(
            name="Your Rates",
            value=f"Post: ${post_rate/100:.2f} | Comment: ${comment_rate/100:.2f}",
            inline=True,
        )

        embed.add_field(
            name="Post status",
            value="Available now" if post_check.allowed else post_check.reason,
            inline=False,
        )
        embed.add_field(
            name="Comment status",
            value="Available now" if comment_check.allowed else comment_check.reason,
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Payments(bot))
