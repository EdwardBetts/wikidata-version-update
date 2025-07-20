# Wikidata Version Update Tool

A command-line tool for automatically updating software version information on Wikidata. This tool adds new software release statements (version number and release date) with preferred rank while downgrading previous releases to normal rank.

## Features

- 🔄 Automatically updates software version information on Wikidata
- 📅 Adds release dates as qualifiers
- 🏆 Sets new versions as preferred rank and downgrades old ones to normal
- 🔐 Secure authentication using bot passwords
- 🧪 Dry-run mode to preview changes before applying
- 💾 Session management for efficient API usage

## Installation

```bash
git clone https://github.com/edwardbetts/wikidata-version-update
cd wikidata-version-update
pip install -e .
```

## Prerequisites

1. **Wikidata Account**: You need a Wikidata account
2. **Bot Password**: Create a bot password for secure API access

### Creating a Bot Password

Bot passwords are required for API authentication (main account login is deprecated). Follow these steps:

1. **Go to Bot Password Creation**:
   - Visit [Special:BotPasswords](https://www.wikidata.org/wiki/Special:BotPasswords) on Wikidata
   - Log in with your main Wikidata account if not already logged in

2. **Create a New Bot Password**:
   - Click "Create a new bot password"
   - Enter a bot name (e.g., "VersionUpdater" or "MyAppBot")
   - This will create a username in the format `YourUsername@BotName`

3. **Grant Required Permissions**:
   - Check "Edit existing pages" (required for updating version statements)

4. **Generate Password**:
   - Click "Create" to generate the bot password
   - **Important**: Copy and save the generated password immediately - it won't be shown again
   - The password will be a long random string like `abc123def456ghi789`

5. **Use Bot Credentials**:
   - Username: `YourUsername@BotName` (e.g., `JohnDoe@VersionUpdater`)
   - Password: The generated bot password (not your main account password)

For more details, see the [MediaWiki Bot Password documentation](https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:Bot_passwords).

## Configuration

The tool supports three ways to provide bot credentials (in priority order):

### 1. Command Line Options (highest priority)

```bash
wikidata-update --username "YourBot@YourApp" --password "your_password" --session-file "/tmp/session.json" --config-file "/path/to/config" Q305892 1.22.0 2024-01-15
```

### 2. Environment Variables (recommended for automation)

```bash
export WIKIDATA_BOT_USERNAME="YourBot@YourApp"
export WIKIDATA_BOT_PASSWORD="your_bot_password"
export WIKIDATA_SESSION_FILE="/var/run/wikidata/session.json"  # optional
export WIKIDATA_CONFIG_FILE="/path/to/config"  # optional
wikidata-update Q305892 1.22.0 2024-01-15
```

### 3. Config File (fallback for local development)

Create a `config` file in your working directory:

```ini
[bot]
username = YourUsername@YourBotName
password = your_bot_password_here
session_file = /custom/path/to/session.json  # optional
```

## Usage

### Running as a Module

If you've cloned the repository or installed from source, you can also run it as a Python module:

```bash
python3 -m wikidata_update Q305892 1.22.0 2024-01-15

# With options
python3 -m wikidata_update --config-file "/etc/wikidata/config" --dry-run Q305892 1.22.0 2024-01-15
```

### Basic Usage

```bash
wikidata-update Q305892 1.22.0 2024-01-15
```

This will:
1. Update the Wikidata item Q305892 (dpkg in this example)
2. Add version "1.22.0" as the new preferred version
3. Set the release date to 15 January, 2024
4. Downgrade any previous preferred versions to normal rank

### Dry Run

Preview changes without making them:

```bash
wikidata-update --dry-run Q305892 1.22.0 2024-01-15
```

### Arguments

- `QID`: Wikidata item ID (e.g., Q305892 for dpkg)
- `VERSION`: Version number (e.g., 1.22.0)
- `RELEASE_DATE`: Release date in ISO format (YYYY-MM-DD)

### Options

- `--dry-run`: Show what would be done without making changes
- `--username TEXT`: Wikidata bot username (overrides config file and environment)
- `--password TEXT`: Wikidata bot password (overrides config file and environment)
- `--session-file TEXT`: Path to session file (overrides config file and environment)
- `--config-file TEXT`: Path to config file (overrides environment variable and default)

## Examples

### Updating a Python package

```bash
# Update requests library to version 2.31.0
wikidata-update Q2984773 2.31.0 2023-05-22
```

### Updating with dry run first

```bash
# Preview the changes
wikidata-update --dry-run Q2984773 2.31.0 2023-05-22

# Apply the changes
wikidata-update Q2984773 2.31.0 2023-05-22
```

### Using in Release Scripts

For automated release scripts, use environment variables:

```bash
#!/bin/bash
export WIKIDATA_BOT_USERNAME="MyBot@MyApp"
export WIKIDATA_BOT_PASSWORD="$WIKIDATA_BOT_PASSWORD"  # from CI secrets

# Update version on release
wikidata-update Q123456 "$NEW_VERSION" "$(date +%Y-%m-%d)"
```

## How It Works

1. **Authentication**: Logs in using your bot password credentials
2. **Fetch Current Data**: Retrieves existing version statements from the Wikidata item
3. **Rank Management**: Downgrades any existing preferred version statements to normal rank
4. **Add New Version**: Creates a new version statement with:
   - The version number as the main value (P348)
   - Publication date as a qualifier (P577)
   - Preferred rank to indicate it's the current version

## Session Management

The tool automatically manages authentication sessions:
- Sessions are cached by default in `~/.wikidata_session.json`
- Session file location is configurable via `--session-file`, `WIKIDATA_SESSION_FILE` environment variable, or config file
- Automatically detects and handles expired sessions
- Securely stores session cookies with restricted file permissions (0600)

### Custom File Locations

Useful for different deployment scenarios:

```bash
# CI/automation with environment variables
export WIKIDATA_SESSION_FILE="/var/run/wikidata/session.json"
export WIKIDATA_CONFIG_FILE="/etc/wikidata/config"

# Docker container with mounted volumes
wikidata-update --config-file "/app/config/wikidata.conf" --session-file "/app/data/session.json" Q123456 1.0.0 2024-01-15

# Config file for project-specific sessions
echo "session_file = ./project-session.json" >> config
```

## Error Handling

The tool includes comprehensive error handling for:
- Invalid QID formats
- Invalid date formats
- Authentication failures
- API errors
- Network issues

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is designed for legitimate maintenance of software project information on Wikidata. Users are responsible for ensuring their edits comply with Wikidata's policies and guidelines.

## Support

If you encounter issues or have questions:
1. Check existing [issues](https://github.com/edwardbetts/wikidata-version-update/issues)
2. Create a new issue with detailed information about the problem
3. Include the output of `--dry-run` mode if applicable
