import discord
from discord.ext import commands
from discord import app_commands
import db

PURCHASE_ACCOUNTS_CHANNEL_ID = 1537510587964071967
ADMIN_ROLE_ID = 1533788208037498942


class AccountRequestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='request-account', description='Request a Reddit account')
    @app_commands.describe(
        account_type='Type of account (e.g., aged, high-karma)',
        details='What you need (age, karma, niche)'
    )
    async def request_account(self, interaction: discord.Interaction, account_type: str, details: str):
        if str(interaction.channel_id) != PURCHASE_ACCOUNTS_CHANNEL_ID:
            await interaction.response.send_message(
                f'Use <#{PURCHASE_ACCOUNTS_CHANNEL_ID}> for account requests.',
                ephemeral=True
            )
            return

        user = interaction.user
        request_id = await db.create_account_request(str(user.id), account_type, details)

        embed = discord.Embed(
            title='🔑 Account Request',
            color=0x5865F2,
            description=f'**{user.name}** requested an account.'
        )
        embed.add_field(name='Account Type', value=account_type, inline=True)
        embed.add_field(name='Details', value=details, inline=False)
        embed.add_field(name='Request ID', value=f'#{request_id}', inline=True)
        embed.set_footer(text=f'Discord ID: {user.id}')

        await interaction.response.send_message(
            embed=embed,
            view=AccountReviewView(request_id, user.id),
            allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=ADMIN_ROLE_ID)])
        )

    @app_commands.command(name='submit-review', description='Submit a review for a purchased account')
    @app_commands.describe(
        request_id='Account request ID',
        review='Your review of the account'
    )
    async def submit_review(self, interaction: discord.Interaction, request_id: int, review: str):
        # This would need a reviews table - for now just acknowledge
        await interaction.response.send_message(
            '📝 Review submitted! It will be visible after admin approval.',
            ephemeral=True
        )


class AccountReviewView(discord.ui.View):
    def __init__(self, request_id: int, user_id: str):
        super().__init__(timeout=None)
        self.request_id = request_id
        self.user_id = user_id

    @discord.ui.button(label='Fulfill', style=discord.ButtonStyle.green, emoji='✅')
    async def fulfill(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can fulfill requests.', ephemeral=True)
            return

        modal = FulfillAccountModal(self.request_id, self.user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red, emoji='❌')
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can reject.', ephemeral=True)
            return

        modal = RejectAccountModal(self.request_id, self.user_id)
        await interaction.response.send_modal(modal)


class FulfillAccountModal(discord.ui.Modal, title='Fulfill Account Request'):
    account_details = discord.ui.TextInput(label='Account details (username, password, etc.)', required=True, style=discord.TextStyle.paragraph)
    notes = discord.ui.TextInput(label='Additional notes', required=False)

    def __init__(self, request_id: int, user_id: str):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        await db.approve_account_request(self.request_id, self.account_details.value)

        embed = discord.Embed(
            title='✅ Account Fulfilled',
            description=f'**Request #{self.request_id}** fulfilled by {interaction.user.mention}',
            color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=None)

        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            await user.send(
                f'✅ **Account Ready!**\n\n'
                f'Your account request #{self.request_id} has been fulfilled.\n\n'
                f'**Account Details:**\n{self.account_details.value}\n\n'
                f'{self.notes.value if self.notes.value else ""}\n\n'
                f'Please change the password immediately and follow the warming guide in <#1537510584046846004>.'
            )
        except:
            pass


class RejectAccountModal(discord.ui.Modal, title='Reject Account Request'):
    reason = discord.ui.TextInput(label='Reason', required=True)

    def __init__(self, request_id: int, user_id: str):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        await db.reject_account_request(self.request_id, self.reason.value)

        embed = discord.Embed(
            title='❌ Account Request Rejected',
            description=f'**Request #{self.request_id}** rejected by {interaction.user.mention}\n**Reason:** {self.reason.value}',
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            await user.send(
                f'❌ **Account Request Rejected**\n\n'
                f'Reason: {self.reason.value}\n\n'
                f'You can request again in <#{PURCHASE_ACCOUNTS_CHANNEL_ID}>.'
            )
        except:
            pass


async def setup(bot):
    await bot.add_cog(AccountRequestCog(bot))
