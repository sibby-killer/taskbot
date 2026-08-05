"""
Section 13 — Moderation & Announcement Approval.

- Any message from Redwire's bot (REDWIRE_BOT_ID in .env) gets pulled and
  routed to #announcement-queue for Approve/Decline instead of posting
  directly — per the plan, task-related DMs from their bot to individual
  taskers are a separate channel entirely and are never touched by this
  (this cog only watches server channels, not DMs), so those are
  effectively "auto-approved" by simply never passing through this queue.
- A basic keyword/link filter auto-deletes obvious ad/promo/spam content
  from anyone (not just the provider bot) and logs it to #mod-log.
"""

import os
import re
import discord
from discord.ext import commands

REDWIRE_BOT_ID = os.environ.get("REDWIRE_BOT_ID")

BANNED_PATTERNS = [
    r"\bdiscord\.gg/\w+",  # other server invites
    r"\bfree\s+nitro\b",
    r"\bcrypto\s+giveaway\b",
    r"\bonlyfans\.com\b",
    r"\bt\.me/\w+",  # telegram promo links (adjust as needed — legitimate payment-related links go through /withdraw, not chat)
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in BANNED_PATTERNS]


class ApprovalView(discord.ui.View):
    """Note: unlike RefreshTierButton, this view is NOT re-registered on
    startup (its buttons carry per-message state — the announcement text —
    that isn't stored anywhere to reconstruct after a restart). If the bot
    restarts while an announcement is sitting in the queue, the buttons on
    that specific message stop working; Admin can just re-approve manually
    by copying the text into #announcements. Restarts should be rare enough
    on Render that this is a reasonable tradeoff over adding a queue table."""

    def __init__(self, original_content: str, original_channel_id: int):
        super().__init__(timeout=None)
        self.original_content = original_content
        self.original_channel_id = original_channel_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="announce_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        announcements = discord.utils.get(interaction.guild.text_channels, name="announcements")
        if announcements:
            await announcements.send(self.original_content)
        await interaction.response.edit_message(content=f"✅ **Approved and posted** by {interaction.user.mention}\n\n{self.original_content}", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, custom_id="announce_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"❌ **Declined** by {interaction.user.mention}\n\n{self.original_content}", view=None)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        # --- Provider bot announcement routing ---
        if REDWIRE_BOT_ID and str(message.author.id) == REDWIRE_BOT_ID:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            queue_channel = discord.utils.get(message.guild.text_channels, name="announcement-queue")
            if queue_channel:
                view = ApprovalView(message.content, message.channel.id)
                await queue_channel.send(
                    f"📢 New announcement from Redwire's bot (posted in #{message.channel.name}):\n\n{message.content}",
                    view=view,
                )
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

        # --- Keyword/link auto-block for everyone else ---
        if message.author.bot:
            return
        if any(p.search(message.content) for p in _COMPILED):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            mod_log = discord.utils.get(message.guild.text_channels, name="mod-log")
            if mod_log:
                await mod_log.send(f"🚫 Auto-blocked message from {message.author.mention} in {message.channel.mention}:\n> {message.content}")
            try:
                await message.author.send("Your message was removed — it matched a blocked pattern (ads/promo links aren't allowed). Contact an Admin if this was a mistake.")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
