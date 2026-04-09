import os
import importlib.util
import discord
from discord import app_commands

from config import TOKEN, GUILD_ID
from log_utils import ensure_csv_headers

RELOAD_ROLE_ID = 935730359360978974


class MyBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        synced = await self.reload_all_commands()
        print(f"Synced {synced} command(s) to guild {GUILD_ID}")

    def register_core_commands(self) -> None:
        @self.tree.command(name="reloadplugins", description="Reload all bot plugins")
        async def reloadplugins(interaction: discord.Interaction) -> None:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            member = interaction.user
            member_roles = getattr(member, "roles", [])
            has_required_role = any(role.id == RELOAD_ROLE_ID for role in member_roles)

            if not has_required_role:
                await interaction.response.send_message(
                    "You do not have permission to use this command.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                synced = await self.reload_all_commands()
                await interaction.followup.send(
                    f"Reloaded plugins successfully. Synced {synced} command(s).",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(
                    f"Failed to reload plugins: {e}",
                    ephemeral=True,
                )

    def load_plugins(self) -> None:
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

        if not os.path.exists(plugins_dir):
            print(f"Plugins folder not found: {plugins_dir}")
            return

        for filename in os.listdir(plugins_dir):
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_"):
                continue

            module_name = filename[:-3]
            file_path = os.path.join(plugins_dir, filename)

            print(f"Loading plugin: {file_path}")

            spec = importlib.util.spec_from_file_location(f"plugins.{module_name}", file_path)
            if spec is None or spec.loader is None:
                print(f"Skipping invalid plugin: {filename}")
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "setup"):
                module.setup(self.tree)
                print(f"Loaded plugin: {filename}")
            else:
                print(f"Skipped {filename} (no setup function found)")

    async def reload_all_commands(self) -> int:
        guild = discord.Object(id=GUILD_ID)

        self.tree.clear_commands(guild=None)
        self.tree.clear_commands(guild=guild)

        self.register_core_commands()
        self.load_plugins()

        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        return len(synced)


bot = MyBot()


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is online.")
    ensure_csv_headers()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    print(f"Command error: {error}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                "Something went wrong running that command.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Something went wrong running that command.",
                ephemeral=True,
            )
    except Exception as send_error:
        print(f"Failed to send error message: {send_error}")


try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Startup error: {e}")
    input("Press Enter to close...")
