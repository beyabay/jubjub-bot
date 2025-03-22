# reminders.py
# Reminder commands and logic

import discord
from discord import app_commands
from discord.ext import tasks
import re
from datetime import datetime, timedelta, timezone
import aiohttp
from embeds import CustomEmbed
from database import post_data, patch_data, fetch_reminders, fetch_due_reminders
from utility_commands import track_command_usage
from config import SUPABASE_URL, SUPABASE_HEADERS  # Add this import

async def remind_me_logic(ctx, reminder_message: str, total_seconds: int, recurrence: str = "none", time_str: str = None):
    now_utc = datetime.now(timezone.utc)
    
    if recurrence != "none":
        if not time_str:
            embed = CustomEmbed.error("Missing Time", "Please specify a time of day (e.g., '07:00') for recurring reminders.")
            await (ctx.response.send_message(embed=embed, ephemeral=True) if hasattr(ctx, 'response') else ctx.send(embed=embed))
            return
        try:
            reminder_hour, reminder_minute = map(int, time_str.split(":"))
            if not (0 <= reminder_hour <= 23 and 0 <= reminder_minute <= 59):
                raise ValueError
        except ValueError:
            embed = CustomEmbed.error("Invalid Time Format", "Time must be in 'HH:MM' format (e.g., '07:00' or '19:00').")
            await (ctx.response.send_message(embed=embed, ephemeral=True) if hasattr(ctx, 'response') else ctx.send(embed=embed))
            return
    else:
        reminder_hour, reminder_minute = None, None

    if recurrence == "none":
        reminder_time = now_utc + timedelta(seconds=total_seconds)
    else:
        reminder_time = now_utc.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
        if total_seconds > 0:
            reminder_time += timedelta(seconds=total_seconds)
        if reminder_time <= now_utc:
            reminder_time = calculate_next_occurrence(reminder_time, recurrence, time_str)

    async with aiohttp.ClientSession() as session:
        user_tz = await get_user_timezone(ctx.user.id, session)
    localized_time = reminder_time.astimezone(user_tz)
    
    payload = {
        "user_id": str(ctx.user.id),
        "channel_id": str(ctx.channel.id),
        "message": reminder_message,
        "reminder_time": reminder_time.isoformat(),
        "set_time": now_utc.isoformat(),
        "recurrence": recurrence,
        "recurrence_time": time_str if recurrence != "none" else None,
        "next_occurrence": None,
        "is_sent": False
    }
    
    status, response_text = await post_data("reminders", payload)
    if status == 201:
        embed = CustomEmbed.success(
            "Reminder Set!",
            f"I'll remind you to: **{reminder_message}**",
            localized_time,
            ctx.user
        )
        recurrence_text = "One-time" if recurrence == "none" else f"Recurring: {recurrence} at {time_str}"
        embed.add_field(name="Recurrence", value=recurrence_text, inline=False)
        await (ctx.response.send_message(embed=embed) if hasattr(ctx, 'response') else ctx.send(embed=embed))
    else:
        print(f"Failed to create reminder. Status: {status}, Response: {response_text}")
        embed = CustomEmbed.error("Failed to Set Reminder", f"Status: {status}. Please try again.")
        await (ctx.response.send_message(embed=embed, ephemeral=True) if hasattr(ctx, 'response') else ctx.send(embed=embed))

async def get_user_timezone(user_id: int, session):
    url = f"{SUPABASE_URL}/user_preferences?user_id=eq.{user_id}"
    async with session.get(url, headers=SUPABASE_HEADERS) as pref_response:
        if pref_response.status == 200:
            preferences = await pref_response.json()
            if preferences and "timezone" in preferences[0]:
                timezone_str = preferences[0]["timezone"]
                if timezone_str:
                    try:
                        hours = int(timezone_str[1:3])
                        minutes = int(timezone_str[4:6]) if len(timezone_str) > 4 else 0
                        sign = -1 if timezone_str[0] == '-' else 1
                        return timezone(timedelta(hours=sign * hours, minutes=sign * minutes))
                    except (ValueError, IndexError) as e:
                        print(f"Invalid timezone format for user {user_id}: {timezone_str}, defaulting to UTC. Error: {e}")
        return timezone.utc

