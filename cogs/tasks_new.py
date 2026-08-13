import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import time
import db
from rates import POST_RATE_CENTS, COMMENT_RATE_CENTS, MIN_WITHDRAWAL_CENTS

TASKS_CHANNEL_ID = '1537510579575459840'
ADMIN_ROLE_ID = '1533788208037498942'
BOT_LOGS_CHANNEL = '1533811521190891660'
ANNOUNCEMENTS_CHANNEL = '1533811503596306545'
EVERYONE_ROLE = '1533310208695079093'

POST_COOLDOWN = 2 * 3600  # 2 hours
COMMENT_COOLDOWN = 30 * 60  # 30 minutes


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_timers = {}

    @app_commands.command(name='request-post', description='Request a Reddit post task')
    @app_commands.describe(title='Post title idea', description='What the post should be about')
    async def request_post(self, interaction: discord.Interaction, title: str, description: str):
        if str(interaction.channel_id) != TASKS_CHANNEL_ID:
            await interaction.response.send_message(
                f'Use <#{TASKS_CHANNEL_ID}> for task requests.',
                ephemeral=True
            )
            return

        user = interaction.user
        user_data = await db.get_user(str(user.id))

        if not user_data or user_data.verification_status != 'approved':
            await interaction.response.send_message(
                'You must be verified first. Use <#1537510572491415592>.',
                ephemeral=True
            )
            return

        # Check cooldown
        last_post = await db.get_last_task_time(str(user.id), 'post')
        if last_post:
            elapsed = time.time() - last_post
            if elapsed < POST_COOLDOWN:
                remaining = int(POST_COOLDOWN - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                await interaction.response.send_message(
                    f'⏳ **Cooldown active!**\n\n'
                    f'You must wait **{hours}h {minutes}m** before requesting another post.\n'
                    f'Posts have a 2-hour cooldown.',
                    ephemeral=True
                )
                return

        # Check failure limit
        failures = await db.count_failed_tasks(str(user.id))
        if failures >= 3:
            await interaction.response.send_message(
                '⚠️ **Too many failed tasks.** You have 3+ rejected tasks. Contact admin.',
                ephemeral=True
            )
            return

        # Check pending tasks
        user_tasks = await db.get_user_tasks(str(user.id))
        pending = [t for t in user_tasks if t['status'] in ('pending', 'assigned')]
        if pending:
            await interaction.response.send_message(
                '⚠️ **You already have a pending task.** Complete it before requesting another.',
                ephemeral=True
            )
            return

        request_id = await db.create_task_request(str(user.id), 'post', title, description)

        embed = discord.Embed(
            title='📝 Post Task Request',
            color=0x5865F2,
            description=f'**{user.name}** requested a post task.'
        )
        embed.add_field(name='Title Idea', value=title, inline=False)
        embed.add_field(name='Description', value=description, inline=False)
        embed.add_field(name='Request ID', value=f'#{request_id}', inline=True)
        embed.add_field(name='Earnings', value=f'${POST_RATE_CENTS[user_data.tier]/100:.2f}', inline=True)
        embed.set_footer(text='⚠️ 30min countdown starts when admin assigns task | 5min after receiving link | 2min warning before expiry')

        await interaction.response.send_message(
            embed=embed,
            view=TaskReviewView(request_id, user.id, 'post'),
            allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=ADMIN_ROLE_ID)])
        )

    @app_commands.command(name='request-comment', description='Request a Reddit comment task')
    @app_commands.describe(title='Comment topic', description='What the comment should say')
    async def request_comment(self, interaction: discord.Interaction, title: str, description: str):
        if str(interaction.channel_id) != TASKS_CHANNEL_ID:
            await interaction.response.send_message(
                f'Use <#{TASKS_CHANNEL_ID}> for task requests.',
                ephemeral=True
            )
            return

        user = interaction.user
        user_data = await db.get_user(str(user.id))

        if not user_data or user_data.verification_status != 'approved':
            await interaction.response.send_message(
                'You must be verified first. Use <#1537510572491415592>.',
                ephemeral=True
            )
            return

        # Check cooldown
        last_comment = await db.get_last_task_time(str(user.id), 'comment')
        if last_comment:
            elapsed = time.time() - last_comment
            if elapsed < COMMENT_COOLDOWN:
                remaining = int(COMMENT_COOLDOWN - elapsed)
                minutes = remaining // 60
                await interaction.response.send_message(
                    f'⏳ **Cooldown active!**\n\n'
                    f'You must wait **{minutes}m** before requesting another comment.\n'
                    f'Comments have a 30-minute cooldown.',
                    ephemeral=True
                )
                return

        # Check failure limit
        failures = await db.count_failed_tasks(str(user.id))
        if failures >= 3:
            await interaction.response.send_message(
                '⚠️ **Too many failed tasks.** You have 3+ rejected tasks. Contact admin.',
                ephemeral=True
            )
            return

        # Check pending tasks
        user_tasks = await db.get_user_tasks(str(user.id))
        pending = [t for t in user_tasks if t['status'] in ('pending', 'assigned')]
        if pending:
            await interaction.response.send_message(
                '⚠️ **You already have a pending task.** Complete it before requesting another.',
                ephemeral=True
            )
            return

        request_id = await db.create_task_request(str(user.id), 'comment', title, description)

        embed = discord.Embed(
            title='💬 Comment Task Request',
            color=0x5865F2,
            description=f'**{user.name}** requested a comment task.'
        )
        embed.add_field(name='Topic', value=title, inline=False)
        embed.add_field(name='Description', value=description, inline=False)
        embed.add_field(name='Request ID', value=f'#{request_id}', inline=True)
        embed.add_field(name='Earnings', value=f'${COMMENT_RATE_CENTS[user_data.tier]/100:.2f}', inline=True)
        embed.set_footer(text='⚠️ 30min countdown starts when admin assigns task | 5min after receiving link | 2min warning before expiry')

        await interaction.response.send_message(
            embed=embed,
            view=TaskReviewView(request_id, user.id, 'comment'),
            allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=ADMIN_ROLE_ID)])
        )

    @app_commands.command(name='my-tasks', description='View your tasks and earnings')
    async def my_tasks(self, interaction: discord.Interaction):
        user = interaction.user
        user_data = await db.get_user(str(user.id))

        tasks_list = await db.get_user_tasks(str(user.id))

        embed = discord.Embed(
            title=f'📋 {user.name}\'s Tasks',
            color=0x5865F2
        )

        if not tasks_list:
            embed.description = 'No tasks yet. Use `/request-post` or `/request-comment` to get started.'
        else:
            pending = [t for t in tasks_list if t['status'] in ('pending', 'assigned')]
            submitted = [t for t in tasks_list if t['status'] == 'submitted']
            approved = [t for t in tasks_list if t['status'] == 'approved']
            rejected = [t for t in tasks_list if t['status'] == 'rejected']

            if pending:
                pending_text = '\n'.join([f'• #{t["id"]} - {t["task_type"]} - {t["title"][:30]}' for t in pending[:5]])
                embed.add_field(name='⏳ Pending', value=pending_text, inline=False)

            if submitted:
                submitted_text = '\n'.join([f'• #{t["id"]} - {t["task_type"]} - {t["title"][:30]}' for t in submitted[:5]])
                embed.add_field(name='📤 Submitted', value=submitted_text, inline=False)

            if approved:
                approved_text = '\n'.join([f'• #{t["id"]} - {t["task_type"]} - ${t["pay_cents"]/100:.2f}' for t in approved[:5]])
                total_earned = sum(t['pay_cents'] for t in approved)
                embed.add_field(name=f'✅ Approved ({len(approved)} total)', value=f'{approved_text}\n\n**Total Earned: ${total_earned/100:.2f}**', inline=False)

            if rejected:
                rejected_text = '\n'.join([f'• #{t["id"]} - {t["task_type"]} - {t.get("admin_note", "No reason")[:30]}' for t in rejected[:3]])
                embed.add_field(name=f'❌ Rejected ({len(rejected)})', value=rejected_text, inline=False)

        if user_data:
            embed.add_field(name='💰 Balance', value=f'${user_data.balance_cents/100:.2f}', inline=True)
            embed.add_field(name='🏆 Tier', value=f'{user_data.tier}', inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='submit-task', description='Submit your completed task')
    @app_commands.describe(request_id='Task ID from /my-tasks', link='Link to your Reddit post/comment')
    async def submit_task(self, interaction: discord.Interaction, request_id: int, link: str):
        task = await db.get_task_by_id(request_id)
        if not task:
            await interaction.response.send_message('Task not found.', ephemeral=True)
            return

        if task['discord_id'] != str(interaction.user.id):
            await interaction.response.send_message('This is not your task.', ephemeral=True)
            return

        if task['status'] != 'assigned':
            await interaction.response.send_message('This task cannot be submitted.', ephemeral=True)
            return

        await db.submit_task(request_id, link)

        embed = discord.Embed(
            title='📤 Task Submitted',
            description=f'**Task #{request_id}** submitted by {interaction.user.mention}',
            color=0xFFA500
        )
        embed.add_field(name='Link', value=f'[Click here]({link})', inline=False)
        embed.set_footer(text='Waiting for admin approval')

        await interaction.response.send_message(embed=embed)

        # Notify admin
        try:
            logs_channel = interaction.guild.get_channel(int(BOT_LOGS_CHANNEL))
            if logs_channel:
                await logs_channel.send(
                    f'📤 **Task #{request_id}** submitted by {interaction.user.mention}\n'
                    f'Link: {link}\n'
                    f'Use admin panel to approve/reject.'
                )
        except:
            pass


