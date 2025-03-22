# config.py
# Central place for all configuration settings

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Convert to int since it's an ID
JUBJUB_BANNER = os.getenv("JUBJUB_BANNER")
JUBJUB_PFP = os.getenv("JUBJUB_PFP")

# Headers for Supabase requests
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}