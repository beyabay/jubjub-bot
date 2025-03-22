# utility_commands.py
# Utility commands like ping and stats

import discord
from discord import app_commands
import time
import aiohttp
from embeds import CustomEmbed
from database import fetch_data
from config import SUPABASE_URL, SUPABASE_HEADERS

# Helper to track command usage in Supabase
async def track_command_usage(user_id: str, command_name: str):
    async with aiohttp.ClientSession() as session:
        # Check if entry exists
        url = f"{SUPABASE_URL}/command_usage?user_id=eq.{user_id}&command_name=eq.{command_name}"
        async with session.get(url, headers=SUPABASE_HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    # Entry exists, increment usage_count
                    entry = data[0]
                    patch_url = f"{SUPABASE_URL}/command_usage?id=eq.{entry['id']}"
                    async with session.patch(patch_url, headers=SUPABASE_HEADERS, json={"usage_count": entry["usage_count"] + 1}) as patch_response:
                        if patch_response.status not in (200, 204):
                            print(f"Failed to update command usage: {await patch_response.text()}")
                else:
                    # No entry, create one
                    post_url = f"{SUPABASE_URL}/command_usage"
                    payload = {"user_id": user_id, "command_name": command_name, "usage_count": 1}
                    async with session.post(post_url, headers=SUPABASE_HEADERS, json=payload) as post_response:
                        if post_response.status != 201:
                            print(f"Failed to create command usage: {await post_response.text()}")

@app_commands.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    # Track command usage
    await track_command_usage(str(interaction.user.id), "ping")

    # Bot latency
    bot_latency = round(interaction.client.latency * 1000)  # Convert to milliseconds

    # Supabase latency
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/command_usage?limit=1"  # Small query to test latency
        async with session.get(url, headers=SUPABASE_HEADERS) as response:
            supabase_latency = round((time.time() - start_time) * 1000)  # Time in milliseconds

    # Create embed with JubJub's colors
    embed = discord.Embed(
        title="🏓 Pong!",
        description="Here’s how fast I’m vibing!",
        color=discord.Color.from_rgb(255, 0, 0)  # Red like JubJub's eyes
    )
    embed.add_field(name="Bot Latency", value=f"**{bot_latency}ms**", inline=True)
    embed.add_field(name="Supabase Latency", value=f"**{supabase_latency}ms**", inline=True)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")  # JubJub's PFP
    embed.set_footer(text="JubJub’s got your back!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
    embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")

    await interaction.response.send_message(embed=embed)

@app_commands.command(name="stats", description="Check bot usage stats")
async def stats(interaction: discord.Interaction):
    # Track command usage
    await track_command_usage(str(interaction.user.id), "stats")

    # Fetch global stats
    global_stats = await fetch_data("command_usage", "")
    total_commands = sum(entry["usage_count"] for entry in global_stats)
    
    # Break down by command
    command_breakdown = {}
    for entry in global_stats:
        cmd = entry["command_name"]
        command_breakdown[cmd] = command_breakdown.get(cmd, 0) + entry["usage_count"]

    # Fetch user stats
    user_stats = await fetch_data("command_usage", f"?user_id=eq.{interaction.user.id}")
    user_total = sum(entry["usage_count"] for entry in user_stats)
    user_breakdown = {entry["command_name"]: entry["usage_count"] for entry in user_stats}

    # Create embed with JubJub's colors
    embed = discord.Embed(
        title="📊 JubJub’s Stats!",
        description="Check out how much action I’ve been getting! 🖤🤍❤️💛",
        color=discord.Color.from_rgb(255, 255, 255)  # White for JubJub's hair
    )
    # Global stats
    embed.add_field(
        name="Global Usage",
        value=f"**Total Commands Used:** {total_commands}\n" +
              "\n".join(f"**{cmd.capitalize()}:** {count}" for cmd, count in command_breakdown.items()),
        inline=False
    )
    # User stats
    user_stats_text = f"**Your Total Commands:** {user_total}\n" + \
                      "\n".join(f"**{cmd.capitalize()}:** {count}" for cmd, count in user_breakdown.items()) \
                      if user_breakdown else "You haven’t used any commands yet!"
    embed.add_field(name=f"{interaction.user.name}’s Stats", value=user_stats_text, inline=False)
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
    embed.set_footer(text="JubJub’s keeping score!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
    embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")

    await interaction.response.send_message(embed=embed)