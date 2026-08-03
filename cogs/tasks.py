"""
Task pool — admin-only /add-task command.
Task request/submit is handled by Redwire (/gettask, /submit).
"""

import discord
from discord import app_commands
from discord.ext import commands

import db


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add-task", description="[Admin] Add a task to the fallback pool.")
    @app_commands.checks.has_role("Admin")
    @app_commands.describe(task_type="post or comment", title="Title", body="Body text", destination_url="Where to post it", min_tier="Minimum tier required")
    async def add_task(self, interaction: discord.Interaction, task_type: str, title: str, body: str, destination_url: str, min_tier: int = 1):
        if task_type not in ("post", "comment"):
            await interaction.response.send_message("task_type must be `post` or `comment`.", ephemeral=True)
            return
        task_id = await db.add_pool_task(task_type, title, body, destination_url, min_tier)
        await interaction.response.send_message(f"Added task #{task_id} ({task_type}, min tier {min_tier}).", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
