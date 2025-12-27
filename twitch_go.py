#!/usr/bin/env python3
import sys
import os
import json
import requests
import yaml
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from obsws_python import ReqClient

# ---------------------------------------------------------------------
# UTF-8 hardening (Windows)
# ---------------------------------------------------------------------

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------
# App paths
# ---------------------------------------------------------------------

APP_DIR = Path.home() / ".twitch-go"

CONFIG_FILE = APP_DIR / "config.yaml"
CONFIG_EXAMPLE = APP_DIR / "config.example.yaml"

ENV_FILE = APP_DIR / ".env"
ENV_EXAMPLE = APP_DIR / ".env.example"

TOKEN_FILE = APP_DIR / "tokens.json"

# ---------------------------------------------------------------------
# Embedded examples (SAFE – no secrets)
# ---------------------------------------------------------------------

DEFAULT_CONFIG_EXAMPLE = """\
version: 1

defaults:
  obs:
    auto_start: true
  prompts:
    confirm: true
  intro: |
    Thanks for watching — and welcome if you're new here.
    
    Customize this section with your own welcome/introductory message.
  rig: |
    🖥 Gaming & Streaming Rig
    Customize this section with your hardware and streaming setup details.
    
    Example:
    • CPU: Your CPU model
    • GPU: Your GPU model
    • RAM: Your RAM specs
    • Streaming: Your streaming software and settings
  about: |
    📌 About This Channel
    Customize this section with information about your channel, streaming style, and what viewers can expect.

presets:
  example:
    game:
      name: Example Game
      category: Just Chatting
    defaults:
      title: "Example stream title"
      go_live_notification: "Example notification"
    tags:
      - Example
      - Streaming
"""

DEFAULT_ENV_EXAMPLE = """\
# Twitch app credentials
TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
TWITCH_REDIRECT_URI=http://localhost

# OBS WebSocket
OBS_WS_HOST=localhost
OBS_WS_PORT=4455
OBS_WS_PASSWORD=
"""

# ---------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------

def bootstrap():
    first_run = False

    if not APP_DIR.exists():
        APP_DIR.mkdir(parents=True)
        first_run = True

    if not CONFIG_EXAMPLE.exists():
        CONFIG_EXAMPLE.write_text(DEFAULT_CONFIG_EXAMPLE, encoding="utf-8")

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG_EXAMPLE, encoding="utf-8")
        first_run = True

    if not ENV_EXAMPLE.exists():
        ENV_EXAMPLE.write_text(DEFAULT_ENV_EXAMPLE, encoding="utf-8")

    if first_run:
        print(f"""
Initialized twitch-go configuration directory:

  {APP_DIR}

Next steps:
1) Edit: {CONFIG_FILE}
2) Copy: {ENV_EXAMPLE.name} → {ENV_FILE.name}
3) Fill in Twitch + OBS credentials
4) Re-run twitch-go
""")
        sys.exit(0)

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def die(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)

def prompt(label, default):
    print(f"\n{label}:")
    print(f"  {default}")
    v = input("Enter value (or press Enter to accept): ").strip()
    return v if v else default

def open_editor(path: Path):
    editor = (
        os.environ.get("EDITOR")
        or os.environ.get("VISUAL")
        or ("notepad.exe" if os.name == "nt" else "vi")
    )
    subprocess.run([editor, str(path)])

# ---------------------------------------------------------------------
# Environment / Secrets
# ---------------------------------------------------------------------

bootstrap()

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    print("WARNING: ~/.twitch-go/.env not found — relying on OS environment variables")

try:
    CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
    CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
    REDIRECT_URI = os.environ["TWITCH_REDIRECT_URI"]
except KeyError as e:
    die(f"Missing required environment variable: {e}")

OBS_HOST = os.environ.get("OBS_WS_HOST", "localhost")
OBS_PORT = int(os.environ.get("OBS_WS_PORT", 4455))
OBS_PASSWORD = os.environ.get("OBS_WS_PASSWORD")

# ---------------------------------------------------------------------
# Twitch API constants
# ---------------------------------------------------------------------

API_BASE = "https://api.twitch.tv/helix"
OAUTH_BASE = "https://id.twitch.tv/oauth2"
SCOPES = "channel:manage:broadcast"

# ---------------------------------------------------------------------
# Config handling
# ---------------------------------------------------------------------

def load_config():
    return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))

def print_intro_info(rig_only=False, intro_only=False, about_only=False):
    """Print rig/streaming setup information from config."""
    cfg = load_config()
    defaults = cfg.get("defaults", {})
    
    intro_text = defaults.get("intro", "").strip()
    rig_text = defaults.get("rig", "").strip()
    about_text = defaults.get("about", "").strip()
    
    # Determine what to display based on flags
    if rig_only:
        if not rig_text:
            print("No rig information configured. Add a 'rig' field under 'defaults' in your config.yaml")
            return
        print(rig_text)
    elif intro_only:
        if not intro_text:
            print("No intro information configured. Add an 'intro' field under 'defaults' in your config.yaml")
            return
        print(intro_text)
    elif about_only:
        if not about_text:
            print("No about information configured. Add an 'about' field under 'defaults' in your config.yaml")
            return
        print(about_text)
    else:
        # Show all fields in order: intro → rig → about
        output_parts = []
        if intro_text:
            output_parts.append(intro_text)
        if rig_text:
            output_parts.append(rig_text)
        if about_text:
            output_parts.append(about_text)
        
        if not output_parts:
            print("No intro information configured. Add 'intro', 'rig', and/or 'about' fields under 'defaults' in your config.yaml")
            return
        
        print("\n\n".join(output_parts))

