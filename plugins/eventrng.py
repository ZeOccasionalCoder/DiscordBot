import random
from datetime import datetime

import discord
from discord import app_commands
from log_utils import log_roll

LIST_ONE = [
    "#1 Adult Tecu Salamander",
    "#2 Donate random number to prize pool between 1gp & 10m gp (team can split cost)",
    "#3 Get first 5 COX completions (reroll if not possible verified by admins/opposing team)",
    "#4 Furball CA - must be a first time no repeats. (reroll if not possible verified by admins/opposing team)",
    "#5 Get first 5 COX CM completions(reroll if not possible verified by admins/opposing team)",
    "#6 Complete Any Moon's Set",
    "#7 Precise Positioning CA, Must be first time (reroll if not possible verified by admins/opposing team)",
    "#8 Drake's Claw or Tooth",
    "#9 Get one of every Superior accessible in Kourend (Banshee, Cockatrice, Bloodveld, Jelly, Spectre, Wyrm, Dust Devil, Custodian, Nechryarch, Guardian Drake, Abyssal Demon & Hydra.)",
    "#10 Mask of Ranul",
    "#11 Long Bone Drop",
    "#12 1000 Red Spiders Eggs from Sarachnis",
    "#13 Pendant of the Ates",
    "#14 Obtain Huasca Seeds",
    "#15 Dragon Drop (Sword, Harpoon, Knife or Thrownaxe) from any Kourend Source.",
    "#16 Barrel of Cum Drop or Forgotten Lockbox",
    "#17 Blue or Orange Egg Sac (keys must be obtained manually & not pre-stacked)",
    "#18 Snape Grass Seed from Farming Contracts",
    "#19 Abyssal Whip Drop",
    "#20 5x Full Skotizo Totems (any 3 pieces don't need to be physically put together 15 totem drops in total)",
    "#21 4x Moss Giant Keys (can be kept for entire bingo ;) )",
    "#22 10x Hill Giant Keys (can be kept for entire bingo ;) )",
    "#23 Dust Battlestaff Drop",
    "#24 Get 1 of every herb drop",
    "#25 Earn 10m collectively as a team at Brutal Black Dragons",
    "#26 Perfect Hueycoatl CA with teammates only",
    "#27 Precise Positioning CA (Skotizo)",
]

LIST_TWO = [
    "#1 3x Hydra ring drops (can be from slayer mob or boss)",
    "#2 Earn 50m collectively as a team at Chambers of Xeric",
    "#3 Obtain a Yama Contract, from a Dossier and complete it.",
    "#4 Hydra \"No Pressure\" CA",
    "#5 Not Solo COX GM time (Trio or 5)",
    "#6 Not Solo Cox CM GM Time (Trio or 5)",
    "#7 Perfect Footwork CA",
    "#8 Colosseum GM Time CA",
    "#9 Slow Dancing in the Sand CA",
    "#10 Perfect Olm Trio CA",
    "#11 Get a first Colosseum Completion (reroll if not possible verified by admins/opposing team).",
    "#12 Kill Awakened Vardorvis",
    "#13 Axe Enthusiast CA (reroll if not possible verified by admins/opposing team).",
    "#14 Yama GM time 2x teammates, must be first time completion (reroll if not possible verified by admins/opposing team).",
    "#15 Donate random number to prize pool between 1 & 20m",
    "#16 5x Awakeners Orbs",
    "#17 100x Oathplate Shards",
    "#18 Curved Bone Drop",
    "#19 Reinforcements CA First time (reroll if not possible verified by admins/opposing team).",
    "#20 Kill the Hueycoatl in 2:30 with three or fewer players. (gm time)",
    "#21 Get a Quiver",
]

LIST_THREE = [
    "Double Task - must have at least 1 tile gap from another team; may not be usable later if every tile gets filled. Cannot be used to directly impact someone's progress on a specific tile. Potent early, weak late.",
    "Lock Tile - Tile cannot be flipped",
    "Unlock Tile - Unlock a locked tile; once a tile has been unlocked it cannot be locked again",
    "Half Task - Usable on a half-able task only",
    "Spyglass - Pre-roll a treasure to see what you'll get if that task is completed. The treasure is available to all teams and can be competed for.",
    "Loaded Dice - Pick your task on a RNG tile. Consumed upon use",
    "Re-Rolling Dice - Re-roll a RNG Tile (random)",
    "Scientific Calculator - Reset a multiplier on any task. Must be used prior to committing to the task and announcement is public that it's been negated, turning it into a race to reclaim.",
    "Golden Pogo Stick - Provides ability to leap over a task, providing access to tiles up to 2 tiles away. This is consumed immediately after your team completes any task; it cannot be held onto.",
    "Neutralize 1 tile - Make any 1 tile neutral. Must be a tile your team is adjacent to and cannot be used on the last day of the week.",
    "+1 bonus point",
]

