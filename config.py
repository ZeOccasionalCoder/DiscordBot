import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN in .env")

if not GUILD_ID:
    raise ValueError("Missing GUILD_ID in .env")

GUILD_ID = int(GUILD_ID)
