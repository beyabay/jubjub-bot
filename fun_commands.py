# fun_commands.py
# Fun commands like roast

import discord
from discord import app_commands
import random
from utility_commands import track_command_usage

# List of lighthearted roasts (safe and fun)
ROASTS = [
    "{user}, you’re so slow, JubJub could finish a Chaos Trial before you even start!",
    "{user}, your vibes are so off, even JubJub’s chaos can’t fix you!",
    "{user}, you’re like a GIF that won’t load—JubJub’s disappointed!",
    "{user}, you call that a meme? JubJub’s seen better from a bot!",
    "{user}, you’re so quiet, JubJub thought you were a ghost in the server!",
    "{user}, your energy’s so low, JubJub’s red eyes are brighter than you!",
    "{user}, you’re so predictable, JubJub could roast you in her sleep!",
    "{user}, you’re trying so hard, but JubJub’s chaos still outshines you!",
    "{user}, you’re like a reminder that never triggers—JubJub’s bored!",
    "{user}, your chaos level is so low, JubJub’s yellow pupils are judging you!"
]

# Cooldown tracking (in-memory for now, could move to Supabase later)
roast_cooldowns = {}

@app_commands.command(name="roast", description="Let JubJub roast someone (or yourself)!")
@app_commands.describe(user="Who to roast (leave blank to roast yourself)")
async def roast(interaction: discord.Interaction, user: discord.User = None):
    await track_command_usage(str(interaction.user.id), "roast")

    # If no user is specified, roast the caller
    target = user if user else interaction.user

    # Check cooldown (5 minutes per user)
    user_id = str(interaction.user.id)
    current_time = discord.utils.utcnow().timestamp()
    if user_id in roast_cooldowns:
        last_used = roast_cooldowns[user_id]
        cooldown_seconds = 300  # 5 minutes
        time_left = cooldown_seconds - (current_time - last_used)
        if time_left > 0:
            embed = discord.Embed(
                title="⏳ Slow Down, Chaos Gremlin!",
                description=f"JubJub needs a break! Wait {int(time_left)} seconds before roasting again.",
                color=discord.Color.from_rgb(255, 0, 0)  # Red like JubJub's eyes
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_footer(text="JubJub’s cooling off!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
            embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    # Update cooldown
    roast_cooldowns[user_id] = current_time

    # Pick a random roast and format it
    roast_text = random.choice(ROASTS).format(user=f"<@{target.id}>")

    # Create the embed
    embed = discord.Embed(
        title="🔥 JubJub’s Roast Time!",
        description=roast_text,
        color=discord.Color.from_rgb(255, 0, 0)  # Red like JubJub's eyes
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
    embed.set_footer(text="JubJub’s roasting time!", icon_url="https://cdn.discordapp.com/attachments/798659460276158527/1352802990536396893/JubJubPFP.png")
    embed.set_image(url="https://cdn.discordapp.com/attachments/798659460276158527/1352803085373673582/JubJubBanner.jpg")

    await interaction.response.send_message(embed=embed)