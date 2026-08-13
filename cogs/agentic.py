import discord
from discord.ext import commands
import db

ADMIN_ROLE_ID = '1533788208037498942'
ADMIN_USER_ID = '829433351731240991'  # alfasibby69

HELP_RESPONSES = {
    'verify': 'To verify your Reddit account, go to <#1537510572491415592> and use the `/verify` command with your Reddit username, a screenshot, and your profile link.',
    'task': 'To request a task, go to <#1537510579575459840> and use `/request-post` or `/request-comment`.',
    'post': 'To request a post task, use `/request-post` in <#1537510579575459840>.',
    'comment': 'To request a comment task, use `/request-comment` in <#1537510579575459840>.',
    'withdraw': 'To withdraw your earnings, use `/withdraw` when your balance reaches $12 minimum.',
    'balance': 'To check your balance, use `/my-tasks` or `/profile`.',
    'profile': 'To view your profile, use `/profile`.',
    'help': 'I can help with:\n• Verification: `/verify`\n• Tasks: `/request-post` or `/request-comment`\n• Balance: `/my-tasks`\n• Withdrawal: `/withdraw`\n\nFor other questions, tag the admin!',
    'cqs': 'To check your Reddit CQS, go to r/WhatIsMyCQS and comment "!cqs". More info in <#1537510584046846004>.',
    'account': 'To request an account, go to <#1537510587964071967> and use `/request-account`.',
    'warming': 'Account warming guide is in <#1537510584046846004>. Follow the Day 0-10 schedule.',
}


class AgenticBotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            content = message.content.lower().replace(f'<@{self.bot.user.id}>', '').strip()

            # Find matching help response
            response = None
            for keyword, help_text in HELP_RESPONSES.items():
                if keyword in content:
                    response = help_text
                    break

            if response:
                await message.reply(response, mention_author=True)
            else:
                # Tag admin and direct user to wait
                await message.reply(
                    f'Hi! I\'m not sure how to help with that.\n\n'
                    f'<@{ADMIN_USER_ID}> please assist <@{message.author.id}>.\n\n'
                    f'You can also check:\n'
                    f'• <#1537510584046846004> for account guides\n'
                    f'• <#1537510521059491842> for commands\n'
                    f'• Type "help" for available commands',
                    mention_author=True
                )


async def setup(bot):
    await bot.add_cog(AgenticBotCog(bot))
