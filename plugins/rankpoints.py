import csv
import os
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

STAFF_ROLE_IDS = [
    935730359360978974,
    841368007384891392,
    846454946148909056,
    841802308387471390,
    841801938735202334,
]

SEA_WORTHY_LOGO_URL = "https://i.imgur.com/hVTcL4l.png"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TOTALS_FILE = os.path.join(DATA_DIR, "rank_points_totals.csv")
LEDGER_FILE = os.path.join(DATA_DIR, "rank_points_ledger.csv")
MEMBER_LEFT_FILE = os.path.join(DATA_DIR, "rank_points_member_left.csv")


def now_dt() -> datetime:
    return datetime.now().astimezone()


def now_text() -> str:
    return now_dt().strftime("%Y-%m-%d %I:%M %p %Z")


def ensure_data_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(TOTALS_FILE):
        with open(TOTALS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "member_discord_nickname",
                "member_discord_id",
                "total_points",
                "counted_split_value",
                "total_split_value",
                "last_updated",
                "last_reason",
            ])

    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "action",
                "delta_points",
                "member_discord_nickname",
                "member_discord_id",
                "performed_by_nickname",
                "performed_by_id",
                "reason",
                "guild_name",
                "channel_name",
            ])

    if not os.path.exists(MEMBER_LEFT_FILE):
        with open(MEMBER_LEFT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "left_timestamp",
                "member_discord_nickname",
                "member_discord_id",
                "total_points",
                "counted_split_value",
                "total_split_value",
                "last_updated",
                "last_reason",
                "removal_source",
            ])


def has_staff_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)


def display_name_for_member(member: discord.Member) -> str:
    return member.display_name or member.name


def action_to_delta(action: str, points: int) -> int:
    return points if action == "add" else -points


def action_title(action: str) -> str:
    return "Points Added" if action == "add" else "Points Subtracted"


def action_color(action: str) -> discord.Color:
    return discord.Color.green() if action == "add" else discord.Color.red()


def build_branded_embed(
    title: str,
    color: discord.Color,
    description: Optional[str] = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=now_dt(),
    )
    embed.set_author(name="Sea Worthy", icon_url=SEA_WORTHY_LOGO_URL)
    embed.set_thumbnail(url=SEA_WORTHY_LOGO_URL)
    embed.set_footer(text="Sea Worthy", icon_url=SEA_WORTHY_LOGO_URL)
    return embed


def load_totals() -> dict[str, dict]:
    ensure_data_files()
    totals: dict[str, dict] = {}

    with open(TOTALS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            member_id = str(row["member_discord_id"]).strip()
            totals[member_id] = {
                "member_discord_nickname": row.get("member_discord_nickname", ""),
                "member_discord_id": member_id,
                "total_points": int(float(row.get("total_points", 0) or 0)),
                "counted_split_value": row.get("counted_split_value", "0"),
                "total_split_value": row.get("total_split_value", "0"),
                "last_updated": row.get("last_updated", ""),
                "last_reason": row.get("last_reason", ""),
            }

    return totals


def save_totals(totals: dict[str, dict]) -> None:
    ensure_data_files()

    rows = sorted(
        totals.values(),
        key=lambda x: (-int(x["total_points"]), x["member_discord_nickname"].lower()),
    )

    with open(TOTALS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "member_discord_nickname",
            "member_discord_id",
            "total_points",
            "counted_split_value",
            "total_split_value",
            "last_updated",
            "last_reason",
        ])

        for row in rows:
            writer.writerow([
                row["member_discord_nickname"],
                row["member_discord_id"],
                row["total_points"],
                row["counted_split_value"],
                row["total_split_value"],
                row["last_updated"],
                row["last_reason"],
            ])


def append_ledger_row(
    action: str,
    delta_points: int,
    target_member_name: str,
    target_member_id: int,
    performer_name: str,
    performer_id: int,
    reason: str,
    guild_name: str,
    channel_name: str,
) -> None:
    ensure_data_files()

    with open(LEDGER_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            now_dt().strftime("%Y-%m-%d %H:%M:%S %Z"),
            action,
            delta_points,
            target_member_name,
            target_member_id,
            performer_name,
            performer_id,
            reason,
            guild_name,
            channel_name,
        ])