def calculate_next_occurrence(last_time: datetime, recurrence: str, recurrence_time: str) -> datetime:
    now = datetime.now(timezone.utc)
    hour, minute = map(int, recurrence_time.split(":"))
    
    if recurrence == "daily":
        next_time = last_time.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
        while next_time <= now:
            next_time += timedelta(days=1)
    elif recurrence == "weekly":
        next_time = last_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        while next_time <= now:
            next_time += timedelta(days=7)
    elif recurrence == "monthly":
        next_time = last_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if last_time.month == 12:
            next_time = next_time.replace(year=last_time.year + 1, month=1)
        else:
            next_time = next_time.replace(month=last_time.month + 1)
        while next_time <= now:
            if next_time.month == 12:
                next_time = next_time.replace(year=next_time.year + 1, month=1)
            else:
                next_time = next_time.replace(month=next_time.month + 1)
    elif recurrence == "yearly":
        next_time = last_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        next_time = next_time.replace(year=last_time.year + 1)
        while next_time <= now:
            next_time = next_time.replace(year=next_time.year + 1)
    else:
        raise ValueError("Invalid recurrence pattern")
    return next_time

@tasks.loop(seconds=60)
async def check_for_reminders():
    print("Checking for reminders...")
    reminders = await fetch_due_reminders()
    print(f"Fetched reminders: {len(reminders)}")
    
    from bot_setup import bot
    for reminder in reminders:
        user = await bot.fetch_user(int(reminder["user_id"]))
        if user:
            channel = bot.get_channel(int(reminder["channel_id"]))
            if channel:
                await channel.send(f"<@{user.id}>")
                set_time = datetime.fromisoformat(reminder["set_time"])
                embed = CustomEmbed.reminder(
                    user, reminder["message"], datetime.fromisoformat(reminder["reminder_time"]),
                    set_time, channel, reminder["recurrence"], reminder["recurrence_time"]
                )
                view = SnoozeView(reminder["id"])
                await user.send(embed=embed, view=view)
                await channel.send(embed=embed, view=view)
                
                if reminder["recurrence"] != "none":
                    next_occurrence = calculate_next_occurrence(
                        datetime.fromisoformat(reminder["reminder_time"]),
                        reminder["recurrence"],
                        reminder["recurrence_time"]
                    )
                    patch_data_dict = {
                        "is_sent": True,
                        "next_occurrence": next_occurrence.isoformat(),
                        "reminder_time": next_occurrence.isoformat()
                    }
                    status, text = await patch_data("reminders", f"id=eq.{reminder['id']}", patch_data_dict)
                    if status not in (200, 204):
                        print(f"Failed to update recurring reminder {reminder['id']}: Status {status}, Response: {text}")
                    else:
                        print(f"Updated recurring reminder {reminder['id']} with next occurrence: {next_occurrence}")
                else:
                    status, text = await patch_data("reminders", f"id=eq.{reminder['id']}", {"is_sent": True})
                    if status not in (200, 204):
                        print(f"Failed to mark reminder {reminder['id']} as sent: Status {status}, Response: {text}")
                    else:
                        print(f"Marked reminder {reminder['id']} as sent")