def print_usage(cfg):
    print("""
Usage:
  twitch-go <preset>        Go live using a preset
  twitch-go edit [target]   Edit config files
  twitch-go stop            Stop OBS streaming
  twitch-go intro           Show rig/streaming setup info (all sections)
  twitch-go intro --rig-only      Show only rig information
  twitch-go intro --intro-only    Show only intro message
  twitch-go intro --about-only    Show only about section

Edit targets:
  config    Edit main config.yaml (default)
  env       Edit secrets .env
  examples  Edit example files

Presets:
""")
    for key, preset in cfg["presets"].items():
        print(f"  {key:<10} → {preset['game']['name']}")

def get_preset(cfg, key):
    try:
        return cfg["presets"][key]
    except KeyError:
        die(f"Unknown preset: {key}")

# ---------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------

def auth_url():
    return (
        f"{OAUTH_BASE}/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
    )

def exchange_code(code):
    r = requests.post(
        f"{OAUTH_BASE}/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
    )
    r.raise_for_status()
    return r.json()

def refresh_tokens(refresh_token):
    r = requests.post(
        f"{OAUTH_BASE}/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    r.raise_for_status()
    return r.json()

def load_tokens():
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text())

def save_tokens(tokens):
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))

# ---------------------------------------------------------------------
# Twitch API helpers
# ---------------------------------------------------------------------

def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json",
    }

def get_broadcaster_id(token):
    r = requests.get(f"{API_BASE}/users", headers=headers(token))
    r.raise_for_status()
    return r.json()["data"][0]["id"]

def get_game_id(token, name):
    r = requests.get(
        f"{API_BASE}/games",
        headers=headers(token),
        params={"name": name},
    )
    r.raise_for_status()
    data = r.json()["data"]
    if not data:
        die(f"Game not found on Twitch: {name}")
    return data[0]["id"]

def update_channel(token, broadcaster_id, payload):
    r = requests.patch(
        f"{API_BASE}/channels",
        headers=headers(token),
        params={"broadcaster_id": broadcaster_id},
        json=payload,
    )
    r.raise_for_status()

# ---------------------------------------------------------------------
# OBS
# ---------------------------------------------------------------------

def start_obs():
    if not OBS_PASSWORD:
        die("OBS_WS_PASSWORD not set")

    obs = ReqClient(
        host=OBS_HOST,
        port=OBS_PORT,
        password=OBS_PASSWORD,
        timeout=5,
    )

    status = obs.get_stream_status()
    if not status.output_active:
        obs.start_stream()
        print("✓ OBS stream started")

def stop_obs():
    if not OBS_PASSWORD:
        die("OBS_WS_PASSWORD not set")

    obs = ReqClient(
        host=OBS_HOST,
        port=OBS_PORT,
        password=OBS_PASSWORD,
        timeout=5,
    )

    status = obs.get_stream_status()
    if status.output_active:
        obs.stop_stream()
        print("✓ OBS stream stopped")
    else:
        print("OBS stream is not running")

# ---------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------

def edit_command(arg=None):
    if arg in (None, "config"):
        open_editor(CONFIG_FILE)
    elif arg == "env":
        open_editor(ENV_FILE)
    elif arg == "examples":
        open_editor(CONFIG_EXAMPLE)
        open_editor(ENV_EXAMPLE)
    else:
        die("Usage: twitch-go edit [config|env|examples]")

def run_preset(cfg, key):
    preset = get_preset(cfg, key)

    tokens = load_tokens()
    if not tokens:
        print("Authorize once using this URL:\n")
        print(auth_url())
        code = input("\nPaste ?code= value:\n> ").strip()
        tokens = exchange_code(code)
        save_tokens(tokens)

    try:
        access_token = tokens["access_token"]
        broadcaster_id = get_broadcaster_id(access_token)
    except requests.HTTPError:
        tokens = refresh_tokens(tokens["refresh_token"])
        save_tokens(tokens)
        access_token = tokens["access_token"]
        broadcaster_id = get_broadcaster_id(access_token)

    title = prompt("Default title", preset["defaults"]["title"])
    prompt(
        "Go-live notification (stored only)",
        preset["defaults"]["go_live_notification"],
    )

    tags = preset.get("tags", [])
    if tags:
        print("\nTags:")
        print(", ".join(tags))

    if cfg["defaults"]["prompts"].get("confirm", True):
        if input("\nProceed? [Y/n]: ").lower() == "n":
            die("Aborted")

    payload = {
        "title": title,
        "game_id": get_game_id(access_token, preset["game"]["category"]),
    }

    if tags:
        payload["tags"] = tags

    update_channel(access_token, broadcaster_id, payload)
    print("✓ Twitch metadata updated")

    if cfg["defaults"]["obs"].get("auto_start", True):
        start_obs()

    print("✓ Go live complete")

# ---------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------

def main():
    cfg = load_config()
    args = sys.argv[1:]

    if not args:
        print_usage(cfg)
        return

    cmd = args[0]

    if cmd == "edit":
        edit_command(args[1] if len(args) > 1 else None)
        return

    if cmd == "stop":
        stop_obs()
        return

    if cmd == "intro":
        # Parse flags for intro command
        rig_only = "--rig-only" in args
        intro_only = "--intro-only" in args
        about_only = "--about-only" in args
        print_intro_info(rig_only=rig_only, intro_only=intro_only, about_only=about_only)
        return

    if cmd in cfg["presets"]:
        run_preset(cfg, cmd)
        return

    die(f"Unknown command or preset: {cmd}")

if __name__ == "__main__":
    main()