def append_member_left_row(row: dict, removal_source: str) -> None:
    ensure_data_files()

    with open(MEMBER_LEFT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            now_text(),
            row["member_discord_nickname"],
            row["member_discord_id"],
            row["total_points"],
            row["counted_split_value"],
            row["total_split_value"],
            row["last_updated"],
            row["last_reason"],
            removal_source,
        ])


def apply_points_change(member: discord.Member, delta_points: int, reason: str) -> int:
    totals = load_totals()
    member_id = str(member.id)

    if member_id not in totals:
        totals[member_id] = {
            "member_discord_nickname": display_name_for_member(member),
            "member_discord_id": member_id,
            "total_points": 0,
            "counted_split_value": "0",
            "total_split_value": "0",
            "last_updated": now_text(),
            "last_reason": "",
        }

    totals[member_id]["member_discord_nickname"] = display_name_for_member(member)
    totals[member_id]["total_points"] = int(totals[member_id]["total_points"]) + delta_points
    totals[member_id]["last_updated"] = now_text()
    totals[member_id]["last_reason"] = reason

    save_totals(totals)
    return int(totals[member_id]["total_points"])


def batch_apply_points_change(
    members: list[discord.Member],
    delta_points: int,
    reason: str,
) -> dict[int, int]:
    totals = load_totals()
    updated_totals_by_member_id: dict[int, int] = {}
    timestamp_text = now_text()
    seen_member_ids: set[int] = set()

    for member in members:
        if member.id in seen_member_ids:
            continue
        seen_member_ids.add(member.id)

        member_id = str(member.id)

        if member_id not in totals:
            totals[member_id] = {
                "member_discord_nickname": display_name_for_member(member),
                "member_discord_id": member_id,
                "total_points": 0,
                "counted_split_value": "0",
                "total_split_value": "0",
                "last_updated": timestamp_text,
                "last_reason": "",
            }

        totals[member_id]["member_discord_nickname"] = display_name_for_member(member)
        totals[member_id]["total_points"] = int(totals[member_id]["total_points"]) + delta_points
        totals[member_id]["last_updated"] = timestamp_text
        totals[member_id]["last_reason"] = reason

        updated_totals_by_member_id[member.id] = int(totals[member_id]["total_points"])

    save_totals(totals)
    return updated_totals_by_member_id


def get_member_points(member: discord.Member) -> int:
    totals = load_totals()
    row = totals.get(str(member.id))
    if not row:
        return 0
    return int(row["total_points"])


async def ensure_guild_members_loaded(guild: discord.Guild) -> None:
    try:
        await guild.chunk(cache=True)
    except Exception:
        pass


async def get_all_role_members(guild: discord.Guild, role: discord.Role) -> list[discord.Member]:
    await ensure_guild_members_loaded(guild)

    members: list[discord.Member] = []
    role_id = role.id

    for member in guild.members:
        if member.bot:
            continue
        if any(r.id == role_id for r in member.roles):
            members.append(member)

    members.sort(key=lambda m: display_name_for_member(m).lower())
    return members


async def get_active_leaderboard_rows(guild: discord.Guild) -> list[dict]:
    await ensure_guild_members_loaded(guild)

    totals = load_totals()
    active_rows: list[dict] = []

    for member_id, row in totals.items():
        member = guild.get_member(int(member_id))
        if member is None:
            try:
                member = await guild.fetch_member(int(member_id))
            except Exception:
                member = None

        if member is None:
            continue

        row_copy = dict(row)
        row_copy["member_discord_nickname"] = display_name_for_member(member)
        active_rows.append(row_copy)

    active_rows.sort(
        key=lambda x: (-int(x["total_points"]), x["member_discord_nickname"].lower())
    )
    return active_rows