ROLL_MAP = {
    "regular": {
        "display_name": "REGULAR RNG ROLL",
        "log_name": "regular_rng_roll",
        "list": LIST_ONE,
        "color": discord.Color.blue(),
        "emoji": "🎲",
        "image_url": "https://i.imgur.com/VFnf2QA.png",
    },
    "challenge": {
        "display_name": "CHALLENGE RNG ROLL",
        "log_name": "challenge_rng_roll",
        "list": LIST_TWO,
        "color": discord.Color.red(),
        "emoji": "⚔️",
        "image_url": "https://i.imgur.com/Hlbrs2f.png",
    },
    "treasure": {
        "display_name": "TREASURE ROLL",
        "log_name": "treasure_roll",
        "list": LIST_THREE,
        "color": discord.Color.gold(),
        "emoji": "💰",
        "image_url": "https://i.imgur.com/7FGeJAl.png",
    },
}

SEA_WORTHY_LOGO_URL = "https://i.imgur.com/hVTcL4l.png"


def format_task(task: str) -> tuple[str, str | None]:
    task = task.strip()

    if " - " in task:
        left, right = task.split(" - ", 1)
        return left.strip(), right.strip()

    if ". " in task:
        left, right = task.split(". ", 1)
        return (left.strip() + "."), right.strip()

    return task, None


def get_local_timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")


def build_footer_text() -> str:
    return f"{get_local_timestamp()} | *Sea Worthy*"


def build_roll_embed(
    interaction: discord.Interaction,
    display_name: str,
    emoji: str,
    color: discord.Color,
    task: str,
    image_url: str | None = None,
) -> discord.Embed:
    title_text, details = format_task(task)

    embed = discord.Embed(
        title=f"{emoji} {display_name} {emoji}",
        color=color,
    )

    embed.set_author(
        name="Sea Worthy",
        icon_url=SEA_WORTHY_LOGO_URL,
    )

    if image_url:
        embed.set_thumbnail(url=image_url)

    embed.add_field(
        name="ROLL TYPE",
        value=f"## {display_name}",
        inline=False,
    )

    embed.add_field(
        name="ROLL RESULT",
        value=f"**{title_text}**",
        inline=False,
    )

    if details:
        embed.add_field(
            name="DETAILS",
            value=f"**{details}**",
            inline=False,
        )

    embed.set_footer(
        text=build_footer_text(),
        icon_url=SEA_WORTHY_LOGO_URL,
    )

    return embed


def setup(tree):
    @tree.command(name="eventrng", description="Roll from an event list")
    @app_commands.describe(option="Choose which roll table to use")
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Regular RNG Roll", value="regular"),
            app_commands.Choice(name="Challenge RNG Roll", value="challenge"),
            app_commands.Choice(name="Treasure Roll", value="treasure"),
        ]
    )
    async def eventrng(
        interaction: discord.Interaction,
        option: app_commands.Choice[str],
    ) -> None:
        await interaction.response.defer()

        roll_config = ROLL_MAP[option.value]
        display_name = roll_config["display_name"]
        log_name = roll_config["log_name"]
        selected_list = roll_config["list"]
        color = roll_config["color"]
        emoji = roll_config["emoji"]
        image_url = roll_config.get("image_url")

        if not selected_list:
            empty_embed = discord.Embed(
                title=f"{emoji} {display_name} {emoji}",
                description="This roll table is currently empty.",
                color=discord.Color.dark_grey(),
            )

            empty_embed.set_author(
                name="Sea Worthy",
                icon_url=SEA_WORTHY_LOGO_URL,
            )

            if image_url:
                empty_embed.set_thumbnail(url=image_url)

            empty_embed.set_footer(
                text=build_footer_text(),
                icon_url=SEA_WORTHY_LOGO_URL,
            )

            await interaction.followup.send(
                content=f"{interaction.user.mention} here is your roll",
                embed=empty_embed,
            )
            return

        choice = random.choice(selected_list)
        log_roll(log_name, choice, interaction)

        embed = build_roll_embed(
            interaction=interaction,
            display_name=display_name,
            emoji=emoji,
            color=color,
            task=choice,
            image_url=image_url,
        )

        await interaction.followup.send(
            content=f"{interaction.user.mention} here is your roll",
            embed=embed,
        )
