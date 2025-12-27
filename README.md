# twitch-go

A streamlined command-line tool for quickly going live on Twitch with preset configurations. Automatically updates your stream title, game category, and tags, then starts OBS streaming—all with a single command.

**Download the latest release** from [GitHub Releases](https://github.com/DevGW/twitch_go/releases)—a standalone executable with no Python installation required.

## Features

- 🎮 **Preset-based streaming** - Pre-configure settings for different games/streams
- 🚀 **One-command go-live** - Update Twitch metadata and start OBS with a single command
- 🏷️ **Automatic tag management** - Set tags per preset
- 📝 **Interactive prompts** - Customize title on-the-fly or use defaults
- ⚙️ **OBS integration** - Automatically start/stop OBS streaming via WebSocket
- 🔐 **Secure credential management** - Uses environment variables for sensitive data
- 📋 **Rig info command** - Quick access to streaming setup information

## Installation

### Quick Install (Recommended)

Download the latest release from [GitHub Releases](https://github.com/DevGW/twitch_go/releases). The executable is a standalone file that includes all dependencies—no Python installation required.

**Windows:**
- Download `twitch-go.exe` from the latest release assets
- Place it in a directory on your PATH, or run it directly

**Linux/macOS:**
- Download `twitch-go` from the latest release assets
- Make it executable: `chmod +x twitch-go`
- Place it in a directory on your PATH, or run it directly

### Requirements

- OBS Studio with WebSocket Server enabled
- Twitch Developer Application credentials
- (For source installation) Python 3.10 or higher

### Install from Source (Development)

If you want to run from source or contribute:

```bash
# Clone the repository
git clone https://github.com/DevGW/twitch_go.git
cd twitch_go

# Install dependencies
pip install -r requirements.txt

# Or install using the project configuration
pip install -e .

# Run directly
python twitch_go.py <preset>
```

### Building the Executable

To build a standalone executable for distribution:

```bash
pyinstaller --onefile --name twitch-go twitch_go_cli.py
```

The executable will be created in the `dist/` directory (which is gitignored). Upload the built executable to [GitHub Releases](https://github.com/DevGW/twitch_go/releases) for distribution.

## Quick Start

### 1. First-Time Setup

On first run, `twitch-go` will create a configuration directory at `~/.twitch-go/` and guide you through setup.

### 2. Configure Twitch Credentials

Create a `.env` file in `~/.twitch-go/` (or copy from `~/.twitch-go/.env.example`):

```env
# Twitch app credentials
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
TWITCH_REDIRECT_URI=http://localhost

# OBS WebSocket
OBS_WS_HOST=localhost
OBS_WS_PORT=4455
OBS_WS_PASSWORD=your_obs_password
```

**Getting Twitch Credentials:**
1. Go to [Twitch Developers](https://dev.twitch.tv/console/apps)
2. Create a new application
3. Set redirect URI to `http://localhost`
4. Copy Client ID and Client Secret

**Setting up OBS WebSocket:**
1. Open OBS Studio
2. Go to Tools → WebSocket Server Settings
3. Enable WebSocket server
4. Set a password (or leave blank)
5. Note the port (default: 4455)

### 3. Configure Presets

Edit `~/.twitch-go/config.yaml` to set up your streaming presets:

```yaml
version: 1

defaults:
  obs:
    auto_start: true
  prompts:
    confirm: true

presets:
  mygame:
    game:
      name: "My Game"
      category: "My Game"
    defaults:
      title: "My Game - Let's Play!"
      go_live_notification: "Going live with My Game!"
    tags:
      - Gaming
      - LiveStream
```

### 4. Authorize Twitch

On first use, `twitch-go` will prompt you to authorize via Twitch. Follow the instructions to complete OAuth.

## Usage

### Go Live with a Preset

```bash
twitch-go <preset>
```

Example:
```bash
twitch-go bf6
```

This will:
1. Prompt you to confirm/edit the stream title
2. Update your Twitch channel (title, game, tags)
3. Start OBS streaming (if `auto_start` is enabled)

### Available Commands

```bash
# Go live with a preset
twitch-go <preset>

# Show rig/streaming setup info
twitch-go intro                    # Show all sections (intro, rig, about)
twitch-go intro --rig-only         # Show only rig information
twitch-go intro --intro-only       # Show only intro message
twitch-go intro --about-only       # Show only about section

# Stop OBS streaming
twitch-go stop

# Edit configuration files
twitch-go edit [config|env|examples]

# Show usage and available presets
twitch-go
```

### Edit Configuration

```bash
# Edit main config.yaml
twitch-go edit config

# Edit .env file
twitch-go edit env

# Edit example files
twitch-go edit examples
```

## Configuration

### Config File Structure

The main configuration file is located at `~/.twitch-go/config.yaml`:

```yaml
version: 1

defaults:
  obs:
    auto_start: true    # Automatically start OBS when going live
  prompts:
    confirm: true       # Require confirmation before updating Twitch
  intro: |             # Welcome/introductory message (shown with 'twitch-go intro')
    Thanks for watching — and welcome if you're new here.
    Customize this section with your own welcome message.
  rig: |               # Hardware/streaming setup information (shown with 'twitch-go intro --rig-only')
    🖥 Gaming & Streaming Rig
    Customize this section with your hardware and streaming setup details.
  about: |             # About this channel information (shown with 'twitch-go intro --about-only')
    📌 About This Channel
    Customize this section with information about your channel and streaming style.

presets:
  preset_key:
    game:
      name: "Display Name"        # Display name for the game
      category: "Twitch Category"  # Exact Twitch category name
    defaults:
      title: "Stream Title"        # Default stream title
      go_live_notification: "..."  # Notification text (stored only)
    tags:
      - Tag1
      - Tag2
```

### Customizing Intro Information

The `intro`, `rig`, and `about` fields under `defaults` allow you to customize the information displayed by the `twitch-go intro` command. These fields use YAML multi-line string syntax (`|`), so you can format your content however you prefer. Each field is optional—if a field is missing, that section will be skipped when displaying all sections, or show a helpful message if requested with a specific flag.

### Preset Management

You can manage presets in two ways:

1. **Direct editing (Recommended)**: Edit `~/.twitch-go/config.yaml` directly. This is the simplest approach for most users.

2. **Individual preset files (Development)**: For developers maintaining the project, you can use individual preset files in `.historic_files/presets/` and merge them using `merge_presets.py`:

```bash
python merge_presets.py
```

This reads all `.yaml` files from `.historic_files/presets/` and merges them into the project root `config.yaml` (which is gitignored). Note: This is primarily for development/maintenance purposes. End users should edit `~/.twitch-go/config.yaml` directly.

## Project Structure

```
twitch_setup/
├── twitch_go.py          # Main application
├── twitch_go_cli.py      # CLI entry point (used for PyInstaller builds)
├── merge_presets.py      # Utility script to merge presets (optional, for development)
├── release.py            # Release automation script (build, archive, publish)
├── config.yaml           # Example configuration (project root, gitignored)
├── pyproject.toml        # Project metadata and dependencies
├── requirements.txt      # Python dependencies
├── README.md
└── .historic_files/      # Historical files (gitignored)
    ├── presets/          # Individual preset YAML files (for merge_presets.py)
    └── twitch_setup.py   # Legacy entry point
```

Note: 
- The `dist/` directory (where executables are built) is gitignored. Download releases from [GitHub Releases](https://github.com/DevGW/twitch_go/releases).
- User configuration is stored in `~/.twitch-go/config.yaml` (not in the project directory).
- The `config.yaml` in the project root is gitignored as it's user-specific.

## How It Works

1. **Configuration Loading**: Reads presets from `~/.twitch-go/config.yaml`
2. **OAuth Flow**: Handles Twitch authentication and token refresh automatically
3. **Interactive Prompts**: Allows customization of stream title before going live
4. **Twitch API**: Updates channel information via Twitch Helix API
5. **OBS Control**: Starts/stops streaming via OBS WebSocket API

## Troubleshooting

### OBS Connection Issues

- Ensure OBS WebSocket Server is enabled
- Verify the port and password match your `.env` settings
- Check that OBS Studio is running

### Twitch Authentication Errors

- Verify your Client ID and Client Secret are correct
- Ensure redirect URI matches exactly: `http://localhost`
- Delete `~/.twitch-go/tokens.json` and re-authenticate if needed

### Game Not Found

- Use the exact game/category name as it appears on Twitch
- Check spelling and capitalization
- Some games may have different names in the Twitch API

## Development

### Building Releases

#### Automated Release (Recommended)

Use the release script to build, package, and publish releases:

```bash
# Full release (build, archive, tag, GitHub release)
python release.py

# Build and archive only (no git tag or GitHub release)
python release.py --no-tag --no-release

# Build, archive, and tag (no GitHub release)
python release.py --no-release

# Override version
python release.py --version 1.2.3
```

The script will:
1. Read version from `pyproject.toml` (or use `--version` override)
2. Clean previous builds
3. Build executable with PyInstaller
4. Create release archive (zip for Windows, tar.gz for Linux/macOS)
5. Optionally create git tag
6. Optionally create GitHub release (requires [GitHub CLI](https://cli.github.com/))

**Requirements for GitHub releases:**
- Install GitHub CLI: `gh auth login`
- Or manually upload archives at [GitHub Releases](https://github.com/DevGW/twitch_go/releases/new)

#### Manual Build

To build manually:

```bash
pyinstaller --onefile --name twitch-go twitch_go_cli.py
```

The executable will be output to the `dist/` directory (which is gitignored). Upload the built executable to [GitHub Releases](https://github.com/DevGW/twitch_go/releases) for distribution.

### Running from Source

```bash
python twitch_go.py <preset>
```

### Dependencies

- `requests` - HTTP client for Twitch API
- `python-dotenv` - Environment variable management
- `pyyaml` - YAML configuration parsing
- `obsws-python` - OBS WebSocket client

### Build Requirements

- `pyinstaller` - For creating standalone executables

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

