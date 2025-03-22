# bot_setup.py
# Bot initialization and startup logic

import discord
from discord.ext import commands
from config import BOT_TOKEN
from reminders import check_for_reminders

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    check_for_reminders.start()
    print("Bot is ready!")