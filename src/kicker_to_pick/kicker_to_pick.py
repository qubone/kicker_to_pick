"""Sleeper Kicker-to-Rookie Pick Converter."""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import requests

PLAYER_CACHE_FILE = "nfl_players.json"
CACHE_EXPIRY = 86400  # 24 hours
TOTAL_NUM_PICKS = 48
LOW_REMAINING_THRESHOLD = 5
HTTP_OK = 200


def fetch_data(url: str) -> Optional[Dict[str, Any] | List[Any]]:
    """Fetch JSON data from a given URL."""
    try:
        response = requests.get(url)
        return response.json() if response.status_code == HTTP_OK else None
    except Exception as e:
        click.secho(f"Network Error: {e}", fg="red")
        return None


def get_players() -> Dict[str, Any]:
    """Integrated from sleeper_fetch_players logic.

    Checks if local player data exists; if not or if old, fetches from Sleeper.
    """
    cache_path = Path(PLAYER_CACHE_FILE)
    if cache_path.is_file():
        # Check if file is older than 24 hours
        file_age = time.time() - cache_path.stat().st_mtime
        if file_age < CACHE_EXPIRY:
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    return dict(json.load(f))
            except (json.JSONDecodeError, IOError) as e:
                click.secho(f"Cache file corrupted or unreadable: {e}. Re-fetching...", fg="yellow")

    click.echo("Fetching fresh player data from Sleeper (this may take a moment)...")
    data = fetch_data("https://api.sleeper.app/v1/players/nfl")
    if data and isinstance(data, dict):
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)
        return data
    return {}


def get_auto_draft_id(league_id: str) -> Optional[str]:
    """Fetch the most recent draft ID for a given league."""
    drafts = fetch_data(f"https://api.sleeper.app/v1/league/{league_id}/drafts")
    if isinstance(drafts, list) and len(drafts) > 0:
        draft_id = drafts[0]["draft_id"]
        return draft_id if isinstance(draft_id, str) else None
    return None


def get_league_info(league_id: str) -> Optional[Dict[str, Any]]:
    """Fetch general league settings and name."""
    data = fetch_data(f"https://api.sleeper.app/v1/league/{league_id}")
    return data if isinstance(data, dict) else None


def resolve_draft_id(league_id: str, draft_id: Optional[str]) -> Optional[str]:
    """Resolve the draft ID, fetching the latest if not provided."""
    if draft_id:
        return draft_id

    click.echo(f"Searching for latest draft in league {league_id}...")
    draft_id = get_auto_draft_id(league_id)
    if not draft_id:
        click.secho("Error: No drafts found for this league.", fg="red")
        return None
    click.echo(f"Target Draft: {draft_id}")
    return draft_id


def fetch_draft_data(
    league_id: str, draft_id: str
) -> Tuple[Optional[Dict[str, Any] | List[Any]], Optional[Dict[str, Any] | List[Any]]]:
    """Fetch users and draft picks data."""
    users_data = fetch_data(f"https://api.sleeper.app/v1/league/{league_id}/users")
    draft_picks = fetch_data(f"https://api.sleeper.app/v1/draft/{draft_id}/picks")
    return users_data, draft_picks


def generate_output(
    players: Dict[str, Any], draft_picks: List[Any], user_map: Dict[str, str], teams: int, final_name: str
) -> str:
    """Generate the output text for kicker picks."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = [f"**2026 Rookie Pick Tracker: {final_name}**", f"*Last Updated: {now}*", "---"]

    for i, pick in enumerate(draft_picks):
        if i >= TOTAL_NUM_PICKS:
            break

        round_num = (i // teams) + 1
        pick_num = (i % teams) + 1
        label = f"{round_num}.{pick_num:02d}"

        username = user_map.get(pick["picked_by"], "Unknown")
        p_meta = pick.get("metadata", {})
        player_name = f"{p_meta.get('first_name', '')} {p_meta.get('last_name', '')}"

        output.append(f"Pick {label} @{username} (via {player_name})")

        if (i + 1) % teams == 0:
            output.append("---")
    output.append("\n")

    remaining = TOTAL_NUM_PICKS - len(draft_picks)
    if 0 < remaining <= LOW_REMAINING_THRESHOLD:
        output.append(f"**Only {remaining} rookie picks remaining.**")
    elif remaining <= 0:
        output.append("**Rookie draft picking complete: All 4 rounds assigned.**")

    return "\n".join(output)


def write_log_file(final_name: str, final_text: str) -> None:
    """Write the output to a log file."""
    kicker_log_file = Path("logs") / f"{final_name}_log.txt"
    kicker_log_file.parent.mkdir(exist_ok=True)

    try:
        with kicker_log_file.open("a", encoding="utf-8") as f:
            f.write(final_text + "\n")
        click.secho(f"\n Output appended to {kicker_log_file}", fg="cyan")
    except IOError as e:
        click.secho(f"Error writing to log file: {e}", fg="red")


@click.command()
@click.argument("league_id", metavar="<League ID>")
@click.argument("draft_id", required=False, metavar="[Draft ID]")
@click.option("--name", "-n", default="Sleeper League", help="Custom name for the league.")
@click.option("--teams", "-t", default=12, type=int, help="Number of teams (picks per round).")
def run_kicker_scan(league_id: str, draft_id: Optional[str], name: str, teams: int) -> None:
    """Sleeper Kicker-to-Rookie Pick Converter.

    <League ID>: The numeric ID found in your Sleeper league URL.

    [Draft ID]: (Optional) The numeric ID for the draft. If omitted, the script finds the latest draft.
    """
    league_data = get_league_info(league_id)
    if not league_data:
        click.secho("Error: Could not find league with that ID.", fg="red")
        return

    final_name = league_data.get("name", name)

    draft_id = resolve_draft_id(league_id, draft_id)
    if not draft_id:
        return

    players = get_players()
    users_data, draft_picks = fetch_draft_data(league_id, draft_id)

    if not users_data or not draft_picks:
        click.secho("Error: Failed to retrieve league users or draft picks.", fg="red")
        return

    user_map = {u["user_id"]: u["display_name"] for u in users_data} if isinstance(users_data, list) else {}
    k_picks = (
        [p for p in draft_picks if players.get(p["player_id"], {}).get("position") in ("K", "P")]
        if isinstance(draft_picks, list)
        else []
    )

    final_text = generate_output(players, k_picks, user_map, teams, final_name)

    click.echo(final_text)
    write_log_file(final_name, final_text)


if __name__ == "__main__":
    run_kicker_scan()
