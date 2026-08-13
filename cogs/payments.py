"""
Profile — shows YOUR rates (from rates.py), not Redwire's.
Payment/withdrawal handled by Referrals handled by Invite Tracker.
"""

import discord
from discord import app_commands
from discord.ext import commands

import db
from rates import POST_RATE_CENTS, COMMENT_RATE_CENTS, MIN_WITHDRAWAL_CENTS, PAYMENT_METHODS
from limits import check_can_request


class Payments(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="See your tier, balance, cooldowns, and rates.")
    async def profile(self, interaction: discord.Interaction):
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You haven't verified yet. Use `/verify` in <#1537510572491415592> to link your Reddit account.", ephemeral=True)
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

    @app_commands.command(name="withdraw", description="Request a withdrawal of your earnings.")
    @app_commands.describe(amount="Amount to withdraw (in dollars)")
    async def withdraw(self, interaction: discord.Interaction, amount: float):
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You haven't verified yet.", ephemeral=True)
            return

        amount_cents = int(amount * 100)

        if amount_cents < MIN_WITHDRAWAL_CENTS:
            await interaction.response.send_message(
                f"Minimum withdrawal is **${MIN_WITHDRAWAL_CENTS/100:.2f}**. You requested **${amount:.2f}**.",
                ephemeral=True
            )
            return

        if amount_cents > user.balance_cents:
            await interaction.response.send_message(
                f"Insufficient balance. You have **${user.balance_cents/100:.2f}**.",
                ephemeral=True
            )
            return

        modal = WithdrawModal(amount_cents, user.balance_cents)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="withdraw-status", description="Check your withdrawal history and status.")
    async def withdraw_status(self, interaction: discord.Interaction):
        user = await db.get_user(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You haven't verified yet.", ephemeral=True)
            return

        withdrawals = await db.get_user_withdrawals(str(interaction.user.id))

        embed = discord.Embed(title=f"Withdrawal Status — u/{user.reddit_username}", color=discord.Color.green())
        embed.add_field(name="Current Balance", value=f"${user.balance_cents / 100:.2f}", inline=True)
        embed.add_field(name="Minimum Withdrawal", value=f"${MIN_WITHDRAWAL_CENTS/100:.2f}", inline=True)

        if user.balance_cents < MIN_WITHDRAWAL_CENTS:
            needed = MIN_WITHDRAWAL_CENTS - user.balance_cents
            embed.add_field(
                name="Status",
                value=f"You need **${needed / 100:.2f}** more to request a withdrawal.",
                inline=False,
            )
        else:
            embed.add_field(
                name="Status",
                value="You can request a withdrawal! Use `/withdraw`.",
                inline=False,
            )

        if withdrawals:
            lines = []
            for w in withdrawals[:5]:
                status_emoji = "⏳" if w["status"] == "pending" else "✅"
                lines.append(f"{status_emoji} **${w['amount_cents'] / 100:.2f}** — {w['requested_at'][:10]}")
            embed.add_field(
                name="Recent Withdrawals",
                value="\n".join(lines),
                inline=False,
            )
        else:
            embed.add_field(name="Recent Withdrawals", value="No withdrawals yet.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class WithdrawModal(discord.ui.Modal, title='Withdrawal Request'):
    payment_method = discord.ui.TextInput(label='Payment method (Binance UID, USDT, USDC)', required=True)
    payment_details = discord.ui.TextInput(label='Payment details (UID, address, etc.)', required=True)

    def __init__(self, amount_cents: int, balance_cents: int):
        super().__init__()
        self.amount_cents = amount_cents
        self.balance_cents = balance_cents

    async def on_submit(self, interaction: discord.Interaction):
        if self.payment_method.value not in PAYMENT_METHODS:
            await interaction.response.send_message(
                f"Invalid payment method. Use: {', '.join(PAYMENT_METHODS)}",
                ephemeral=True
            )
            return

        withdrawal_id = await db.create_withdrawal(
            str(interaction.user.id),
            self.amount_cents,
            self.payment_method.value,
            self.payment_details.value
        )

        new_balance = self.balance_cents - self.amount_cents

        embed = discord.Embed(
            title='💸 Withdrawal Requested',
            description=f'**${self.amount_cents/100:.2f}** withdrawal requested by {interaction.user.mention}',
            color=0xFFA500
        )
        embed.add_field(name='Payment Method', value=self.payment_method.value, inline=True)
        embed.add_field(name='Payment Details', value=self.payment_details.value[:50], inline=True)
        embed.add_field(name='New Balance', value=f'${new_balance/100:.2f}', inline=True)
        embed.set_footer(text='Waiting for admin approval')

        await interaction.response.send_message(embed=embed)

        # Notify admin
        try:
            admin = await interaction.client.fetch_user(829433351731240991)
            await admin.send(
                f'💸 **Withdrawal Request**\n\n'
                f'**User:** {interaction.user.mention}\n'
                f'**Amount:** ${self.amount_cents/100:.2f}\n'
                f'**Method:** {self.payment_method.value}\n'
                f'**Details:** {self.payment_details.value}\n\n'
                f'Use `/mark-paid` to approve.'
            )
        except:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Payments(bot))
