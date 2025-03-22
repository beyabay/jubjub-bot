# database.py
# Supabase API interaction helpers

import aiohttp
from config import SUPABASE_URL, SUPABASE_HEADERS
from urllib.parse import quote
from datetime import datetime, timezone  # Add this line

async def fetch_data(endpoint: str, filters: str = ""):
    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/{endpoint}{filters}"
        async with session.get(url, headers=SUPABASE_HEADERS) as response:
            if response.status == 200:
                return await response.json()
            print(f"Failed to fetch {endpoint}: {response.status}")
            return []

async def post_data(endpoint: str, data: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/{endpoint}"
        async with session.post(url, headers=SUPABASE_HEADERS, json=data) as response:
            return response.status, await response.text()

async def patch_data(endpoint: str, filters: str, data: dict):
    async with aiohttp.ClientSession() as session:
        url = f"{SUPABASE_URL}/{endpoint}?{filters}"
        async with session.patch(url, headers=SUPABASE_HEADERS, json=data) as response:
            return response.status, await response.text()

async def fetch_gifs():
    return await fetch_data("gifs", "?select=name,link,category")

async def fetch_reminders(user_id: str, active_only: bool = True):
    is_sent_filter = "is_sent=eq.false" if active_only else "is_sent=eq.true"
    filters = f"?user_id=eq.{user_id}&{is_sent_filter}&order=reminder_time.asc"
    return await fetch_data("reminders", filters)

async def fetch_due_reminders():
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00")
    encoded_time = quote(current_time)
    filters = f"?is_sent=eq.false&reminder_time=lt.{encoded_time}"
    return await fetch_data("reminders", filters)