class TaskReviewView(discord.ui.View):
    def __init__(self, request_id: int, user_id: str, task_type: str):
        super().__init__(timeout=None)
        self.request_id = request_id
        self.user_id = user_id
        self.task_type = task_type

    @discord.ui.button(label='Assign Task', style=discord.ButtonStyle.green, emoji='✅')
    async def assign(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can assign tasks.', ephemeral=True)
            return

        modal = AssignTaskModal(self.request_id, self.user_id, self.task_type)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red, emoji='❌')
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message('Only admins can reject.', ephemeral=True)
            return

        modal = RejectTaskModal(self.request_id, self.user_id)
        await interaction.response.send_modal(modal)


class AssignTaskModal(discord.ui.Modal, title='Assign Task'):
    reddit_link = discord.ui.TextInput(label='Reddit post/comment link to engage with', required=True)
    pay_cents = discord.ui.TextInput(label='Pay amount in cents (e.g., 150 for $1.50)', required=True)
    instructions = discord.ui.TextInput(label='Additional instructions', required=False, style=discord.TextStyle.paragraph)

    def __init__(self, request_id: int, user_id: str, task_type: str):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id
        self.task_type = task_type

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pay = int(self.pay_cents.value)
        except ValueError:
            await interaction.response.send_message('Invalid pay amount.', ephemeral=True)
            return

        await db.assign_task(self.request_id, pay)

        # Start countdown timer
        embed = discord.Embed(
            title='✅ Task Assigned!',
            color=0x00FF00,
            description=f'**Task #{self.request_id}** assigned to <@{self.user_id}>'
        )
        embed.add_field(name='Reddit Link', value=f'[Click here]({self.reddit_link.value})', inline=False)
        embed.add_field(name='Pay', value=f'${pay/100:.2f}', inline=True)
        embed.add_field(name='Time Limit', value='**30 minutes** to complete', inline=True)

        if self.instructions.value:
            embed.add_field(name='Instructions', value=self.instructions.value, inline=False)

        embed.set_footer(text='⚠️ 30min countdown | 5min after receiving link | 2min warning | Then task goes to someone else')

        await interaction.response.edit_message(embed=embed, view=None)

        # Notify user
        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            await user.send(
                f'🎯 **Task Assigned!**\n\n'
                f'**Task #{self.request_id}** has been assigned to you.\n\n'
                f'**Reddit Link:** {self.reddit_link.value}\n'
                f'**Pay:** ${pay/100:.2f}\n'
                f'**Time Limit:** 30 minutes\n\n'
                f'⚠️ You have **30 minutes** to complete this task.\n'
                f'After 5 minutes, you\'ll get a **2-minute warning**.\n'
                f'If you fail to submit on time, the task will be reassigned.\n\n'
                f'Use `/submit-task {self.request_id} <link>` when done.'
            )
        except discord.Forbidden:
            pass

        # Start countdown
        asyncio.create_task(self.start_countdown(interaction.client))

    async def start_countdown(self, bot):
        user = await bot.fetch_user(int(self.user_id))

        # 25 minutes warning (5 minutes left)
        await asyncio.sleep(25 * 60)
        try:
            await user.send(
                f'⏰ **5 minutes remaining!**\n\n'
                f'Task #{self.request_id} expires in 5 minutes.\n'
                f'Use `/submit-task {self.request_id} <link>` now!'
            )
        except:
            pass

        # 28 minutes (2 minutes left)
        await asyncio.sleep(2 * 60)
        try:
            await user.send(
                f'🚨 **2 MINUTES LEFT!**\n\n'
                f'Task #{self.request_id} expires in 2 minutes!\n'
                f'Submit NOW or the task will be reassigned!'
            )
        except:
            pass

        # Final 2 minutes
        await asyncio.sleep(2 * 60)

        # Check if still assigned
        task = await db.get_task_by_id(self.request_id)
        if task and task['status'] == 'assigned':
            await db.reject_task(self.request_id, 'Timed out - not submitted in time')
            try:
                await user.send(
                    f'❌ **Task Expired**\n\n'
                    f'Task #{self.request_id} has been reassigned because you did not submit in time.'
                )
            except:
                pass


class RejectTaskModal(discord.ui.Modal, title='Reject Task'):
    reason = discord.ui.TextInput(label='Reason for rejection', required=True)

    def __init__(self, request_id: int, user_id: str):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        await db.reject_task(self.request_id, self.reason.value)

        embed = discord.Embed(
            title='❌ Task Rejected',
            description=f'**Task #{self.request_id}** rejected by {interaction.user.mention}\n**Reason:** {self.reason.value}',
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            await user.send(
                f'❌ **Task Rejected**\n\n'
                f'Task #{self.request_id} has been rejected.\n'
                f'**Reason:** {self.reason.value}\n\n'
                f'You can request a new task in <#{TASKS_CHANNEL_ID}>.'
            )
        except:
            pass


async def setup(bot):
    await bot.add_cog(TasksCog(bot))
