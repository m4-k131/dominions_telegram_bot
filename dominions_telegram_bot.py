import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)

CACHE_DIR = Path("cached_states")
CACHE_DIR.mkdir(exist_ok=True)

# --- Helper Functions ---


def send_telegram_message(message, config):
    """Sends a message to all configured chat IDs."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chat_id in config.get("chat_ids", []):
        try:
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")


def sanitize_filename(name):
    return "".join([c for c in name if c.isalnum() or c in (" ", "-", "_")]).strip()


def parse_status_page(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="basictab")

    if not table:
        return None

    rows = table.find_all("tr")
    if not rows:
        return None

    header_text = rows[0].get_text(strip=True)
    turn_match = re.search(r"turn\s+(\d+)", header_text, re.IGNORECASE)
    current_turn = int(turn_match.group(1)) if turn_match else 0
    game_name = header_text.split(",")[0].strip()

    nations_status = {}
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            nation_name = cols[0].get_text(strip=True)
            status = cols[1].get_text(strip=True)
            nations_status[nation_name] = status

    return {"game_name": game_name, "turn": current_turn, "nations": nations_status}


def get_state_file_path(game_name):
    safe_name = sanitize_filename(game_name)
    return CACHE_DIR / f"{safe_name}.json"


def process_turn_check(config):
    """
    Fetches data, compares with cache, and notifies if changed.
    Returns: True if monitoring should continue, False if a fatal error (404) occurred.
    """
    url = config.get("game_status_url")
    if not url:
        print("Error: 'game_status_url' missing in config.")
        return False

    # 1. Fetch
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            print(f"❌ 404 Not Found: {url}")
            msg = f"⚠️ <b>Game Monitor Stopped</b>\n\nThe status page returned a <b>404 Not Found</b>.\nThe game has likely finished or the URL is incorrect.\n<a href='{url}'>Link to Page</a>"
            send_telegram_message(msg, config)
            return False  # Stop monitoring
        else:
            print(f"HTTP Error: {err}")
            return True  # Retry next time
    except Exception as e:
        print(f"Network error fetching status page: {e}")
        return True  # Retry next time

    # 2. Parse
    current_state = parse_status_page(response.text)
    if not current_state:
        print("Error: Could not parse game data from HTML.")
        return True

    game_name = current_state["game_name"]
    state_file = get_state_file_path(game_name)

    # 3. Load Previous State
    previous_state = None
    if state_file.exists():
        try:
            with open(state_file) as f:
                previous_state = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Corrupt cache file for {game_name}, resetting.")

    # 4. Compare & Notify
    if previous_state:
        prev_turn = previous_state.get("turn", 0)
        curr_turn = current_state.get("turn", 0)
        # A) New Turn
        if curr_turn > prev_turn:
            msg = f"🚨 <b>NEW TURN!</b> 🚨\n\nGame: <b>{game_name}</b>\nTurn: {curr_turn}\n<a href='{url}'>Link to Status Page</a>"
            print(f"[{game_name}] New turn detected: {curr_turn}")
            send_telegram_message(msg)
        # B) Player Status Change
        elif curr_turn == prev_turn:
            changes = []
            for nation, status in current_state["nations"].items():
                prev_status = previous_state["nations"].get(nation)
                if prev_status != status and status == "Turn played":
                    changes.append(f"✅ <b>{nation}</b> finished their turn.")

            if changes:
                msg = f"📝 <b>Status Update</b> ({game_name})\n" + "\n".join(changes)
                print(f"[{game_name}] Status changes: {changes}")
                send_telegram_message(msg)
    else:
        print(f"[{game_name}] First run or no cache. Saving initial state.")

    # 5. Save New State
    with open(state_file, "w") as f:
        json.dump(current_state, f, indent=4)

    return True


# --- Main Execution ---


def main():
    parser = argparse.ArgumentParser(description="Monitor Dominions 6 game status.")
    parser.add_argument("--minutes", "-m", type=float, help="Run periodically every X minutes.")
    parser.add_argument("--config", "-c", type=str, help="Path of the JSON-Config")
    args = parser.parse_args()

    try:
        with open(args.config) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {args.config} not found.")
        sys.exit(1)

    if args.minutes is not None:
        interval_seconds = max(60, int(args.minutes * 60))
        print(f"Starting continuous monitor. Checking every {interval_seconds} seconds...")

        while True:
            print(f"Checking status at {datetime.now().strftime('%H:%M:%S')}...")
            should_continue = process_turn_check(config)

            if not should_continue:
                print("Stopping monitor due to fatal error (404).")
                break

            time.sleep(interval_seconds)
    else:
        print("Running single check...")
        process_turn_check(config)
        print("Done.")


if __name__ == "__main__":
    main()
