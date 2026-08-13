import discord
from discord.ext import commands
from discord import app_commands
import db

VERIFY_CHANNEL_ID = 1537510572491415592
ADMIN_ROLE_ID = 1533788208037498942
TASKER_ROLE_ID = 1533788214849175613
ENGLISH_CHAT_ID = 1533810521059491842


class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='verify', description='Submit Reddit verification (screenshot + profile link)')
    @app_commands.describe(
        reddit_username='Your Reddit username',
        screenshot='Screenshot of your Reddit profile',
        profile_link='Link to your Reddit profile'
    )
    async def verify(self, interaction: discord.Interaction, reddit_username: str, screenshot: discord.Attachment, profile_link: str):
        if str(interaction.channel_id) != VERIFY_CHANNEL_ID:
            await interaction.response.send_message(
                f'Use <#{VERIFY_CHANNEL_ID}> for verification.',
                ephemeral=True
            )
            return

        user = interaction.user
        request_id = await db.create_verification_request(
            str(user.id), reddit_username, screenshot.url, profile_link
        )

        embed = discord.Embed(
            title='📋 Verification Request',
            color=0x5865F2,
            description=f'**{user.name}** submitted a verification request.'
        )
        embed.add_field(name='Reddit Username', value=reddit_username, inline=True)
        embed.add_field(name='Profile Link', value=f'[Click here]({profile_link})', inline=True)
        embed.add_field(name='Request ID', value=f'#{request_id}', inline=True)
        embed.set_image(url=screenshot.url)
        embed.set_footer(text=f'Discord ID: {user.id}')

        await interaction.response.send_message(
            embed=embed,
            view=VerificationReviewView(request_id, user.id, reddit_username),
            allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=ADMIN_ROLE_ID)])
        )

    @app_commands.command(name='pending-verifications', description='List pending verification requests (admin only)')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def pending_verifications(self, interaction: discord.Interaction):
        pending = await db.get_pending_verifications()
        if not pending:
            await interaction.response.send_message('No pending verification requests.', ephemeral=True)
            return

        embed = discord.Embed(
            title='📋 Pending Verifications',
            color=0x5865F2
        )
        for req in pending[:10]:
            embed.add_field(
                name=f'#{req["id"]} - {req["reddit_username"]}',
                value=f'<@{req["discord_id"]}> | [Profile]({req["profile_link"]}) | <t:{int(__import__("datetime").datetime.fromisoformat(req["created_at"]).timestamp())}:R>',
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class VerificationReviewView(discord.ui.View):
    def __init__(self, request_id: int, user_id: str, reddit_username: str):
        super().__init__(timeout=None)
        self.request_id = request_id
        self.user_id = user_id
        self.reddit_username = reddit_username

    @discord.ui.button(label='Approve', style=discord.ButtonStyle.green, emoji='✅')
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can approve.', ephemeral=True)
            return

        await db.approve_verification(self.request_id, f'Approved by {interaction.user.name}')
        await db.upsert_user(self.user_id, reddit_username=self.reddit_username, verification_status='approved')

        member = interaction.guild.get_member(int(self.user_id))
        if member:
            tasker_role = interaction.guild.get_role(TASKER_ROLE_ID)
            if tasker_role:
                await member.add_roles(tasker_role)

        try:
            user = await self.bot.fetch_user(int(self.user_id))
            await user.send(
                f'✅ **Verification Approved!**\n\n'
                f'Welcome to TaskBridge! You now have access to <#{ENGLISH_CHAT_ID}> and can request tasks.\n\n'
                f'Next steps:\n'
                f'1. Check your Reddit account CQS in <#1537510584046846004>\n'
                f'2. Start with the account warming guide\n'
                f'3. Go to <#1537510579575459840> to request tasks'
            )
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title='✅ Verification Approved',
            description=f'**{self.reddit_username}** approved by {interaction.user.mention}',
            color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red, emoji='❌')
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can reject.', ephemeral=True)
            return

        modal = RejectModal(self.request_id, self.user_id, self.reddit_username)
        await interaction.response.send_modal(modal)


class RejectModal(discord.ui.Modal, title='Reject Verification'):
    reason = discord.ui.TextInput(label='Reason for rejection', required=True)

    def __init__(self, request_id: int, user_id: str, reddit_username: str):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id
        self.reddit_username = reddit_username

    async def on_submit(self, interaction: discord.Interaction):
        await db.reject_verification(self.request_id, self.reason.value)

        try:
            user = await self.bot.fetch_user(int(self.user_id))
            await user.send(
                f'❌ **Verification Rejected**\n\n'
                f'**Reason:** {self.reason.value}\n\n'
                f'Please fix the issue and submit again in <#{VERIFY_CHANNEL_ID}>.'
            )
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title='❌ Verification Rejected',
            description=f'**{self.reddit_username}** rejected by {interaction.user.mention}\n**Reason:** {self.reason.value}',
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(VerificationCog(bot))
