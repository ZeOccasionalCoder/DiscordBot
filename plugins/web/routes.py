"""
web_routes.py — Web dashboard route handlers and template rendering
--------------------------------------------------------------------
Serves the multi-page Sea Worthy clan dashboard using Jinja2 templates.
Called from clan_stats.py's aiohttp web server.
"""

import os
import datetime
from collections import OrderedDict

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

# Import data-access functions from clan_stats
from plugins.clan_stats import (
    get_top_players_for_metric,
    get_top_gainers_for_metric,
    get_all_personal_bests,
    get_unique_pb_bosses,
    get_recent_drops,
    get_recent_collection_logs,
    get_top_drops_by_value,
    get_top_collection_log_players,
    get_active_competitions,
    get_competition_standings,
    _format_boss_name,
    _format_number,
    WOM_SKILLS,
    WOM_BOSSES,
    WOM_ACTIVITIES,
    WOM_GROUP_ID,
    _connect,
)

# ---------------------------------------------------------------------------
# Jinja2 setup
# ---------------------------------------------------------------------------
WEB_DIR = os.path.dirname(os.path.abspath(__file__))  # plugins/web/
TEMPLATE_DIR = os.path.join(WEB_DIR, "templates")
STATIC_DIR = os.path.join(WEB_DIR, "static")

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
)
_jinja_env.globals["format_boss_name"] = _format_boss_name

# ---------------------------------------------------------------------------
# Common context shared by all pages
# ---------------------------------------------------------------------------
def _base_context(active_page: str) -> dict:
    return {
        "active_page": active_page,
        "member_count": _get_member_count(),
        "wom_group_id": WOM_GROUP_ID,
    }


_cached_member_count = 0
_member_count_ts = 0


def _get_member_count() -> int:
    """Get member count from wom_player_types table (all players tracked by WOM group).
    Falls back to wom_hiscores distinct count. Cached for 30 minutes.
    """
    global _cached_member_count, _member_count_ts
    import time
    now = time.time()
    if _cached_member_count > 0 and (now - _member_count_ts) < 1800:
        return _cached_member_count

    # _connect imported at module level from clan_stats
    try:
        conn = _connect()
        # Best source: wom_player_types table (populated from WOM group members endpoint)
        row = conn.execute("SELECT COUNT(*) FROM wom_player_types").fetchone()
        count = row[0] if row and row[0] > 0 else 0
        if count == 0:
            # Fallback: distinct players across all hiscores
            row = conn.execute(
                "SELECT COUNT(DISTINCT player_name) FROM wom_hiscores WHERE value > 0"
            ).fetchone()
            count = row[0] if row else 0
        conn.close()
        _cached_member_count = count
        _member_count_ts = now
        return count
    except Exception:
        return _cached_member_count or 0


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _fmt_value(value: int) -> str:
    """Format large numbers: 1,234,567 or 12.3m or 1.2b."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}b"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    elif value >= 10_000:
        return f"{value / 1_000:.1f}k"
    else:
        return f"{value:,}"


def _fmt_gained(value) -> str:
    """Format gained values."""
    if isinstance(value, float):
        value = int(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}k"
    else:
        return f"{value:,}"


def _short_date(iso_str: str) -> str:
    """Convert ISO timestamp to short display like 'Mar 15'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except Exception:
        return iso_str[:10] if len(iso_str) >= 10 else iso_str


def _enrich_drops(drops: list) -> list:
    """Add formatted values, short dates, and image URLs to drop dicts."""
    for d in drops:
        d["item_value_fmt"] = _format_number(d.get("item_value", 0))
        d["recorded_at_short"] = _short_date(d.get("recorded_at", ""))
        # Add wiki image URL if no image already set
        if not d.get("item_image_url"):
            d["item_image_url"] = _wiki_item_image_url(d.get("item_name", ""))
    return drops


def _wiki_item_image_url(item_name: str) -> str:
    """Generate an OSRS Wiki image URL for an item name."""
    if not item_name:
        return ""
    # Wiki uses the item name with spaces replaced by underscores
    wiki_name = item_name.replace(" ", "_")
    return f"https://oldschool.runescape.wiki/images/{wiki_name}_detail.png"


def _enrich_clogs(clogs: list) -> list:
    for c in clogs:
        c["recorded_at_short"] = _short_date(c.get("recorded_at", ""))
        # Add item image URL from wiki
        if not c.get("item_image_url"):
            c["item_image_url"] = _wiki_item_image_url(c.get("item_name", ""))
    return clogs


