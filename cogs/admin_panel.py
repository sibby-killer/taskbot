import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import db
from rates import POST_RATE_CENTS, COMMENT_RATE_CENTS, MIN_WITHDRAWAL_CENTS, RATES_CENTS

ADMIN_ROLE_ID = 1533788208037498942
ANNOUNCEMENTS_CHANNEL = 1533811503596306545
BOT_LOGS_CHANNEL = 1533811521190891660
EVERYONE_ROLE = 1533310208695079093


class AdminPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_reminder.start()

    def cog_unload(self):
        self.daily_reminder.cancel()

    # ── Admin Panel ──────────────────────────────────────────────

    @app_commands.command(name='admin-panel', description='Open the admin dashboard')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def admin_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title='🔧 Admin Dashboard',
            color=0x5865F2,
            description='Select an option below:'
        )
        embed.add_field(name='👥 Users', value='View all users, tasks, and earnings', inline=True)
        embed.add_field(name='📋 Tasks', value='View pending/approved/rejected tasks', inline=True)
        embed.add_field(name='💰 Rates', value='Update task rates', inline=True)
        embed.add_field(name='💸 Withdrawals', value='Manage withdrawal requests', inline=True)
        embed.add_field(name='📊 Stats', value='Server statistics', inline=True)

        await interaction.response.send_message(
            embed=embed,
            view=AdminDashboardView(),
            ephemeral=True
        )

    # ── User Management ──────────────────────────────────────────

    @app_commands.command(name='users', description='List all users with tasks and earnings')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def list_users(self, interaction: discord.Interaction):
        users = await db.get_all_users()
        if not users:
            await interaction.response.send_message('No users found.', ephemeral=True)
            return

        embed = discord.Embed(
            title='👥 All Users',
            color=0x5865F2
        )

        total_earned = 0
        total_tasks = 0

        for user in users[:25]:
            tasks_list = await db.get_user_tasks(user['discord_id'])
            approved = [t for t in tasks_list if t['status'] == 'approved']
            earned = sum(t['pay_cents'] for t in approved)
            total_earned += earned
            total_tasks += len(approved)

            status_emoji = '✅' if user['verification_status'] == 'approved' else '⏳'
            embed.add_field(
                name=f'{status_emoji} {user.get("reddit_username", "Unknown")}',
                value=f'<@{user["discord_id"]}> | Tier {user.tier} | ${earned/100:.2f} earned | {len(approved)} tasks',
                inline=False
            )

        embed.set_footer(text=f'Total: {len(users)} users | {total_tasks} tasks | ${total_earned/100:.2f} earned')

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Task Management ──────────────────────────────────────────

    @app_commands.command(name='pending-tasks', description='View all pending task submissions')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def pending_tasks(self, interaction: discord.Interaction):
        tasks_list = await db.get_pending_task_requests()
        if not tasks_list:
            await interaction.response.send_message('No pending tasks.', ephemeral=True)
            return

        embed = discord.Embed(
            title='📋 Pending Task Submissions',
            color=0xFFA500
        )

        for task in tasks_list[:10]:
            embed.add_field(
                name=f'#{task["id"]} - {task["task_type"].title()}',
                value=f'<@{task["discord_id"]}> | {task["title"][:50]}\nStatus: {task["status"]} | Pay: ${task["pay_cents"]/100:.2f}',
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='approve-task', description='Approve a submitted task')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(request_id='Task ID to approve')
    async def approve_task(self, interaction: discord.Interaction, request_id: int):
        task = await db.get_task_by_id(request_id)
        if not task:
            await interaction.response.send_message('Task not found.', ephemeral=True)
            return

        if task['status'] != 'submitted':
            await interaction.response.send_message('This task is not submitted yet.', ephemeral=True)
            return

        # Credit balance
        await db.add_balance(task['discord_id'], task['pay_cents'])

        # Trigger referral if applicable
        referral = await db.get_referral_by_referred(task['discord_id'])
        if referral and not referral.qualified:
            user_tasks = await db.get_user_tasks(task['discord_id'])
            approved_posts = [t for t in user_tasks if t['status'] == 'approved' and t['task_type'] == 'post']
            approved_comments = [t for t in user_tasks if t['status'] == 'approved' and t['task_type'] == 'comment']
            if approved_posts and approved_comments:
                await db.qualify_referral(task['discord_id'])
                await db.reward_referral(task['discord_id'])
                try:
                    referrer = await interaction.client.fetch_user(int(referral.referrer_discord_id))
                    await referrer.send(
                        f'🎉 **Referral Reward!**\n\n'
                        f'You earned **$1.00** for referring someone!\n'
                        f'They completed their first post + comment.'
                    )
                except:
                    pass

        # Check balance milestone
        user_data = await db.get_user(task['discord_id'])
        if user_data and user_data.balance_cents >= MIN_WITHDRAWAL_CENTS:
            try:
                user = await interaction.client.fetch_user(int(task['discord_id']))
                await user.send(
                    f'🎉 **Congratulations!**\n\n'
                    f'Your balance is now **${user_data.balance_cents/100:.2f}**!\n'
                    f'You can withdraw using `/withdraw`.'
                )
            except:
                pass

        await db.approve_task(request_id)

        embed = discord.Embed(
            title='✅ Task Approved',
            description=f'Task #{request_id} approved by {interaction.user.mention}',
            color=0x00FF00
        )
        embed.add_field(name='Pay', value=f'${task["pay_cents"]/100:.2f}', inline=True)

        await interaction.response.send_message(embed=embed)

        try:
            user = await interaction.client.fetch_user(int(task['discord_id']))
            await user.send(
                f'✅ **Task Approved!**\n\n'
                f'Task #{request_id} approved.\n'
                f'**Pay:** ${task["pay_cents"]/100:.2f}\n'
                f'**New Balance:** ${user_data.balance_cents/100:.2f}'
            )
        except:
            pass

    # ── Rate Management ──────────────────────────────────────────

    @app_commands.command(name='update-rates', description='Update task rates')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(
        task_type='post or comment',
        tier='1, 2, or 3',
        tasker_rate='New tasker rate in cents'
    )
    async def update_rates(self, interaction: discord.Interaction, task_type: str, tier: int, tasker_rate: int):
        if task_type not in ('post', 'comment'):
            await interaction.response.send_message('Invalid task type.', ephemeral=True)
            return
        if tier not in (1, 2, 3):
            await interaction.response.send_message('Invalid tier.', ephemeral=True)
            return

        # Update rates
        RATES_CENTS[task_type][tier]['tasker'] = tasker_rate
        RATES_CENTS[task_type][tier]['company'] = int(tasker_rate * 2)

        # Update flat rate lookups
        if task_type == 'post':
            POST_RATE_CENTS[tier] = tasker_rate
        else:
            COMMENT_RATE_CENTS[tier] = tasker_rate

        embed = discord.Embed(
            title='💰 Rates Updated',
            description=f'{task_type.title()} Tier {tier} updated by {interaction.user.mention}',
            color=0x00FF00
        )
        embed.add_field(name='New Tasker Rate', value=f'${tasker_rate/100:.2f}', inline=True)
        embed.add_field(name='New Company Rate', value=f'${RATES_CENTS[task_type][tier]["company"]/100:.2f}', inline=True)

        await interaction.response.send_message(embed=embed)

    # ── Withdrawal Management ────────────────────────────────────

    @app_commands.command(name='pending-withdrawals', description='View all pending withdrawals')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    async def pending_withdrawals(self, interaction: discord.Interaction):
        withdrawals = await db.get_pending_withdrawals()
        if not withdrawals:
            await interaction.response.send_message('No pending withdrawals.', ephemeral=True)
            return

        embed = discord.Embed(
            title='💸 Pending Withdrawals',
            color=0xFFA500
        )

        for w in withdrawals[:10]:
            embed.add_field(
                name=f'#{w["id"]} - ${w["amount_cents"]/100:.2f}',
                value=f'<@{w["discord_id"]}> | {w["payment_method"]} | {w["payment_details"][:30]}',
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='mark-paid', description='Mark a withdrawal as paid')
    @app_commands.checks.has_role(ADMIN_ROLE_ID)
    @app_commands.describe(withdrawal_id='Withdrawal ID to mark as paid')
    async def mark_paid(self, interaction: discord.Interaction, withdrawal_id: int):
        await db.mark_withdrawal_paid(withdrawal_id, f'Paid by {interaction.user.name}')

        embed = discord.Embed(
            title='✅ Withdrawal Paid',
            description=f'Withdrawal #{withdrawal_id} marked as paid by {interaction.user.mention}',
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)

    # ── Daily Reminders ──────────────────────────────────────────

    DAILY_MESSAGES = [
        # Morning messages
        [
            '☀️ **Good morning Taskers!**\n\nNew day, new tasks! Start earning now:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nFirst come, first served!',
            '🌅 **Rise and grind!**\n\nTasks are live! Grab yours before they\'re gone:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nDon\'t miss out!',
            '☕ **Morning check-in!**\n\nReady to earn? Tasks available now:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nLet\'s go!',
        ],
        # Afternoon messages
        [
            '🌤️ **Afternoon update!**\n\nStill earning? More tasks dropped:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nGrab yours!',
            '⚡ **Midday push!**\n\nTasks are flowing! Don\'t miss out:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nLet\'s get it!',
            '🎯 **Afternoon reminder!**\n\nSpots filling up fast:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nAct now!',
        ],
        # Evening messages
        [
            '🌙 **Evening session!**\n\nNight owls, tasks are live:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nEarn before bed!',
            '🔥 **Last call!**\n\nFinal tasks of the day:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nDon\'t sleep on this!',
            '✨ **Evening grind!**\n\nStill opportunities available:\n• `/request-post` — $1.00\n• `/request-comment` — $0.50\n\nEnd the day strong!',
        ],
    ]

    @tasks.loop(hours=8)
    async def daily_reminder(self):
        try:
            import random
            from datetime import datetime
            hour = datetime.now().hour
            
            if 5 <= hour < 12:
                messages = self.DAILY_MESSAGES[0]
            elif 12 <= hour < 17:
                messages = self.DAILY_MESSAGES[1]
            else:
                messages = self.DAILY_MESSAGES[2]

            message = random.choice(messages)

                channel = self.bot.get_channel(ANNOUNCEMENTS_CHANNEL)
                if channel:
                    await channel.send(
                        f'<@&{EVERYONE_ROLE}>\n\n{message}'
                    )
        except Exception as e:
            print(f'Daily reminder error: {e}')

    @daily_reminder.before_loop
    async def before_daily_reminder(self):
        await self.bot.wait_until_ready()


class AdminDashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder='Select an option...',
        options=[
            discord.SelectOption(label='Users', description='View all users with tasks and earnings', emoji='👥'),
            discord.SelectOption(label='Tasks', description='View pending task submissions', emoji='📋'),
            discord.SelectOption(label='Rates', description='Update task rates', emoji='💰'),
            discord.SelectOption(label='Withdrawals', description='Manage withdrawal requests', emoji='💸'),
            discord.SelectOption(label='Stats', description='Server statistics', emoji='📊'),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values[0] == 'Users':
            users = await db.get_all_users()
            embed = discord.Embed(title='👥 All Users', color=0x5865F2)
            for user in users[:10]:
                tasks_list = await db.get_user_tasks(user['discord_id'])
                approved = [t for t in tasks_list if t['status'] == 'approved']
                earned = sum(t['pay_cents'] for t in approved)
                embed.add_field(
                    name=f'{user.get("reddit_username", "Unknown")}',
                    value=f'<@{user["discord_id"]}> | ${earned/100:.2f} | {len(approved)} tasks',
                    inline=False
                )
            await interaction.response.edit_message(embed=embed, view=self)

        elif select.values[0] == 'Tasks':
            tasks_list = await db.get_pending_task_requests()
            embed = discord.Embed(title='📋 Pending Tasks', color=0xFFA500)
            for task in tasks_list[:10]:
                embed.add_field(
                    name=f'#{task["id"]} - {task["task_type"]}',
                    value=f'<@{task["discord_id"]}> | {task["status"]}',
                    inline=False
                )
            await interaction.response.edit_message(embed=embed, view=self)

        elif select.values[0] == 'Rates':
            embed = discord.Embed(title='💰 Current Rates', color=0x00FF00)
            for task_type in ['post', 'comment']:
                for tier in [1, 2, 3]:
                    rate = RATES_CENTS[task_type][tier]['tasker']
                    embed.add_field(
                        name=f'{task_type.title()} Tier {tier}',
                        value=f'${rate/100:.2f}',
                        inline=True
                    )
            await interaction.response.edit_message(embed=embed, view=self)

        elif select.values[0] == 'Withdrawals':
            withdrawals = await db.get_pending_withdrawals()
            embed = discord.Embed(title='💸 Pending Withdrawals', color=0xFFA500)
            for w in withdrawals[:10]:
                embed.add_field(
                    name=f'#{w["id"]} - ${w["amount_cents"]/100:.2f}',
                    value=f'<@{w["discord_id"]}> | {w["payment_method"]}',
                    inline=False
                )
            await interaction.response.edit_message(embed=embed, view=self)

        elif select.values[0] == 'Stats':
            users = await db.get_all_users()
            tasks_list = await db.get_pending_task_requests()
            withdrawals = await db.get_pending_withdrawals()
            embed = discord.Embed(title='📊 Server Stats', color=0x5865F2)
            embed.add_field(name='Users', value=str(len(users)), inline=True)
            embed.add_field(name='Pending Tasks', value=str(len(tasks_list)), inline=True)
            embed.add_field(name='Pending Withdrawals', value=str(len(withdrawals)), inline=True)
            await interaction.response.edit_message(embed=embed, view=self)


async def setup(bot):
    await bot.add_cog(AdminPanelCog(bot))