async def prune_departed_members(guild: discord.Guild, removal_source: str) -> list[dict]:
    await ensure_guild_members_loaded(guild)

    totals = load_totals()
    removed_rows: list[dict] = []
    remaining_totals = dict(totals)

    for member_id, row in totals.items():
        member = guild.get_member(int(member_id))
        if member is None:
            try:
                member = await guild.fetch_member(int(member_id))
            except Exception:
                member = None

        if member is None:
            append_member_left_row(row, removal_source)
            removed_rows.append(row)
            remaining_totals.pop(member_id, None)

    if removed_rows:
        save_totals(remaining_totals)

    return removed_rows


async def handle_member_departure(member: discord.Member) -> None:
    totals = load_totals()
    member_id = str(member.id)

    if member_id not in totals:
        return

    row = totals[member_id]
    append_member_left_row(row, "member_remove")
    totals.pop(member_id, None)
    save_totals(totals)


async def autocomplete_users(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if interaction.guild is None:
        return []

    raw = current or ""
    parts = [part.strip() for part in raw.split(",")]
    active_prefix = parts[-1] if parts else ""
    already_entered = [part for part in parts[:-1] if part]

    prefix_lower = active_prefix.lower()
    matches: list[app_commands.Choice[str]] = []

    await ensure_guild_members_loaded(interaction.guild)

    for member in interaction.guild.members:
        name_candidates = []
        if member.display_name:
            name_candidates.append(member.display_name)
        if member.name and member.name not in name_candidates:
            name_candidates.append(member.name)

        matched_name = None
        for candidate in name_candidates:
            if not prefix_lower or prefix_lower in candidate.lower():
                matched_name = candidate
                break

        if not matched_name:
            continue

        combined = already_entered + [matched_name]
        value = ", ".join(combined)

        if len(value) > 100:
            continue

        matches.append(app_commands.Choice(name=matched_name, value=value))

        if len(matches) >= 25:
            break

    return matches


async def resolve_members_from_users_field(
    guild: discord.Guild,
    users_text: str,
) -> tuple[list[discord.Member], list[str]]:
    await ensure_guild_members_loaded(guild)

    tokens = [token.strip() for token in users_text.split(",") if token.strip()]
    resolved_members: list[discord.Member] = []
    unresolved_tokens: list[str] = []
    seen_ids: set[int] = set()

    for token in tokens:
        cleaned = token.strip()
        member: Optional[discord.Member] = None

        if cleaned.startswith("<@") and cleaned.endswith(">"):
            cleaned = cleaned.replace("<@", "").replace("!", "").replace(">", "").strip()

        if cleaned.isdigit():
            member = guild.get_member(int(cleaned))
            if member is None:
                try:
                    member = await guild.fetch_member(int(cleaned))
                except Exception:
                    member = None
        else:
            lowered = cleaned.lower()

            exact_display = discord.utils.find(
                lambda m: (m.display_name or "").lower() == lowered,
                guild.members,
            )
            exact_name = discord.utils.find(
                lambda m: m.name.lower() == lowered,
                guild.members,
            )
            partial_display = discord.utils.find(
                lambda m: lowered in (m.display_name or "").lower(),
                guild.members,
            )
            partial_name = discord.utils.find(
                lambda m: lowered in m.name.lower(),
                guild.members,
            )

            member = exact_display or exact_name or partial_display or partial_name

        if member is None:
            unresolved_tokens.append(token)
            continue

        if member.id in seen_ids:
            continue

        seen_ids.add(member.id)
        resolved_members.append(member)

    return resolved_members, unresolved_tokens


async def resolve_member_ids_to_members(
    guild: discord.Guild,
    member_ids: list[int],
) -> tuple[list[discord.Member], list[int]]:
    await ensure_guild_members_loaded(guild)

    resolved: list[discord.Member] = []
    unresolved: list[int] = []
    seen: set[int] = set()

    for member_id in member_ids:
        if member_id in seen:
            continue
        seen.add(member_id)

        member = guild.get_member(member_id)
        if member is None:
            try:
                member = await guild.fetch_member(member_id)
            except Exception:
                member = None

        if member is None:
            unresolved.append(member_id)
        else:
            resolved.append(member)

    return resolved, unresolved


class MemberAdjustmentSelect(discord.ui.UserSelect):
    def __init__(self, parent_view: "MemberAdjustmentView"):
        super().__init__(
            placeholder="Select up to 15 members...",
            min_values=1,
            max_values=15,
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.parent_view.pending_member_ids = [int(user.id) for user in self.values]
        self.parent_view.confirm_selection_button.disabled = len(self.parent_view.pending_member_ids) == 0

        preview_names = ", ".join(
            user.display_name if isinstance(user, discord.Member) else user.name
            for user in self.values[:15]
        )

        embed = build_branded_embed(
            title=self.parent_view.preview_title,
            color=self.parent_view.preview_color,
            description="Selection staged. Click Confirm Selection to lock it in.",
        )
        embed.add_field(name="POINTS", value=f"**{self.parent_view.points}**", inline=True)
        embed.add_field(name="ACTION", value=f"**{self.parent_view.action.upper()}**", inline=True)
        embed.add_field(name="REASON", value=f"**{self.parent_view.reason}**", inline=False)
        embed.add_field(
            name="RECOMMENDED LIMIT",
            value="**Best for 10–15 members maximum per action.**",
            inline=False,
        )
        embed.add_field(
            name="PENDING SELECTION",
            value=preview_names or "No members selected.",
            inline=False,
        )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class MemberAdjustmentView(discord.ui.View):
    def __init__(
        self,
        *,
        action: str,
        points: int,
        reason: Optional[str],
        staff_user_id: int,
    ):
        super().__init__(timeout=300)
        self.action = action
        self.points = points
        self.reason = (reason or "No reason provided").strip()
        self.staff_user_id = staff_user_id
        self.completed = False
        self.pending_member_ids: list[int] = []
        self.confirmed_member_ids: list[int] = []
        self.preview_title = "Select Rank Point Adjustment"
        self.preview_color = action_color(action)

        self.member_select = MemberAdjustmentSelect(self)
        self.add_item(self.member_select)
        self.confirm_selection_button.disabled = True
        self.submit_button.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.staff_user_id:
            await interaction.response.send_message(
                "Only the staff member who opened this selector can use it.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm Selection", style=discord.ButtonStyle.primary, row=1)
    async def confirm_selection_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.completed:
            await interaction.response.send_message(
                "This selector has already been used.",
                ephemeral=True,
            )
            return

        if not self.pending_member_ids:
            await interaction.response.send_message(
                "Select at least one member first.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        self.confirmed_member_ids = list(self.pending_member_ids)
        self.submit_button.disabled = False

        resolved_members, unresolved_ids = await resolve_member_ids_to_members(
            interaction.guild,
            self.confirmed_member_ids,
        )

        selected_names = ", ".join(
            display_name_for_member(member) for member in resolved_members[:15]
        )

        if unresolved_ids:
            unresolved_text = ", ".join(str(x) for x in unresolved_ids[:10])
            if len(unresolved_ids) > 10:
                unresolved_text += f", and {len(unresolved_ids) - 10} more"
            if selected_names:
                selected_names += f"\n\nUnresolved IDs: {unresolved_text}"
            else:
                selected_names = f"Unresolved IDs: {unresolved_text}"

        embed = build_branded_embed(
            title=self.preview_title,
            color=self.preview_color,
            description="Selection confirmed. Click Submit Point Change to apply the points.",
        )
        embed.add_field(name="POINTS", value=f"**{self.points}**", inline=True)
        embed.add_field(name="ACTION", value=f"**{self.action.upper()}**", inline=True)
        embed.add_field(name="REASON", value=f"**{self.reason}**", inline=False)
        embed.add_field(
            name="RECOMMENDED LIMIT",
            value="**Best for 10–15 members maximum per action.**",
            inline=False,
        )
        embed.add_field(
            name="CONFIRMED MEMBERS",
            value=selected_names or "No resolvable members confirmed.",
            inline=False,
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Submit Point Change", style=discord.ButtonStyle.success, row=1)
    async def submit_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.completed:
            await interaction.response.send_message(
                "This selector has already been used.",
                ephemeral=True,
            )
            return

        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not self.confirmed_member_ids:
            await interaction.response.send_message(
                "Confirm your selection first.",
                ephemeral=True,
            )
            return

        resolved_members, unresolved_ids = await resolve_member_ids_to_members(
            interaction.guild,
            self.confirmed_member_ids,
        )

        if not resolved_members:
            await interaction.response.send_message(
                "None of the confirmed members could be resolved.",
                ephemeral=True,
            )
            return

        guild_name = interaction.guild.name
        channel_name = getattr(interaction.channel, "name", "unknown-channel")
        performer_name = display_name_for_member(interaction.user)
        performer_id = interaction.user.id

        result_lines: list[str] = []
        delta = action_to_delta(self.action, self.points)

        updated_totals_by_member_id = batch_apply_points_change(
            resolved_members,
            delta,
            self.reason,
        )

        for member in resolved_members:
            new_total = updated_totals_by_member_id.get(member.id, get_member_points(member))
            append_ledger_row(
                action=self.action,
                delta_points=delta,
                target_member_name=display_name_for_member(member),
                target_member_id=member.id,
                performer_name=performer_name,
                performer_id=performer_id,
                reason=self.reason,
                guild_name=guild_name,
                channel_name=channel_name,
            )

            sign = "+" if delta > 0 else ""
            result_lines.append(
                f"**{display_name_for_member(member)}**: {sign}{delta} → **{new_total}**"
            )

        if unresolved_ids:
            result_lines.append("")
            result_lines.append(f"Unresolved IDs: {', '.join(str(x) for x in unresolved_ids)}")

        embed = build_branded_embed(
            title=action_title(self.action),
            color=action_color(self.action),
        )
        embed.add_field(name="POINTS", value=f"**{self.points}**", inline=True)
        embed.add_field(name="ACTION", value=f"**{self.action.upper()}**", inline=True)
        embed.add_field(name="REASON", value=f"**{self.reason}**", inline=False)
        embed.add_field(
            name="ROLL RESULT",
            value="\n".join(result_lines) if result_lines else "No valid members selected.",
            inline=False,
        )

        self.completed = True
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.completed:
            await interaction.response.send_message(
                "This selector has already been used.",
                ephemeral=True,
            )
            return

        self.completed = True
        for item in self.children:
            item.disabled = True

        embed = build_branded_embed(
            title="Selection Cancelled",
            color=discord.Color.light_grey(),
            description="No points were changed.",
        )
        await interaction.response.edit_message(embed=embed, view=self)


class RoleAdjustmentView(discord.ui.View):
    def __init__(
        self,
        *,
        role: discord.Role,
        members: list[discord.Member],
        action: str,
        points: int,
        reason: str,
        staff_user_id: int,
    ):
        super().__init__(timeout=600)
        self.role = role
        self.members = sorted(members, key=lambda m: display_name_for_member(m).lower())
        self.action = action
        self.points = points
        self.reason = reason
        self.staff_user_id = staff_user_id
        self.page = 0
        self.per_page = 20
        self.completed = False
        self.refresh_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.staff_user_id:
            await interaction.response.send_message(
                "Only the staff member who opened this preview can use it.",
                ephemeral=True,
            )
            return False
        return True

    def max_page(self) -> int:
        return max((len(self.members) - 1) // self.per_page, 0)

    def refresh_buttons(self) -> None:
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.max_page()

    def build_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        page_members = self.members[start:end]

        lines = []
        for idx, member in enumerate(page_members, start=start + 1):
            lines.append(f"**#{idx}** {display_name_for_member(member)}")

        delta = action_to_delta(self.action, self.points)
        delta_text = f"+{self.points}" if delta > 0 else f"-{self.points}"

        embed = build_branded_embed(
            title="Role Point Change Preview",
            color=action_color(self.action),
            description="Review every member, then confirm to apply the point change.",
        )
        embed.add_field(name="ROLE", value=self.role.mention, inline=True)
        embed.add_field(name="ACTION", value=f"**{self.action.upper()}**", inline=True)
        embed.add_field(name="POINTS EACH", value=f"**{delta_text}**", inline=True)
        embed.add_field(name="TOTAL MEMBERS", value=f"**{len(self.members)}**", inline=True)
        embed.add_field(name="REASON", value=f"**{self.reason}**", inline=False)
        embed.add_field(
            name="MEMBERS ON THIS PAGE",
            value="\n".join(lines) if lines else "No members found.",
            inline=False,
        )
        embed.add_field(
            name="PAGE",
            value=f"**{self.page + 1} / {self.max_page() + 1}**",
            inline=False,
        )
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=1)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.page < self.max_page():
            self.page += 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Confirm Point Change", style=discord.ButtonStyle.success, row=2)
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.completed:
            await interaction.response.send_message(
                "This preview has already been used.",
                ephemeral=True,
            )
            return

        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        guild_name = interaction.guild.name
        channel_name = getattr(interaction.channel, "name", "unknown-channel")
        performer_name = display_name_for_member(interaction.user)
        performer_id = interaction.user.id
        delta = action_to_delta(self.action, self.points)

        updated_totals_by_member_id = batch_apply_points_change(
            self.members,
            delta,
            self.reason,
        )

        result_lines: list[str] = []
        for member in self.members:
            new_total = updated_totals_by_member_id.get(member.id, get_member_points(member))
            append_ledger_row(
                action=self.action,
                delta_points=delta,
                target_member_name=display_name_for_member(member),
                target_member_id=member.id,
                performer_name=performer_name,
                performer_id=performer_id,
                reason=self.reason,
                guild_name=guild_name,
                channel_name=channel_name,
            )

            sign = "+" if delta > 0 else ""
            result_lines.append(f"**{display_name_for_member(member)}**: {sign}{delta} → **{new_total}**")

        embed = build_branded_embed(
            title=action_title(self.action),
            color=action_color(self.action),
            description=f"Applied the point change to **{len(self.members)}** member(s) in {self.role.mention}.",
        )
        embed.add_field(name="ROLE", value=self.role.mention, inline=True)
        embed.add_field(name="ACTION", value=f"**{self.action.upper()}**", inline=True)
        embed.add_field(name="POINTS EACH", value=f"**{delta}**", inline=True)
        embed.add_field(name="REASON", value=f"**{self.reason}**", inline=False)

        preview_results = result_lines[:20]
        if len(result_lines) > 20:
            preview_results.append(f"...and {len(result_lines) - 20} more")

        embed.add_field(
            name="ROLL RESULT",
            value="\n".join(preview_results) if preview_results else "No results to display.",
            inline=False,
        )

        self.completed = True
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.completed:
            await interaction.response.send_message(
                "This preview has already been used.",
                ephemeral=True,
            )
            return

        self.completed = True
        for item in self.children:
            item.disabled = True

        embed = build_branded_embed(
            title="Role Point Change Cancelled",
            color=discord.Color.light_grey(),
            description="No points were changed.",
        )
        await interaction.response.edit_message(embed=embed, view=self)


class LeaderboardView(discord.ui.View):
    def __init__(self, rows: list[dict], per_page: int = 10):
        super().__init__(timeout=300)
        self.rows = rows
        self.per_page = per_page
        self.page = 0
        self.refresh_buttons()

    def refresh_buttons(self) -> None:
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= max((len(self.rows) - 1) // self.per_page, 0)

    def build_embed(self) -> discord.Embed:
        total_members = len(self.rows)
        total_points = sum(int(row["total_points"]) for row in self.rows)

        start = self.page * self.per_page
        end = start + self.per_page
        page_rows = self.rows[start:end]

        embed = build_branded_embed(
            title="Rank Up Points Leaderboard",
            color=discord.Color.gold(),
            description=(
                f"**Active Members Ranked:** {total_members}\n"
                f"**Combined Active Member Points:** {total_points}"
            ),
        )

        if not page_rows:
            embed.add_field(name="RANKINGS", value="No leaderboard entries found.", inline=False)
            return embed

        lines = []
        for idx, row in enumerate(page_rows, start=start + 1):
            last_reason = row.get("last_reason", "").strip() or "No reason provided"
            lines.append(
                f"**#{idx}** {row['member_discord_nickname']} — **{row['total_points']}** pts\n"
                f"Recent: *{last_reason}*"
            )

        embed.add_field(name="RANKINGS", value="\n\n".join(lines), inline=False)
        embed.add_field(
            name="PAGE",
            value=f"**{self.page + 1} / {max((len(self.rows) - 1) // self.per_page, 0) + 1}**",
            inline=False,
        )
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        max_page = max((len(self.rows) - 1) // self.per_page, 0)
        if self.page < max_page:
            self.page += 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


rankpoints_group = app_commands.Group(
    name="rankpoints",
    description="Manage rank up points",
)


@rankpoints_group.command(name="manual", description="Manual member list point adjustment")
@app_commands.describe(
    action="Add or subtract points",
    users="Comma-separated names, IDs, or mentions",
    points="How many points to apply to each listed member",
    reason="Optional reason for the adjustment",
)
@app_commands.autocomplete(users=autocomplete_users)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract"),
    ]
)
async def rankpoints_manual(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    users: str,
    points: app_commands.Range[int, 1, 1000000],
    reason: Optional[str] = None,
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not has_staff_role(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    resolved_members, unresolved = await resolve_members_from_users_field(interaction.guild, users)

    if not resolved_members:
        await interaction.followup.send("No valid members were found in the users field.", ephemeral=True)
        return

    reason_text = (reason or "No reason provided").strip()
    guild_name = interaction.guild.name
    channel_name = getattr(interaction.channel, "name", "unknown-channel")
    performer_name = display_name_for_member(interaction.user)
    performer_id = interaction.user.id
    delta = action_to_delta(action.value, points)

    updated_totals_by_member_id = batch_apply_points_change(
        resolved_members,
        delta,
        reason_text,
    )

    lines = []
    for member in resolved_members:
        new_total = updated_totals_by_member_id.get(member.id, get_member_points(member))
        append_ledger_row(
            action=action.value,
            delta_points=delta,
            target_member_name=display_name_for_member(member),
            target_member_id=member.id,
            performer_name=performer_name,
            performer_id=performer_id,
            reason=reason_text,
            guild_name=guild_name,
            channel_name=channel_name,
        )
        sign = "+" if delta > 0 else ""
        lines.append(f"**{display_name_for_member(member)}**: {sign}{delta} → **{new_total}**")

    if unresolved:
        lines.append("")
        lines.append(f"Unresolved: {', '.join(unresolved)}")

    embed = build_branded_embed(title=action_title(action.value), color=action_color(action.value))
    embed.add_field(name="POINTS", value=f"**{points}**", inline=True)
    embed.add_field(name="ACTION", value=f"**{action.value.upper()}**", inline=True)
    embed.add_field(name="REASON", value=f"**{reason_text}**", inline=False)
    embed.add_field(name="ROLL RESULT", value="\n".join(lines), inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


@rankpoints_group.command(name="select", description="Small group point adjustment with member picker")
@app_commands.describe(
    action="Add or subtract points",
    points="How many points to apply to each selected member",
    reason="Optional reason for the adjustment",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract"),
    ]
)
async def rankpoints_select(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    points: app_commands.Range[int, 1, 1000000],
    reason: Optional[str] = None,
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not has_staff_role(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    view = MemberAdjustmentView(
        action=action.value,
        points=points,
        reason=reason,
        staff_user_id=interaction.user.id,
    )

    embed = build_branded_embed(
        title="Select Rank Point Adjustment",
        color=action_color(action.value),
        description="Best for small groups only. Recommended limit is 10–15 members.",
    )
    embed.add_field(name="ACTION", value=f"**{action.value.upper()}**", inline=True)
    embed.add_field(name="POINTS", value=f"**{points}**", inline=True)
    embed.add_field(name="REASON", value=f"**{(reason or 'No reason provided').strip()}**", inline=False)
    embed.add_field(
        name="RECOMMENDED LIMIT",
        value="**Use this for 10–15 members max. For larger groups, use `/rankpoints role` or `/rankpoints manual`.**",
        inline=False,
    )
    embed.add_field(name="PENDING SELECTION", value="No members selected yet.", inline=False)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@rankpoints_group.command(name="role", description="Apply points to everyone in a role with confirmation")
@app_commands.describe(
    action="Add or subtract points",
    role="The role to apply the point change to",
    points="How many points to apply to each member of the role",
    reason="Optional reason for the adjustment",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract"),
    ]
)
async def rankpoints_role(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    role: discord.Role,
    points: app_commands.Range[int, 1, 1000000],
    reason: Optional[str] = None,
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not has_staff_role(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    role_members = await get_all_role_members(interaction.guild, role)

    if not role_members:
        await interaction.followup.send(
            "That role has no non-bot members to adjust.",
            ephemeral=True,
        )
        return

    reason_text = (reason or "No reason provided").strip()

    view = RoleAdjustmentView(
        role=role,
        members=role_members,
        action=action.value,
        points=points,
        reason=reason_text,
        staff_user_id=interaction.user.id,
    )

    await interaction.followup.send(
        embed=view.build_embed(),
        view=view,
        ephemeral=True,
    )


@rankpoints_group.command(name="balance", description="Check a member's current point total")
@app_commands.describe(member="The member to check")
async def rankpoints_balance(
    interaction: discord.Interaction,
    member: Optional[discord.Member] = None,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    target = member or interaction.user
    if not isinstance(target, discord.Member):
        await interaction.response.send_message("That member could not be resolved.", ephemeral=True)
        return

    points = get_member_points(target)
    totals = load_totals()
    row = totals.get(str(target.id), {})
    last_reason = (row.get("last_reason", "") or "No reason provided").strip()

    embed = build_branded_embed(title="Rank Up Points", color=discord.Color.blurple())
    embed.add_field(name="MEMBER", value=target.mention, inline=False)
    embed.add_field(name="CURRENT POINTS", value=f"**{points}**", inline=False)
    embed.add_field(name="MOST RECENT REASON", value=f"*{last_reason}*", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@rankpoints_group.command(name="leaderboard", description="Show the full rank points leaderboard")
async def rankpoints_leaderboard(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    await interaction.response.defer()

    rows = await get_active_leaderboard_rows(interaction.guild)
    view = LeaderboardView(rows=rows, per_page=10)
    embed = view.build_embed()

    await interaction.followup.send(embed=embed, view=view)


@rankpoints_group.command(name="export", description="Export the rank points CSV files")
async def rankpoints_export(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not has_staff_role(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    ensure_data_files()

    await interaction.response.send_message(
        content="Here are the current rank points exports.",
        files=[
            discord.File(TOTALS_FILE, filename="rank_points_totals.csv"),
            discord.File(LEDGER_FILE, filename="rank_points_ledger.csv"),
            discord.File(MEMBER_LEFT_FILE, filename="rank_points_member_left.csv"),
        ],
        ephemeral=True,
    )


@rankpoints_group.command(name="pruneleft", description="Remove users from totals who are no longer in the server")
async def rankpoints_pruneleft(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    if not has_staff_role(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    removed_rows = await prune_departed_members(interaction.guild, "manual_prune")

    if not removed_rows:
        embed = build_branded_embed(
            title="Prune Complete",
            color=discord.Color.green(),
            description="No departed members were found in the totals CSV.",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    lines = [
        f"**{row['member_discord_nickname']}** — **{row['total_points']}** pts"
        for row in removed_rows[:25]
    ]

    if len(removed_rows) > 25:
        lines.append(f"...and {len(removed_rows) - 25} more")

    embed = build_branded_embed(
        title="Prune Complete",
        color=discord.Color.orange(),
        description=f"Removed **{len(removed_rows)}** departed member(s) from totals.",
    )
    embed.add_field(name="REMOVED", value="\n".join(lines), inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


def setup(tree: app_commands.CommandTree) -> None:
    ensure_data_files()

    try:
        tree.add_command(rankpoints_group)
    except app_commands.CommandAlreadyRegistered:
        pass

    bot = tree.client

    @bot.event
    async def on_member_remove(member: discord.Member) -> None:
        await handle_member_departure(member)
