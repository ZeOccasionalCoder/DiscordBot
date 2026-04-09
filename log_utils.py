import os
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "roll_log.csv")


def ensure_csv_headers() -> None:
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "guild",
                "channel",
                "user",
                "discord_id",
                "command",
                "result",
            ])


def log_roll(command_name: str, result: str, interaction) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guild_name = interaction.guild.name if interaction.guild else "DM"
    channel_name = getattr(interaction.channel, "name", "unknown-channel")
    username = str(interaction.user)
    user_id = interaction.user.id

    ensure_csv_headers()

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            guild_name,
            channel_name,
            username,
            user_id,
            command_name,
            result,
        ])
