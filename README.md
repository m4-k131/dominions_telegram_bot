# The Pantokrators Herold 
*A Dynamic Discord/Telegram Bot for Dominions 6*


**The Pantokrators Herold** is a Python-based bot that monitors Illwinter's Dominions 6 multiplayer servers. It acts as a mechanical scout, allowing users to subscribe to specific games via Telegram commands, track turn cycles, and receive alerts when nations submit their orders.

## Features

* **🦟 Dynamic Subscriptions:** Add or remove games directly from Telegram chat.
* **⚔️ Turn Notifications:** Instant alerts when a new turn begins.
* **📜 Order Tracking:** Notifications when a specific nation marks their turn as "Turn played".
* **🌍 Multi-Server Support:** Works with the official server or custom URLs (e.g., Ulm, Snek).
* **📊 Instant Status:** Returns the current turn number and list of unfinished nations immediately upon subscribing.
* **💾 Persistence:** Remembers subscriptions and turn numbers across restarts via JSON caching.
* **💀 Safety:** Automatically stops monitoring games that return 404 errors (Game Over).

## Prerequisites

* Python 3.8+
* A Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Installation

1.  **Clone or download** this folder.
2.  **Install dependencies:**
    ```bash
    pip install requests beautifulsoup4
    ```
3.  Ensure you have both script files in the same directory:
    * `dom6_monitor.py` (Main executable)
    * `dom6_lib.py` (Library functions)

## Configuration

### 1. `config.json`
Create a file named `config.json` in the script directory. This sets the default server if you only provide a game name (instead of a full URL).

```json
{
  "base_game_url": "http://ulm.illwinter.com/dom6/server"
}
```

### 2. Environment Variable

To keep your bot token secure, export it as an environment variable.

* **Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-YourTokenHere"
```


* **Windows (CMD):**
```cmd
set TELEGRAM_BOT_TOKEN=123456:ABC-YourTokenHere
```


* **Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="123456:ABC-YourTokenHere"
```



## Usage

### Running the Bot

You must provide a check interval in minutes using the `--minutes` or `-m` flag.

```bash
# Run continuously, checking every 5 minutes
python dom6_monitor.py --minutes 5
```

*Note: The script enforces a minimum interval of 1 minute to prevent server flooding.*

### Telegram Commands

Once the bot is running, interact with it in your Telegram chat:

| Command | Usage | Description |
| --- | --- | --- |
| **Start** | `start <name>` | Subscribe to a game using the default base URL. |
| **Start (URL)** | `start <full_url>` | Subscribe to a game using a specific link (e.g., Ulm/Snek). |
| **Stop** | `stop <name>` | Unsubscribe from updates for a specific game. |

#### Examples:

> **User:** `start te26`

> **The Pantokrators Herold:**
> ✅ Game found! Subscribed to **te26**.
> 📊 **Current Status**
> Turn: **81**
> ⏳ **Waiting (3):** Arcoscephale, Caelum, Berytos
> [Link to Status Page]

> **User:** `start http://ulm.illwinter.com/dom6/server/mygame.html`

> **The Pantokrators Herold:** ✅ Game found! Subscribed to **mygame**.

## File Structure

* `dom6_monitor.py`: The main orchestrator. Handles the loop and command parsing.
* `dom6_lib.py`: The core logic. Handles HTML parsing, networking, and JSON management.
* `config.json`: Configuration settings.
* `cached_states/`: A directory created automatically to store `.json` files for every subscribed game.

## Troubleshooting

* **Bot doesn't reply:** Ensure the script is running in your terminal and `TELEGRAM_BOT_TOKEN` is set correctly.
* **"Game not found":** If using `start <name>`, check if `base_game_url` in `config.json` matches the server hosting your game. If not, use the full URL.
* **Duplicate Notifications:** Ensure you don't have multiple instances of the script running simultaneously.