# ---------------------------------------------------------------------------
# Data builders for metric cards (all-time + month columns)
# ---------------------------------------------------------------------------
def _build_metric_cards(metrics: list, metric_type: str, top_n: int = 5) -> OrderedDict:
    """Build {metric: {display_name, alltime, monthly, row_count}} for a list of metrics."""
    cards = OrderedDict()
    for metric in metrics:
        alltime = get_top_players_for_metric(metric, top_n)
        if not alltime:
            continue
        monthly = get_top_gainers_for_metric(metric, top_n)

        for p in alltime:
            p["value_fmt"] = _fmt_value(p.get("value", 0))
        for p in monthly:
            p["gained_fmt"] = _fmt_gained(p.get("gained", 0))

        cards[metric] = {
            "display_name": _format_boss_name(metric),
            "alltime": alltime,
            "monthly": monthly,
            "row_count": max(len(alltime), len(monthly)),
        }
    return cards


# ---------------------------------------------------------------------------
# Gained records builder (day/week/month/year tabs)
# ---------------------------------------------------------------------------
def _build_gained_records(metrics: list, top_n: int = 10) -> OrderedDict:
    """Build {metric: {day: [...], week: [...], month: [...], year: [...]}}."""
    records = OrderedDict()
    for metric in metrics:
        periods = {}
        for period in ["month"]:  # Start with month only (already fetched), others need API calls
            gainers = get_top_gainers_for_metric(metric, top_n)
            if gainers:
                for p in gainers:
                    p["gained_fmt"] = _fmt_gained(p.get("gained", 0))
                periods[period] = gainers
        if periods:
            records[metric] = periods
    return records


def _build_gained_records_full(metrics: list, top_n: int = 10) -> OrderedDict:
    """Build gained records with all periods from wom_gains_multi table."""
    # _connect imported at module level from clan_stats
    records = OrderedDict()
    for metric in metrics:
        periods = {}
        for period in ["day", "week", "month", "year"]:
            try:
                conn = _connect()
                rows = conn.execute(
                    """SELECT player_name, gained FROM wom_gains_multi
                       WHERE metric = ? AND period = ? AND gained > 0
                       ORDER BY gained DESC LIMIT ?""",
                    (metric, period, top_n)
                ).fetchall()
                conn.close()
                if rows:
                    entries = []
                    for r in rows:
                        entries.append({
                            "player_name": r[0],
                            "gained": r[1],
                            "gained_fmt": _fmt_gained(r[1]),
                        })
                    periods[period] = entries
            except Exception:
                pass
        if periods:
            records[metric] = periods
    return records


# ---------------------------------------------------------------------------
# EHP / EHB split by player type
# ---------------------------------------------------------------------------
def _get_ehp_ehb_by_type(metric: str, top_n: int = 10) -> tuple:
    """Return (mains_list, irons_list) for ehp or ehb metric."""
    # _connect imported at module level from clan_stats
    mains = []
    irons = []
    try:
        conn = _connect()
        # Get all players for this metric
        rows = conn.execute(
            """SELECT h.player_name, h.value, COALESCE(p.player_type, 'regular') as ptype
               FROM wom_hiscores h
               LEFT JOIN wom_player_types p ON LOWER(h.player_name) = LOWER(p.player_name)
               WHERE h.metric = ? AND h.value > 0
               ORDER BY h.value DESC""",
            (metric,)
        ).fetchall()
        conn.close()

        for r in rows:
            entry = {
                "player_name": r[0],
                "value": r[1],
                "value_fmt": _fmt_value(r[1]),
            }
            ptype = r[2].lower() if r[2] else "regular"
            if ptype in ("ironman", "hardcore", "ultimate", "group_ironman"):
                if len(irons) < top_n:
                    irons.append(entry)
            else:
                if len(mains) < top_n:
                    mains.append(entry)
            if len(mains) >= top_n and len(irons) >= top_n:
                break
    except Exception:
        pass
    return mains, irons


# ---------------------------------------------------------------------------
# #1 player showcase builders
# ---------------------------------------------------------------------------
def _build_alltime_leaders() -> OrderedDict:
    """Get #1 player for key categories."""
    leaders = OrderedDict()
    # Top overall XP
    top = get_top_players_for_metric("overall", 1)
    if top:
        leaders["Overall XP"] = {"player": top[0]["player_name"], "value": _fmt_value(top[0]["value"])}
    # Top slayer
    top = get_top_players_for_metric("slayer", 1)
    if top:
        leaders["Slayer XP"] = {"player": top[0]["player_name"], "value": _fmt_value(top[0]["value"])}
    # A few key bosses
    for boss_key, boss_label in [("chambers_of_xeric", "COX KC"), ("theatre_of_blood", "TOB KC"),
                                  ("tombs_of_amascut", "TOA KC"), ("vorkath", "Vorkath KC"),
                                  ("zulrah", "Zulrah KC"), ("the_corrupted_gauntlet", "CG KC")]:
        top = get_top_players_for_metric(boss_key, 1)
        if top:
            leaders[boss_label] = {"player": top[0]["player_name"], "value": _fmt_value(top[0]["value"])}
    # Top collection log
    top_clog = get_top_collection_log_players(1)
    if top_clog:
        leaders["Collection Log"] = {"player": top_clog[0]["player_name"],
                                      "value": f"{top_clog[0]['slots']}/{top_clog[0]['total']}"}
    return leaders


