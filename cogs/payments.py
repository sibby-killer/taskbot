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

    @app_commands.command(name="withdraw-status", description="Check your withdrawal history and status.")
    async def withdraw_status(self, interaction: discord.Interaction):
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You haven't verified yet.", ephemeral=True)
            return

        withdrawals = await db.get_user_withdrawals(str(interaction.user.id))

        embed = discord.Embed(title=f"Withdrawal Status — u/{user.reddit_username}", color=discord.Color.green())
        embed.add_field(name="Current Balance", value=f"${user.balance_cents / 100:.2f}", inline=True)
        embed.add_field(name="Minimum Withdrawal", value="$12.00", inline=True)

        if user.balance_cents < 1200:
            needed = 1200 - user.balance_cents
            embed.add_field(
                name="Status",
                value=f"You need **${needed / 100:.2f}** more to request a withdrawal.",
                inline=False,
            )
        else:
            embed.add_field(
                name="Status",
                value="You can request a withdrawal! Use `/withdraw` when available.",
                inline=False,
            )

        if withdrawals:
            lines = []
            for w in withdrawals[:5]:
                status_emoji = "Pending" if w["status"] == "pending" else "Paid"
                lines.append(f"**${w['amount_cents'] / 100:.2f}** — {status_emoji} — {w['requested_at'][:10]}")
            embed.add_field(
                name="Recent Withdrawals",
                value="\n".join(lines),
                inline=False,
            )
        else:
            embed.add_field(name="Recent Withdrawals", value="No withdrawals yet.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Payments(bot))
