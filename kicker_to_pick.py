import requests
import json
import os
import time
import click
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
YEAR = "2026"
PLAYER_CACHE_FILE = "nfl_players.json"
CACHE_EXPIRY = 86400  # 24 hours

def fetch_data(url):
    try:
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        click.secho(f"Network Error: {e}", fg="red")
        return None

def get_players():
    """
    Integrated from sleeper_fetch_players logic:
    Checks if local player data exists; if not or if old, fetches from Sleeper.
    """
    if os.path.exists(PLAYER_CACHE_FILE):
        # Check if file is older than 24 hours
        file_age = time.time() - os.path.getmtime(PLAYER_CACHE_FILE)
        if file_age < CACHE_EXPIRY:
            with open(PLAYER_CACHE_FILE, 'r') as f:
                return json.load(f)

    print("Fetching fresh player data from Sleeper (this may take a moment)...")
    data = fetch_data("https://api.sleeper.app/v1/players/nfl")
    if data:
        with open(PLAYER_CACHE_FILE, 'w') as f:
            json.dump(data, f)
        return data
    return {}

def get_auto_draft_id(league_id):
    """Fetches the most recent draft ID for a given league."""
    drafts = fetch_data(f"https://api.sleeper.app/v1/league/{league_id}/drafts")
    if drafts and len(drafts) > 0:
        return drafts[0]['draft_id']
    return None

def get_league_info(league_id):
    """Fetches general league settings and name."""
    return fetch_data(f"https://api.sleeper.app/v1/league/{league_id}")

@click.command()
@click.argument('league_id', metavar='<League ID>')
@click.argument('draft_id', required=False, metavar='[Draft ID]')
@click.option('--name', '-n', default="Sleeper League", help="Custom name for the league.")
@click.option('--teams', '-t', default=12, type=int, help="Number of teams (picks per round).")
@click.option('--logfile', '-l', default="kicker_scan.log", help="File to append logs to.")
def run_kicker_scan(league_id, draft_id, name, teams, logfile):
    """
    Sleeper Kicker-to-Rookie Pick Converter.

    <League ID>: The numeric ID found in your Sleeper league URL.

    [Draft ID]: (Optional) The numeric ID for the draft. If omitted, the script finds the latest draft.
    """

    league_data = get_league_info(league_id)
    if not league_data:
        click.secho("❌ Error: Could not find league with that ID.", fg="red")
        return

    # Use API name if no flag provided
    final_name = league_data.get('name', 'Sleeper League')

    # 1. Resolve Draft ID
    if not draft_id:
        click.echo(f"Searching for latest draft in league {league_id}...")
        draft_id = get_auto_draft_id(league_id)
        if not draft_id:
            click.secho("Error: No drafts found for this league.", fg="red")
            return
        click.echo(f"Target Draft: {draft_id}")

    # 2. Fetch League & Draft Data
    players = get_players()
    users_data = fetch_data(f"https://api.sleeper.app/v1/league/{league_id}/users")
    draft_picks = fetch_data(f"https://api.sleeper.app/v1/draft/{draft_id}/picks")

    if not users_data or not draft_picks:
        click.secho("Error: Failed to retrieve league users or draft picks.", fg="red")
        return

    # 3. Process Logic
    user_map = {u['user_id']: u['display_name'] for u in users_data}
    k_picks = [p for p in draft_picks if players.get(p['player_id'], {}).get('position') == 'K']
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_allowed = 48
    
    # 4. Generate Output
    output = [
        f"**2026 Rookie Pick Tracker: {final_name}**",
        f"*Last Updated: {now}*",
        "---"
    ]

    for i, pick in enumerate(k_picks):
        if i >= total_allowed: break
        
        round_num = (i // teams) + 1
        pick_num = (i % teams) + 1
        label = f"{round_num}.{str(pick_num).zfill(2)}"
        
        username = user_map.get(pick['picked_by'], 'Unknown')
        p_meta = pick.get('metadata', {})
        player_name = f"{p_meta.get('first_name', '')} {p_meta.get('last_name', '')}"
        
        output.append(f"Pick {label} @{username} (via {player_name})")

        # Round Completion Logic
        if (i + 1) % teams == 0:
            output.append(f"**Round {round_num} is now full.**")
            output.append("---")
    output.append("\n")

    # Final Count Logic
    remaining = total_allowed - len(k_picks)
    if 0 < remaining <= 5:
        output.append(f"**Only {remaining} rookie picks remaining.**")
    elif remaining <= 0:
        output.append("**Rookie draft picking complete: All 4 rounds assigned.**")

    final_text = "\n".join(output)

    # 1. Print to Console
    click.echo(final_text)

    # 2. Append to Log File
    kicker_log_file = Path("logs") / f"{final_name}_log.txt"
    with open(kicker_log_file, "a", encoding="utf-8") as f:
        f.write(final_text + "\n")

    click.secho(f"\n Output appended to {kicker_log_file}", fg="cyan")

if __name__ == "__main__":
    run_kicker_scan()