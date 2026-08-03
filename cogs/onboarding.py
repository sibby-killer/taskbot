"""
Onboarding — /refresh-tier only.
Verify is handled by Redwire. Referrals handled by Invite Tracker.
"""

import discord
from discord import app_commands
from discord.ext import commands

import db
import reddit
from tiers import calculate_tier


async def apply_verification_result(
    guild: discord.Guild,
    member: discord.abc.User,
    reddit_username: str,
    country: str,
    full_name: str,
    whatsapp_contact: str,
    profile: reddit.RedditProfile,
):
    """Shared by /refresh-tier — saves to DB and syncs tier role."""
    tier_result = calculate_tier(profile.total_karma, profile.comment_karma, profile.account_age_days)

    await db.upsert_verified_user(
        discord_id=str(member.id),
        reddit_username=profile.username,
        country=country,
        full_name=full_name,
        whatsapp_contact=whatsapp_contact,
        tier=tier_result.tier,
        total_karma=profile.total_karma,
        comment_karma=profile.comment_karma,
        account_age_days=profile.account_age_days,
    )

    guild_member = guild.get_member(member.id) or await guild.fetch_member(member.id)
    tasker_role = discord.utils.get(guild.roles, name="Tasker")
    tier_role = discord.utils.get(guild.roles, name=f"Tier {tier_result.tier}")

    for other_tier in (1, 2, 3):
        r = discord.utils.get(guild.roles, name=f"Tier {other_tier}")
        if r and r in guild_member.roles and r != tier_role:
            await guild_member.remove_roles(r)

    roles_to_add = [r for r in (tasker_role, tier_role) if r and r not in guild_member.roles]
    if roles_to_add:
        await guild_member.add_roles(*roles_to_add)

    log_channel = discord.utils.get(guild.text_channels, name="onboarding-log")
    if log_channel:
        await log_channel.send(
            f"**{guild_member.mention}** refreshed tier — u/{profile.username} | Tier {tier_result.tier}\n"
            f"karma {profile.total_karma} | age {profile.account_age_days}d — {tier_result.reason}"
        )

    return tier_result


class RefreshTierButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh Tier", style=discord.ButtonStyle.secondary, custom_id="refresh_tier_button")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = await db.get_user(str(interaction.user.id))
        if not user or not user.reddit_username:
            await interaction.response.send_message("Use Redwire's `/verify` command first to link your Reddit account.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        profile = await reddit.verify_reddit_account(user.reddit_username)
        if not profile.exists or profile.is_suspended:
            await interaction.followup.send(f"{profile.error or 'Could not re-check that account.'}", ephemeral=True)
            return

        tier_result = await apply_verification_result(
            interaction.guild, interaction.user, user.reddit_username, user.country, user.full_name, user.whatsapp_contact, profile
        )
        await interaction.followup.send(f"Refreshed — you're now **Tier {tier_result.tier}**.\n{tier_result.reason}", ephemeral=True)


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="refresh-tier", description="Re-check your Reddit stats in case your tier changed.")
    async def refresh_tier(self, interaction: discord.Interaction):
        view = RefreshTierButton()
        await interaction.response.send_message("Click below to refresh:", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
