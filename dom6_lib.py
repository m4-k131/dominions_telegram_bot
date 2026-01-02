import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# --- Custom Exceptions ---
class GameNotFoundError(Exception):
    """Raised when the game page returns a 404."""

    pass


# --- 1. Networking & Parsing (Game) ---


def fetch_game_html(url):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            raise GameNotFoundError(f"Game page not found: {url}")
        raise err


def parse_game_state(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="basictab")

    if not table:
        return None

    rows = table.find_all("tr")
    if not rows:
        return None

    # Header format: "te26, turn 81"
    header_text = rows[0].get_text(strip=True)
    turn_match = re.search(r"turn\s+(\d+)", header_text, re.IGNORECASE)

    state = {
        "game_name": header_text.split(",")[0].strip(),
        "turn": int(turn_match.group(1)) if turn_match else 0,
        "nations": {},
        "subscribers": [],  # Default empty list for new games
    }

    # Parse Nation Rows
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            # ORIGINAL: nation_name = cols[0].get_text(strip=True)

            # FIXED: Get text, split by comma, take the first part
            raw_name = cols[0].get_text(strip=True)
            nation_name = raw_name.split(",")[0].strip()

            status = cols[1].get_text(strip=True)
            state["nations"][nation_name] = status

    return state


# --- 2. Storage (JSON Handling) ---


def _get_filepath(game_name, cache_dir):
    safe_name = "".join([c for c in game_name if c.isalnum() or c in (" ", "-", "_")]).strip()
    return Path(cache_dir) / f"{safe_name}.json"


def load_state(game_name, cache_dir):
    """Loads the state dictionary from JSON."""
    filepath = _get_filepath(game_name, cache_dir)
    if filepath.exists():
        try:
            with open(filepath) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    return None


def save_state(state, cache_dir):
    """Saves the state dictionary to JSON."""
    filepath = _get_filepath(state["game_name"], cache_dir)
    with open(filepath, "w") as f:
        json.dump(state, f, indent=4)


def add_subscriber(game_name, chat_id, cache_dir):
    """Adds a chat_id to the subscribers list of a game."""
    state = load_state(game_name, cache_dir)
    if not state:
        return False  # Game doesn't exist locally yet

    if "subscribers" not in state:
        state["subscribers"] = []

    if chat_id not in state["subscribers"]:
        state["subscribers"].append(chat_id)
        save_state(state, cache_dir)
    return True


def remove_subscriber(game_name, chat_id, cache_dir):
    """Removes a chat_id from the subscribers list."""
    state = load_state(game_name, cache_dir)
    if not state:
        return False

    if "subscribers" in state and chat_id in state["subscribers"]:
        state["subscribers"].remove(chat_id)
        save_state(state, cache_dir)
        return True
    return False


# --- 3. Telegram Logic ---


def get_telegram_updates(bot_token, offset=None):
    """Fetches new messages from Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": 0, "limit": 100}
    if offset:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram polling error: {e}")
        return None


def send_telegram(bot_token, chat_ids, message):
    """Sends a message to a list of chat IDs."""
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Deduplicate IDs just in case
    for chat_id in set(chat_ids):
        try:
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            requests.post(api_url, json=payload)
        except Exception as e:
            print(f"Failed to notify chat {chat_id}: {e}")


# --- 4. Logic & Formatting ---


def generate_change_messages(prev_state, curr_state, url):
    if not prev_state:
        return []

    messages = []
    game_name = curr_state["game_name"]
    prev_turn = prev_state.get("turn", 0)
    curr_turn = curr_state.get("turn", 0)

    if curr_turn > prev_turn:
        msg = f"⚔️ <b>NEW TURN!</b> ⚔️\n\nGame: <b>{game_name}</b>\nTurn: {curr_turn}\n<a href='{url}'>Link to Status Page</a>"
        messages.append(msg)

    elif curr_turn == prev_turn:
        changes = []
        for nation, status in curr_state["nations"].items():
            prev_status = prev_state["nations"].get(nation)
            if prev_status != status and status == "Turn played":
                changes.append(f"📜 <b>{nation}</b> sent their orders.")

        if changes:
            full_msg = f"🔮 <b>The Pantokrators Herold Reports</b> ({game_name})\n" + "\n".join(changes)
            messages.append(full_msg)

    return messages