@app_commands.command(name="remindme", description="Set a one-time reminder")
@app_commands.describe(
    message="The reminder message",
    days="Days until the reminder",
    hours="Hours until the reminder",
    minutes="Minutes until the reminder",
    seconds="Seconds until the reminder"
)
async def remind_me_slash(interaction: discord.Interaction, message: str, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
    await track_command_usage(str(interaction.user.id), "remindme")
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
    if total_seconds <= 0:
        embed = CustomEmbed.error("Invalid Time Format", "The total time must be greater than zero.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await remind_me_logic(interaction, message, total_seconds)

@app_commands.command(name="remindloop", description="Set a recurring reminder")
@app_commands.describe(
    message="The reminder message",
    recurrence="Recurrence pattern",
    time="Time of day for the reminder (e.g., '07:00' or '19:00')",
    days="Days until the first occurrence (optional)"
)
@app_commands.choices(recurrence=[
    app_commands.Choice(name="Daily", value="daily"),
    app_commands.Choice(name="Weekly", value="weekly"),
    app_commands.Choice(name="Monthly", value="monthly"),
    app_commands.Choice(name="Yearly", value="yearly"),
])
async def remind_loop_slash(interaction: discord.Interaction, message: str, recurrence: str, time: str, days: int = 0):
    await track_command_usage(str(interaction.user.id), "remindloop")
    total_seconds = days * 86400
    await remind_me_logic(interaction, message, total_seconds, recurrence, time)

async def check_reminders_logic(ctx):
    user_id = str(ctx.user.id)
    reminders = await fetch_reminders(user_id)
    embed = CustomEmbed.reminder_list(reminders, active_only=True)
    view = ReminderView(user_id, reminders)
    await (ctx.response.send_message(embed=embed, view=view) if hasattr(ctx, 'response') else ctx.send(embed=embed, view=view))

@app_commands.command(name="checkreminders", description="Check your reminders")
async def check_reminders_slash(interaction: discord.Interaction):
    await track_command_usage(str(interaction.user.id), "checkreminders")
    await check_reminders_logic(interaction)

@app_commands.command(name="cancelreminder", description="Cancel a specific reminder by ID")
@app_commands.describe(id="The ID of the reminder to cancel (see /checkreminders)")
async def cancel_reminder(interaction: discord.Interaction, id: int):
    await track_command_usage(str(interaction.user.id), "cancelreminder")
    user_id = str(interaction.user.id)
    
    # Check if the reminder exists and belongs to the user
    reminders = await fetch_reminders(user_id, active_only=True)
    reminder = next((r for r in reminders if r["id"] == id), None)
    
    if not reminder:
        embed = discord.Embed(
            title="❌ Reminder Not Found",
            description=f"No active reminder with ID `{id}` found. Use `/checkreminders` to see your reminders.",
            color=discord.Color.from_rgb(255, 0, 0)  # Red like JubJub's eyes
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_footer(text="JubJub’s confused!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Delete the reminder
    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/reminders?id=eq.{id}&user_id=eq.{user_id}"
        async with session.delete(url, headers=SUPABASE_HEADERS) as response:
            if response.status in (200, 204):
                embed = discord.Embed(
                    title="🗑️ Reminder Canceled!",
                    description=f"Reminder `{id}` has been canceled: **{reminder['message']}**",
                    color=discord.Color.from_rgb(255, 0, 0)  # Red like JubJub's eyes
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
                embed.set_footer(text="JubJub’s got it!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
                embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Failed to Cancel",
                    description="Something went wrong while canceling the reminder. Try again later.",
                    color=discord.Color.from_rgb(255, 0, 0)
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
                embed.set_footer(text="JubJub’s sorry!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
                embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
                await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="snooze", description="Snooze a reminder by ID")
@app_commands.describe(
    id="The ID of the reminder to snooze (see /checkreminders)",
    minutes="How many minutes to snooze (default 10)"
)
async def snooze_reminder(interaction: discord.Interaction, id: int, minutes: int = 10):
    await track_command_usage(str(interaction.user.id), "snooze")
    user_id = str(interaction.user.id)
    
    # Validate minutes
    if minutes <= 0:
        embed = discord.Embed(
            title="❌ Invalid Snooze Time",
            description="Snooze time must be greater than 0 minutes.",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_footer(text="JubJub’s confused!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check if the reminder exists and belongs to the user
    reminders = await fetch_reminders(user_id, active_only=True)
    reminder = next((r for r in reminders if r["id"] == id), None)
    
    if not reminder:
        embed = discord.Embed(
            title="❌ Reminder Not Found",
            description=f"No active reminder with ID `{id}` found. Use `/checkreminders` to see your reminders.",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_footer(text="JubJub’s confused!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Update the reminder time
    current_time = datetime.fromisoformat(reminder["reminder_time"])
    new_time = current_time + timedelta(minutes=minutes)
    patch_data_dict = {
        "reminder_time": new_time.isoformat(),
        "is_sent": False  # Reset is_sent so it triggers again
    }
    status, text = await patch_data("reminders", f"id=eq.{id}", patch_data_dict)
    
    if status in (200, 204):
        embed = discord.Embed(
            title="💤 Reminder Snoozed!",
            description=f"Reminder `{id}` has been snoozed for {minutes} minutes: **{reminder['message']}**\nNew time: {new_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            color=discord.Color.from_rgb(255, 255, 0)  # Yellow like JubJub's pupils
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_footer(text="JubJub’s snoozing!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Failed to Snooze",
            description="Something went wrong while snoozing the reminder. Try again later.",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_footer(text="JubJub’s sorry!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
        embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReminderView(discord.ui.View):
    def __init__(self, user_id, reminders):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.reminders = reminders
        self.active_only = True
        self.current_page = 0
        self.max_per_page = 10
    
    def update_buttons(self):
        total_pages = (len(self.reminders) + self.max_per_page - 1) // self.max_per_page
        self.children[2].disabled = self.current_page == 0
        self.children[3].disabled = self.current_page >= total_pages - 1
    
    @discord.ui.button(label="Show Active", style=discord.ButtonStyle.success, custom_id="show_active", emoji="✅")
    async def show_active(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        await interaction.response.defer()
        self.active_only = True
        self.reminders = await fetch_reminders(self.user_id, active_only=True)
        self.current_page = 0
        embed = CustomEmbed.reminder_list(self.reminders, self.active_only, self.current_page * self.max_per_page, self.max_per_page)
        self.update_buttons()
        await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="Show Archived", style=discord.ButtonStyle.secondary, custom_id="show_archived", emoji="📁")
    async def show_archived(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        await interaction.response.defer()
        self.active_only = False
        self.reminders = await fetch_reminders(self.user_id, active_only=False)
        self.current_page = 0
        embed = CustomEmbed.reminder_list(self.reminders, self.active_only, self.current_page * self.max_per_page, self.max_per_page)
        self.update_buttons()
        await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray, custom_id="prev", emoji="⬅️")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            embed = CustomEmbed.reminder_list(self.reminders, self.active_only, self.current_page * self.max_per_page, self.max_per_page)
            self.update_buttons()
            await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray, custom_id="next", emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        await interaction.response.defer()
        total_pages = (len(self.reminders) + self.max_per_page - 1) // self.max_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = CustomEmbed.reminder_list(self.reminders, self.active_only, self.current_page * self.max_per_page, self.max_per_page)
            self.update_buttons()
            await interaction.message.edit(embed=embed, view=self)

class SnoozeView(discord.ui.View):
    def __init__(self, reminder_id):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.reminder_id = reminder_id

    @discord.ui.button(label="Snooze 5m", style=discord.ButtonStyle.secondary, custom_id="snooze_5")
    async def snooze_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.snooze(interaction, 5)

    @discord.ui.button(label="Snooze 10m", style=discord.ButtonStyle.secondary, custom_id="snooze_10")
    async def snooze_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.snooze(interaction, 10)

    @discord.ui.button(label="Snooze 30m", style=discord.ButtonStyle.secondary, custom_id="snooze_30")
    async def snooze_30(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.snooze(interaction, 30)

    async def snooze(self, interaction: discord.Interaction, minutes: int):
        user_id = str(interaction.user.id)
        
        # Check if the reminder exists and belongs to the user
        reminders = await fetch_reminders(user_id, active_only=True)
        reminder = next((r for r in reminders if r["id"] == self.reminder_id), None)
        
        if not reminder or reminder["user_id"] != user_id:
            await interaction.response.send_message("This reminder isn’t yours or doesn’t exist!", ephemeral=True)
            return
        
        # Update the reminder time
        current_time = datetime.fromisoformat(reminder["reminder_time"])
        new_time = current_time + timedelta(minutes=minutes)
        patch_data_dict = {
            "reminder_time": new_time.isoformat(),
            "is_sent": False
        }
        status, text = await patch_data("reminders", f"id=eq.{self.reminder_id}", patch_data_dict)
        
        if status in (200, 204):
            embed = discord.Embed(
                title="💤 Reminder Snoozed!",
                description=f"Reminder `{self.reminder_id}` has been snoozed for {minutes} minutes: **{reminder['message']}**\nNew time: {new_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                color=discord.Color.from_rgb(255, 255, 0)  # Yellow like JubJub's pupils
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_footer(text="JubJub’s snoozing!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
            await interaction.response.send_message(embed=embed)
            # Disable the buttons after snoozing
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        else:
            embed = discord.Embed(
                title="❌ Failed to Snooze",
                description="Something went wrong while snoozing the reminder. Try again later.",
                color=discord.Color.from_rgb(255, 0, 0)
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_footer(text="JubJub’s sorry!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
            await interaction.response.send_message(embed=embed, ephemeral=True)