def _build_monthly_leaders() -> OrderedDict:
    """Get #1 gainer for key categories this month."""
    leaders = OrderedDict()
    for metric, label in [("overall", "Overall XP"), ("slayer", "Slayer XP"),
                          ("chambers_of_xeric", "COX KC"), ("theatre_of_blood", "TOB KC"),
                          ("tombs_of_amascut", "TOA KC"), ("vorkath", "Vorkath KC")]:
        top = get_top_gainers_for_metric(metric, 1)
        if top:
            leaders[label] = {"player": top[0]["player_name"], "value": f"+{_fmt_gained(top[0]['gained'])}"}
    return leaders


# ---------------------------------------------------------------------------
# PB data restructuring for the PBs page
# ---------------------------------------------------------------------------
# Priority bosses that get their own featured sections
PRIORITY_PB_BOSSES = {
    "Tombs of Amascut": "toa",
    "Theatre of Blood": "tob",
    "Chambers of Xeric": "cox",
    "Sol Heredit": "sol",
    "TzKal-Zuk": "zuk",
}

# Alternate name variations to match
TOA_NAMES = ["Tombs of Amascut", "Tombs Of Amascut", "tombs of amascut"]
TOB_NAMES = ["Theatre of Blood", "Theatre Of Blood", "theatre of blood",
             "Theater of Blood", "Theater Of Blood"]
COX_NAMES = ["Chambers of Xeric", "Chambers Of Xeric", "chambers of xeric"]
SOL_NAMES = ["Sol Heredit", "sol heredit"]
ZUK_NAMES = ["TzKal-Zuk", "Tzkal-Zuk", "tzkal-zuk", "TzKal Zuk", "Inferno"]


def _categorize_pb(boss_name: str) -> str:
    """Return category key for a PB boss name."""
    bn_lower = boss_name.lower()
    if "tombs of amascut" in bn_lower or "toa" == bn_lower:
        return "toa"
    if "theatre of blood" in bn_lower or "theater of blood" in bn_lower or "tob" == bn_lower:
        return "tob"
    if "chambers of xeric" in bn_lower or "cox" == bn_lower:
        return "cox"
    if "sol heredit" in bn_lower:
        return "sol"
    if "tzkal-zuk" in bn_lower or "tzkal zuk" in bn_lower or "inferno" in bn_lower:
        return "zuk"
    return "other"


def _build_structured_pbs() -> dict:
    """Build structured PB data for the template."""
    all_pbs = get_all_personal_bests(limit=5000)

    toa = {}   # mode -> team_size -> [pbs]
    tob = {}   # 'normal'/'hard' -> team_size -> [pbs]
    cox = {}   # 'normal'/'cm' -> team_size -> [pbs]
    sol = {}   # team_size -> [pbs]
    zuk = {}   # team_size -> [pbs]
    other = OrderedDict()  # boss_name -> [pbs]

    for pb in all_pbs:
        boss = pb.get("boss_name", "")
        cat = _categorize_pb(boss)
        team = pb.get("team_size", "Solo")
        mode = pb.get("mode", "")

        # Normalize team size
        if team.lower() == "solo":
            team = "Team of 1"

        if cat == "toa":
            # TOA: split by Normal/Expert mode
            mode_key = mode if mode in ("Normal", "Expert") else ""
            toa.setdefault(mode_key, {}).setdefault(team, []).append(pb)

        elif cat == "tob":
            # TOB: determine if hard mode from boss name or mode field
            is_hard = ("hard" in boss.lower()) or ("hard" in mode.lower())
            mode_key = "hard" if is_hard else "normal"
            tob.setdefault(mode_key, {}).setdefault(team, []).append(pb)

        elif cat == "cox":
            # COX: determine if challenge mode
            is_cm = ("challenge" in boss.lower()) or ("challenge" in mode.lower())
            mode_key = "cm" if is_cm else "normal"
            cox.setdefault(mode_key, {}).setdefault(team, []).append(pb)

        elif cat == "sol":
            sol.setdefault(team, []).append(pb)

        elif cat == "zuk":
            zuk.setdefault(team, []).append(pb)

        else:
            # "Yama" and other bosses — no category column
            other.setdefault(boss, []).append(pb)

    # Sort the "other" dict alphabetically
    other_sorted = OrderedDict(sorted(other.items(), key=lambda x: x[0].lower()))

    return {
        "toa_pbs": toa if toa else None,
        "tob_pbs": tob if tob else None,
        "cox_pbs": cox if cox else None,
        "sol_pbs": sol if sol else None,
        "zuk_pbs": zuk if zuk else None,
        "other_pbs": other_sorted if other_sorted else None,
    }


