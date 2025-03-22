# embeds.py
# Custom embed handler for consistent styling

import discord
from config import JUBJUB_BANNER
from datetime import datetime

class CustomEmbed:
    @staticmethod
    def success(title: str, description: str, timestamp: datetime = None, user=None):
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green(),
            timestamp=timestamp
        )
        if user:
            embed.set_author(name=user.name, icon_url=user.avatar.url)
            embed.set_footer(text=f"Set by {user.name}")
        embed.set_image(url=JUBJUB_BANNER)
        return embed

    @staticmethod
    def error(title: str, description: str):
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red()
        )
        embed.set_image(url=JUBJUB_BANNER)
        return embed

    @staticmethod
    def reminder(user, message: str, reminder_time: datetime, set_time: datetime, channel, recurrence: str, recurrence_time: str = None):
        embed = discord.Embed(
            title="⏰ Reminder!",
            description=message,
            color=discord.Color.green(),
            timestamp=reminder_time
        )
        embed.set_author(name=user.name, icon_url=user.avatar.url)
        embed.set_footer(text="JubJub")
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_image(url=JUBJUB_BANNER)
        embed.add_field(name="Set On", value=set_time.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="Channel", value=channel.mention, inline=False)
        if recurrence != "none":
            embed.add_field(name="Recurrence", value=f"{recurrence} at {recurrence_time}", inline=False)
        return embed

    @staticmethod
    def reminder_list(reminders, active_only: bool, start_index: int = 0, max_per_page: int = 10):
        embed = discord.Embed(
            title="Your Active Reminders" if active_only else "Your Archived Reminders",
            color=discord.Color.green() if active_only else discord.Color.greyple()
        )
        embed.set_image(url=JUBJUB_BANNER)
        
        if not reminders:
            embed.description = "You have no active reminders." if active_only else "You have no archived reminders."
        else:
            end_index = min(start_index + max_per_page, len(reminders))
            for reminder in reminders[start_index:end_index]:
                reminder_time = datetime.fromisoformat(reminder["reminder_time"])
                set_time = datetime.fromisoformat(reminder["set_time"])
                value = (
                    f"**Message**: {reminder['message']}\n"
                    f"**Reminding On**: {reminder_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"**Set On**: {set_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"**Status**: {'Active' if not reminder['is_sent'] else 'Archived'}\n"
                    f"**Recurrence**: {reminder['recurrence'] if reminder['recurrence'] != 'none' else 'None'}"
                )
                embed.add_field(name=f"Reminder (ID: {reminder['id']})", value=value, inline=False)
            embed.set_footer(text=f"Showing {start_index + 1}-{end_index} of {len(reminders)} reminders")
        return embed