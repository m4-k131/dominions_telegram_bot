import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import dom6_lib

# --- Configuration ---

CONFIG_FILE = 'config.json'
CACHE_DIR = Path("cached_states")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def get_bot_token():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN env var not set.")
        sys.exit(1)
    return token

# --- Command Handlers ---

def handle_start_command(bot_token, chat_id, input_text, default_base_url):
    """
    Accepts a game name OR a full URL.
    Saves the game and immediately reports the current status.
    """
    input_text = input_text.strip()
    if not input_text:
        dom6_lib.send_telegram(bot_token, [chat_id], "⚠️ Please specify a game name or URL.\nExample: <code>start te26</code>")
        return

    # 1. Determine the Target URL
    if input_text.startswith("http"):
        target_url = input_text
        # We don't know the name yet, the parser will get it
    else:
        target_url = f"{default_base_url.rstrip('/')}/{input_text}.html"

    try:
        # 2. Fetch & Verify
        html = dom6_lib.fetch_game_html(target_url)
        state = dom6_lib.parse_game_state(html)
        
        if not state:
            raise ValueError("Could not parse game data")

        # 3. Update State & Subscriber List
        state['url'] = target_url
        
        # Load existing subscribers if file exists
        existing_state = dom6_lib.load_state(state['game_name'], CACHE_DIR)
        
        if existing_state:
            state['subscribers'] = existing_state.get('subscribers', [])
        else:
            state['subscribers'] = []

        if chat_id not in state['subscribers']:
            state['subscribers'].append(chat_id)

        # 4. Save to disk
        dom6_lib.save_state(state, CACHE_DIR)
        
        # 5. Send Notifications
        # A) Confirmation
        dom6_lib.send_telegram(bot_token, [chat_id], f"✅ Game found! Subscribed to <b>{state['game_name']}</b>.")
        
        # B) Immediate Status Report
        # Identify nations that haven't played (Status is usually "-")
        unfinished = [n for n, s in state['nations'].items() if s == "-"]
        
        status_msg = (f"📊 <b>Current Status</b>\n"
                      f"Turn: <b>{state['turn']}</b>\n")
        
        if unfinished:
            # Join list with commas
            status_msg += f"⏳ <b>Waiting ({len(unfinished)}):</b> {', '.join(unfinished)}"
        else:
            status_msg += "✅ All turns played (processing?)"
            
        status_msg += f"\n<a href='{target_url}'>Link to Status Page</a>"
        
        dom6_lib.send_telegram(bot_token, [chat_id], status_msg)
        
    except dom6_lib.GameNotFoundError:
        dom6_lib.send_telegram(bot_token, [chat_id], f"❌ Game not found at:\n{target_url}")
    except Exception as e:
        print(f"Error verifying game {target_url}: {e}")
        dom6_lib.send_telegram(bot_token, [chat_id], "⚠️ Error accessing game. Check bot logs.")

def handle_stop_command(bot_token, chat_id, game_name):
    game_name = game_name.strip()
    if not game_name:
        dom6_lib.send_telegram(bot_token, [chat_id], "⚠️ Please specify a game name. Example: <code>stop te26</code>")
        return

    success = dom6_lib.remove_subscriber(game_name, chat_id, CACHE_DIR)
    if success:
        dom6_lib.send_telegram(bot_token, [chat_id], f"🗑️ Unsubscribed from <b>{game_name}</b>.")
    else:
        dom6_lib.send_telegram(bot_token, [chat_id], f"⚠️ You were not subscribed to <b>{game_name}</b>.")

# --- Periodic Check Logic ---

def check_all_subscribed_games(config, bot_token):
    """Iterates through all JSON files in CACHE_DIR and checks for updates."""
    default_base_url = config.get('base_game_url', 'http://www.illwinter.com/dom6')
    
    game_files = list(CACHE_DIR.glob("*.json"))
    
    for file_path in game_files:
        try:
            with open(file_path) as f:
                prev_state = json.load(f)
            
            game_name = prev_state.get('game_name')
            subscribers = prev_state.get('subscribers', [])
            
            if not subscribers:
                continue 

            # Get URL: Prefer the one saved in JSON
            target_url = prev_state.get('url')
            if not target_url:
                target_url = f"{default_base_url.rstrip('/')}/{game_name}.html"
            
            try:
                html = dom6_lib.fetch_game_html(target_url)
                curr_state = dom6_lib.parse_game_state(html)
                
                # Preserve meta-data
                curr_state['subscribers'] = subscribers
                curr_state['url'] = target_url 
                
                messages = dom6_lib.generate_change_messages(prev_state, curr_state, target_url)
                for msg in messages:
                    print(f"[{game_name}] Sending update to {len(subscribers)} subs.")
                    dom6_lib.send_telegram(bot_token, subscribers, msg)
                
                # Save new state
                dom6_lib.save_state(curr_state, CACHE_DIR)
                
            except dom6_lib.GameNotFoundError:
                print(f"[{game_name}] 404 Not Found at {target_url}")
            except Exception as e:
                print(f"[{game_name}] Check failed: {e}")
                
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

# --- Main Loop ---

def main():
    parser = argparse.ArgumentParser(description="The Iron Fly - Dynamic Dom6 Bot")
    parser.add_argument("--minutes", "-m", type=float, help="Interval for game status checks (min 1).")
    args = parser.parse_args()

    config = load_config()
    bot_token = get_bot_token()
    CACHE_DIR.mkdir(exist_ok=True)
    
    base_url = config.get('base_game_url', 'http://www.illwinter.com/dom6')

    # Telegram polling offset
    last_update_id = 0
    
    # Timing
    check_interval = max(60, int(args.minutes * 60)) if args.minutes else 0
    last_check_time = 0

    print("🦟 The Iron Fly is listening...")

    while True:
        # 1. Poll Telegram for Commands
        updates_data = dom6_lib.get_telegram_updates(bot_token, last_update_id + 1)
        
        if updates_data and updates_data.get('ok'):
            for update in updates_data.get('result', []):
                last_update_id = update['update_id']
                
                if 'message' in update and 'text' in update['message']:
                    text = update['message']['text'].strip()
                    chat_id = update['message']['chat']['id']
                    
                    if text.lower().startswith('start '):
                        input_arg = text[6:] # Name OR URL
                        handle_start_command(bot_token, chat_id, input_arg, base_url)
                    elif text.lower().startswith('stop '):
                        game_target = text[5:]
                        handle_stop_command(bot_token, chat_id, game_target)

        # 2. Poll Game Servers
        current_time = time.time()
        if check_interval > 0 and (current_time - last_check_time) > check_interval:
            print(f"⏰ Checking game states at {datetime.now().strftime('%H:%M:%S')}...")
            check_all_subscribed_games(config, bot_token)
            last_check_time = current_time

        time.sleep(1) 

if __name__ == "__main__":
    main()