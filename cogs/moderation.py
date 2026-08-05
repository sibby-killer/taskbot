"""
Moderation & auto features.

- Redwire announcement routing to #announcement-queue
- Keyword/link spam filter
- Payment-proof: image-only enforcement for non-admins
- Referral qualification detection (when referred user completes tasks)
- Balance milestone notifications ($12 minimum withdrawal)
"""

import os
import re
import discord
from discord.ext import commands

import db

REDWIRE_BOT_ID = os.environ.get("REDWIRE_BOT_ID")
MIN_WITHDRAWAL_CENTS = 1200  # $12

BANNED_PATTERNS = [
    r"\bdiscord\.gg/\w+",
    r"\bfree\s+nitro\b",
    r"\bcrypto\s+giveaway\b",
    r"\bonlyfans\.com\b",
    r"\bt\.me/\w+",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in BANNED_PATTERNS]


class ApprovalView(discord.ui.View):
    def __init__(self, original_content: str, original_channel_id: int):
        super().__init__(timeout=None)
        self.original_content = original_content
        self.original_channel_id = original_channel_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="announce_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        announcements = discord.utils.get(interaction.guild.text_channels, name="announcements")
        if announcements:
            await announcements.send(self.original_content)
        await interaction.response.edit_message(content=f"Approved and posted by {interaction.user.mention}\n\n{self.original_content}", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, custom_id="announce_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"Declined by {interaction.user.mention}\n\n{self.original_content}", view=None)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        # --- Payment-proof: images only for non-admins ---
        if message.channel.name == "payment-proof" and not message.author.bot:
            admin_role = discord.utils.get(message.guild.roles, name="Admin")
            if admin_role not in message.author.roles:
                if not message.attachments:
                    try:
                        await message.delete()
                        await message.author.send("Payment proof must include an image. Text-only messages aren't allowed in #payment-proof.")
                    except discord.Forbidden:
                        pass
                    return

        # --- Provider bot announcement routing ---
        if REDWIRE_BOT_ID and str(message.author.id) == REDWIRE_BOT_ID:
            # Check for task completion keywords
            content_lower = message.content.lower()
            if any(kw in content_lower for kw in ["completed", "submitted", "approved", "verified"]):
                await self._check_referral_qualification(message)
                await self._check_balance_milestone(message)

            try:
                await message.delete()
            except discord.Forbidden:
                pass
            queue_channel = discord.utils.get(message.guild.text_channels, name="announcement-queue")
            if queue_channel:
                view = ApprovalView(message.content, message.channel.id)
                await queue_channel.send(
                    f"New announcement from Redwire's bot (posted in #{message.channel.name}):\n\n{message.content}",
                    view=view,
                )
            return

        # --- Keyword/link auto-block ---
        if message.author.bot:
            return
        if any(p.search(message.content) for p in _COMPILED):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            mod_log = discord.utils.get(message.guild.text_channels, name="mod-log")
            if mod_log:
                await mod_log.send(f"Auto-blocked message from {message.author.mention} in {message.channel.mention}:\n> {message.content}")
            try:
                await message.author.send("Your message was removed — it matched a blocked pattern. Contact an Admin if this was a mistake.")
            except discord.Forbidden:
                pass

    async def _check_referral_qualification(self, message: discord.Message):
        """Check if a completed task qualifies a referral."""
        referral_logs = discord.utils.get(message.guild.text_channels, name="referral-logs")
        if not referral_logs:
            return

        # Try to find user mentioned or referenced
        for user in message.mentions:
            if user.bot:
                continue
            referral = await db.get_referral_by_referred(str(user.id))
            if referral and not referral.qualified:
                # Check if user has completed at least 1 post and 1 comment
                post_cd = await db.get_cooldown_state(str(user.id), "post")
                comment_cd = await db.get_cooldown_state(str(user.id), "comment")
                if post_cd.tasks_completed_today >= 1 or comment_cd.tasks_completed_today >= 1:
                    # Simplified: qualify after any task completion
                    qualified = await db.qualify_referral(str(user.id))
                    if qualified:
                        referrer = await db.get_user(qualified.referrer_discord_id)
                        if referrer:
                            await referral_logs.send(
                                f"Congratulations <@{qualified.referrer_discord_id}>! "
                                f"You have received **$1.00** for referring <@{qualified.referred_discord_id}>."
                            )
                            # Auto-reward
                            await db.reward_referral(str(user.id))

    async def _check_balance_milestone(self, message: discord.Message):
        """Check if a user reached $12 minimum withdrawal."""
        for user in message.mentions:
            if user.bot:
                continue
            db_user = await db.get_user(str(user.id))
            if db_user and db_user.balance_cents >= MIN_WITHDRAWAL_CENTS:
                referral_logs = discord.utils.get(message.guild.text_channels, name="referral-logs")
                if referral_logs:
                    await referral_logs.send(
                        f"Congratulations <@{user.id}>! Your balance is now **${db_user.balance_cents / 100:.2f}**. "
                        f"You are free to request a withdrawal! Use `/withdraw` in <#1533919277239767243> to check your status."
                    )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
