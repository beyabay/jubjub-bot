# gif_commands.py
# GIF-related commands

import discord
from discord import app_commands
from database import fetch_gifs
from config import OWNER_ID
from utility_commands import track_command_usage

@app_commands.command(name="gif", description="Send a GIF")
@app_commands.describe(gif_name="The name of the GIF to send")
async def send_gif(interaction: discord.Interaction, gif_name: str):
    await track_command_usage(str(interaction.user.id), "gif")
    gifs = await fetch_gifs()
    gif_link = next((g["link"] for g in gifs if g["name"].lower() == gif_name.lower()), None)
    if gif_link:
        await interaction.response.send_message(gif_link)
    else:
        await interaction.response.send_message("GIF not found!", ephemeral=True)

@send_gif.autocomplete("gif_name")
async def gif_autocomplete(interaction: discord.Interaction, current: str):
    gifs = await fetch_gifs()
    choices = [app_commands.Choice(name=gif["name"], value=gif["name"]) for gif in gifs]
    return [choice for choice in choices if current.lower() in choice.name.lower()]

@app_commands.command(name="gif_add", description="Add a new GIF (Owner only)")
@app_commands.describe(name="GIF name", link="GIF URL", category="GIF category")
async def gif_add(interaction: discord.Interaction, name: str, link: str, category: str = "general"):
    await track_command_usage(str(interaction.user.id), "gif_add")
    from database import post_data
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    status, _ = await post_data("gifs", {"name": name, "link": link, "category": category})
    if status == 201:
        await interaction.response.send_message(f"GIF '{name}' added successfully!", ephemeral=True)
    else:
        await interaction.response.send_message(f"Failed to add GIF: {status}", ephemeral=True)