# ---------------------------------------------------------------------------
# Competition data for home page
# ---------------------------------------------------------------------------
def _build_competitions() -> list:
    """Build enriched competition data for the template."""
    comps = get_active_competitions()
    if not comps:
        return []

    enriched = []
    for comp in comps:
        c = dict(comp)
        c["metric_display"] = _format_boss_name(comp["metric"])

        try:
            start_dt = datetime.datetime.fromisoformat(comp["starts_at"].replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(comp["ends_at"].replace("Z", "+00:00"))
            c["date_range"] = f"{start_dt.strftime('%b %d')} — {end_dt.strftime('%b %d, %Y')}"

            if comp["status"] == "ongoing":
                delta = end_dt.replace(tzinfo=None) - datetime.datetime.utcnow()
                if delta.days > 0:
                    c["remaining"] = f"({delta.days}d remaining)"
                elif delta.seconds > 3600:
                    c["remaining"] = f"({delta.seconds // 3600}h remaining)"
                else:
                    c["remaining"] = "(ending soon!)"
            else:
                c["remaining"] = ""
        except Exception:
            c["date_range"] = "Unknown dates"
            c["remaining"] = ""

        # Standings
        if comp["status"] == "ongoing":
            standings = get_competition_standings(comp["id"], 15)
            for s in standings:
                s["gained_fmt"] = _fmt_gained(s.get("gained", 0))
            c["standings"] = standings
        else:
            c["standings"] = []

        enriched.append(c)
    return enriched


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------
async def serve_home(request: web.Request) -> web.Response:
    """Home page: drops, clogs, leaderboards, EHP/EHB, competitions."""
    ctx = _base_context("home")

    ctx["recent_drops"] = _enrich_drops(get_recent_drops(20))
    ctx["recent_clogs"] = _enrich_clogs(get_recent_collection_logs(20))
    ctx["top_drops"] = _enrich_drops(get_top_drops_by_value(15))
    ctx["top_clog"] = get_top_collection_log_players(15)

    # EHP / EHB split by player type
    ctx["ehp_mains"], ctx["ehp_irons"] = _get_ehp_ehb_by_type("ehp", 10)
    ctx["ehb_mains"], ctx["ehb_irons"] = _get_ehp_ehb_by_type("ehb", 10)

    # Showcase cards
    ctx["alltime_leaders"] = _build_alltime_leaders()
    ctx["monthly_leaders"] = _build_monthly_leaders()

    # Competitions
    ctx["competitions"] = _build_competitions()

    template = _jinja_env.get_template("home.html")
    html = template.render(**ctx)
    return web.Response(text=html, content_type="text/html")


async def serve_skills(request: web.Request) -> web.Response:
    """Skills hiscores page."""
    ctx = _base_context("skills")
    ctx["skills"] = _build_metric_cards(WOM_SKILLS, "skill", top_n=5)
    ctx["gained_records"] = _build_gained_records_full(WOM_SKILLS, top_n=10)
    template = _jinja_env.get_template("skills.html")
    html = template.render(**ctx)
    return web.Response(text=html, content_type="text/html")


async def serve_bosses(request: web.Request) -> web.Response:
    """Boss hiscores page."""
    ctx = _base_context("bosses")
    ctx["bosses"] = _build_metric_cards(WOM_BOSSES, "boss", top_n=5)
    ctx["activities"] = _build_metric_cards(WOM_ACTIVITIES, "activity", top_n=5)
    ctx["gained_records"] = _build_gained_records_full(WOM_BOSSES + WOM_ACTIVITIES, top_n=10)
    template = _jinja_env.get_template("bosses.html")
    html = template.render(**ctx)
    return web.Response(text=html, content_type="text/html")


async def serve_pbs(request: web.Request) -> web.Response:
    """Personal bests page."""
    ctx = _base_context("pbs")
    ctx.update(_build_structured_pbs())
    template = _jinja_env.get_template("pbs.html")
    html = template.render(**ctx)
    return web.Response(text=html, content_type="text/html")


def setup_routes(app: web.Application) -> None:
    """Register all dashboard routes on the aiohttp app."""
    app.router.add_get("/", serve_home)
    app.router.add_get("/skills", serve_skills)
    app.router.add_get("/bosses", serve_bosses)
    app.router.add_get("/pbs", serve_pbs)

    # Static files
    app.router.add_static("/static", STATIC_DIR, show_index=False)

    # Keep the old API endpoints (served from clan_stats directly)
