# Dominions 6 Game Monitor

A Python script to monitor Illwinter's Dominions 6 status page. It tracks the game state, detects when a new turn begins or when players finish their turns, and sends notifications via a Telegram bot. 

## Features

- **Turn notifications**: Alerts when the turn timer advances. 
- **Player status**: Alerts when a specific nation finishes their turn (status changes to "Turn played"). 
- **Persistent tracking**: Caches the game state to `cached_states/` to remember turn numbers between script restarts. 
- **Error handling**: Detects if the game page disappears (404 Not Found) and stops monitoring to prevent spam. 
- **Configurable interval**: Can run once or continuously at a set interval. 

## Prerequisites

- Python 3.x 
- A Telegram bot token (from [@BotFather](https://t.me/botfather)) 
- Target Telegram chat IDs (user or group IDs) 

## Installation

1. **Clone or download** this repository. 
2. **Install dependencies**: 

```
pip install requests beautifulsoup4
```

## Configuration

### 1. Config file

Create a file named `config.json` in the project root: 

```
{
"game_status_url": "http://www.illwinter.com/dom6/server.html",
"chat_ids": ["123456789", "-987654321"]
}
```

### 2. Secret token

Export your Telegram bot token as an environment variable to keep it out of the repo. 

**Linux / macOS (bash/zsh):** 

```
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

**Windows (CMD):** 

```
set TELEGRAM_BOT_TOKEN=your_bot_token_here"
```

**Windows (PowerShell):** 

```
\$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

## Usage

### Run once

Useful for checking status manually or running via an external scheduler (like cron). 

```
python dom6_monitor.py
```

### Run continuously

Keeps the script running and checking every X minutes. 

```
# Check every 5 minutes
python dom6_monitor.py --minutes 5
```

The script enforces a minimum interval of 1 minute to respect the server. 

## File structure

- `dom6_monitor.py`: Main script. 
- `config.json`: Configuration settings. 
- `cached_states/`: Directory where JSON snapshots of the game state are stored. 
