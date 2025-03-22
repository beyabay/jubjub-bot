# main.py
# Entry point for the bot

import discord
from bot_setup import bot
from reminders import remind_me_logic, check_reminders_logic, remind_me_slash, remind_loop_slash, check_reminders_slash, cancel_reminder, snooze_reminder
from gif_commands import send_gif, gif_add
from utility_commands import ping, stats
from fun_commands import roast  # Add this
import re
from embeds import CustomEmbed
from config import BOT_TOKEN

# Register slash commands
bot.tree.add_command(remind_me_slash)
bot.tree.add_command(remind_loop_slash)
bot.tree.add_command(check_reminders_slash)
bot.tree.add_command(send_gif)
bot.tree.add_command(gif_add)
bot.tree.add_command(ping)
bot.tree.add_command(stats)
bot.tree.add_command(cancel_reminder)
bot.tree.add_command(snooze_reminder)
bot.tree.add_command(roast)  # Add this

@bot.command(name="remindme")
async def remind_me_prefix(ctx, *, reminder_input: str):
    time_pattern = re.compile(r"(\d+)\s*(d(ays?)?|h(ours?)?|m(in(utes?)?|ins?)?|s(ec(onds?)?|ecs?)?)\b", re.IGNORECASE)
    matches = list(time_pattern.finditer(reminder_input))
    
    if not matches:
        embed = CustomEmbed.error("Invalid Time Format", "Use something like `14m`, `1h30m`, `2d5s`, or `10s`.")
        await ctx.send(embed=embed)
        return
    
    total_seconds = 0
    for match in matches:
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("d"):
            total_seconds += value * 86400
        elif unit.startswith("h"):
            total_seconds += value * 3600
        elif unit.startswith("m"):
            total_seconds += value * 60
        elif unit.startswith("s"):
            total_seconds += value
    
    if total_seconds <= 0:
        embed = CustomEmbed.error("Invalid Time Format", "Use something like `14m`, `1h30m`, `2d5s`, or `10s`.")
        await ctx.send(embed=embed)
        return
    
    last_match = matches[-1]
    end_index = last_match.end()
    reminder_message = reminder_input[end_index:].strip() or "for no reason"
    await remind_me_logic(ctx, reminder_message, total_seconds)

@bot.command(name="checkreminders")
async def check_reminders_prefix(ctx):
    await check_reminders_logic(ctx)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)