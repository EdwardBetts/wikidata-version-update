#!/usr/bin/python3
"""Wikidata Version Update Tool."""

import configparser
import json
import os
import sys
import typing
from datetime import datetime
from pathlib import Path

import click
import requests

__version__ = "0.1.0"

StrDict = dict[str, typing.Any]

# Configuration
url = "https://www.wikidata.org/w/api.php"
headers = {"User-Agent": "update-wikidata/0.1"}

# Config file location
CONFIG_FILE = Path("config")
DEFAULT_SESSION_FILE = Path.home() / ".wikidata_session.json"


def load_config(
    username: str | None = None,
    password: str | None = None,
    session_file: str | None = None,
    config_file: str | None = None,
) -> dict[str, str]:
    """Load bot credentials from config file, environment variables, or command line args.

    Config file location priority:
    1. config_file parameter (command line --config-file)
    2. WIKIDATA_CONFIG_FILE environment variable
    3. Default 'config' file in current directory
    """
    # If both username and password provided via command line, use them
    if username and password:
        result = {
            "bot_username": username,
            "bot_password": password,
        }
        if session_file:
            result["session_file"] = session_file
        return result

    # Try environment variables first
    env_username = os.getenv("WIKIDATA_BOT_USERNAME")
    env_password = os.getenv("WIKIDATA_BOT_PASSWORD")

    if env_username and env_password:
        result = {
            "bot_username": env_username,
            "bot_password": env_password,
        }
        # Check for session file in environment
        env_session_file = session_file or os.getenv("WIKIDATA_SESSION_FILE")
        if env_session_file:
            result["session_file"] = env_session_file
        return result

    # Fall back to config file
    try:
        # Determine config file path
        config_file_path = Path(
            config_file or os.getenv("WIKIDATA_CONFIG_FILE") or CONFIG_FILE
        )

        config = configparser.ConfigParser()
        config.read(config_file_path)

        if "bot" not in config:
            raise ValueError("Config must contain [bot] section")

        bot_section = config["bot"]
        if "username" not in bot_section or "password" not in bot_section:
            raise ValueError("[bot] section must contain 'username' and 'password'")

        result = {
            "bot_username": bot_section["username"],
            "bot_password": bot_section["password"],
        }

        # Check for session file in config or environment or command line
        config_session_file = (
            session_file
            or os.getenv("WIKIDATA_SESSION_FILE")
            or bot_section.get("session_file")
        )
        if config_session_file:
            result["session_file"] = config_session_file

        return result
    except FileNotFoundError:
        print(
            f"Config file {config_file_path} not found and no environment variables set."
        )
        print("Please either:")
        print("1. Create a config file with your bot credentials:")
        print("   [bot]")
        print("   username = YourBot@YourApp")
        print("   password = your_password")
        print("2. Set environment variables:")
        print("   export WIKIDATA_BOT_USERNAME=YourBot@YourApp")
        print("   export WIKIDATA_BOT_PASSWORD=your_password")
        print("3. Use command line options: --username and --password")
        print("\nConfig file location can be configured with:")
        print("- Command line: --config-file /path/to/config")
        print("- Environment: export WIKIDATA_CONFIG_FILE=/path/to/config")
        print("\nSession file location can be configured with:")
        print("- Command line: --session-file /path/to/session.json")
        print("- Environment: export WIKIDATA_SESSION_FILE=/path/to/session.json")
        print("- Config file: session_file = /path/to/session.json")
        sys.exit(1)
    except (configparser.Error, ValueError) as e:
        print(f"Error reading config file {config_file_path}: {e}")
        sys.exit(1)


def save_session(session_data: StrDict, session_file_path: Path) -> None:
    """Save session data to file."""
    with open(session_file_path, "w") as f:
        json.dump(session_data, f, indent=2)
    session_file_path.chmod(0o600)


def load_session(session_file_path: Path) -> StrDict | None:
    """Load session data from file."""
    try:
        if session_file_path.exists():
            with open(session_file_path, "r") as f:
                result = json.load(f)
                if isinstance(result, dict):
                    return result
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def get_login_token(session: requests.Session) -> str:
    """Get a login token from the API."""
    data = wikidata_get(session, action="query", meta="tokens", type="login")

    token = data["query"]["tokens"]["logintoken"]
    if isinstance(token, str):
        return token
    raise ValueError("Invalid token type returned from API")


def login_with_bot_password(username: str, password: str) -> requests.Session:
    """Login using bot password and return authenticated session."""
    session = requests.Session()
    session.headers.update(headers)

    # Get login token
    login_token = get_login_token(session)

    # Perform login
    login_data = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": login_token,
        "format": "json",
    }

    response = session.post(url, data=login_data)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise ValueError(f"Login failed: {data['error']}")

    login_result = data.get("login", {})
    if login_result.get("result") != "Success":
        raise ValueError(f"Login failed: {login_result.get('reason', 'Unknown error')}")

    print(f"Successfully logged in as: {login_result.get('lgusername', username)}")
    return session


def get_authenticated_session(
    username: str | None = None,
    password: str | None = None,
    session_file: str | None = None,
    config_file: str | None = None,
) -> requests.Session:
    """Get an authenticated session."""
    config = load_config(username, password, session_file, config_file)

    # Determine session file path
    session_file_path = Path(config.get("session_file", DEFAULT_SESSION_FILE))

    # Try to load existing session
    session_data = load_session(session_file_path)
    if session_data:
        print("Found existing session, testing...")
        session = requests.Session()
        session.headers.update(headers)
        session.cookies.update(session_data.get("cookies", {}))

        try:
            data = wikidata_get(session, action="query", meta="userinfo")
            if "query" in data and "userinfo" in data["query"]:
                user = data["query"]["userinfo"]
                if user.get("name") and user.get("name") != "":
                    print(f"Session valid! Logged in as: {user.get('name')}")
                    return session
        except (requests.RequestException, ValueError):
            pass

        print("Existing session invalid, logging in again...")
    else:
        print("No existing session found, logging in...")

    # Login with bot password
    session = login_with_bot_password(config["bot_username"], config["bot_password"])

    # Save session cookies
    session_data = {"cookies": dict(session.cookies)}
    save_session(session_data, session_file_path)

    return session


def wikidata_get(session: requests.Session, **kwargs: typing.Any) -> StrDict:
    """Make authenticated GET request to Wikidata API."""
    params: dict[str, typing.Any] = {"format": "json", "formatversion": 2} | kwargs

    r = session.get(url, params=params)

    try:
        data = r.json()
    except json.JSONDecodeError:
        print("Failed to parse JSON response:")
        print(r.text)
        raise

    if "error" in data:
        print(f"API Error: {data['error']}")
        raise ValueError(f"Wikidata API error: {data['error']}")

    if isinstance(data, dict):
        return data
    raise ValueError("Invalid response type from API")


def wikidata_post(session: requests.Session, **kwargs: typing.Any) -> StrDict:
    """Make authenticated POST request to Wikidata API."""
    params = {"format": "json", "formatversion": 2} | kwargs

    r = session.post(url, data=params)

    try:
        data = r.json()
    except json.JSONDecodeError:
        print("Failed to parse JSON response:")
        print(r.text)
        raise

    if "error" in data:
        print(f"API Error: {data['error']}")
        raise ValueError(f"Wikidata API error: {data['error']}")

    if isinstance(data, dict):
        return data
    raise ValueError("Invalid response type from API")


def get_entity(session: requests.Session, qid: str) -> StrDict:
    data = wikidata_get(session, action="wbgetentities", ids=qid)
    return data


def get_version_statements(session: requests.Session, qid: str) -> list[StrDict]:
    """Get all existing software version (P348) statements for an entity."""
    entity_data = get_entity(session, qid)
    entity = entity_data["entities"][qid]

    if "claims" not in entity or "P348" not in entity["claims"]:
        return []

    claims = entity["claims"]["P348"]
    if isinstance(claims, list):
        return claims
    return []


def downgrade_version_ranks(
    session: requests.Session, version_statements: list[StrDict]
) -> None:
    """Downgrade all version statements from preferred to normal rank."""
    csrf_token = get_csrf_token(session)

    for statement in version_statements:
        if statement.get("rank") == "preferred":
            claim_id = statement["id"]
            print(f"Downgrading claim {claim_id} to normal rank...")

            wikidata_post(
                session,
                action="wbsetclaimrank",
                claim=claim_id,
                rank="normal",
                token=csrf_token,
            )


def add_version_statement(
    session: requests.Session, qid: str, version: str, release_date: str
) -> None:
    """Add a new software version statement with preferred rank and release date qualifier."""
    csrf_token = get_csrf_token(session)

    # Create the main version claim
    print(f"Adding version {version} to {qid}...")

    data = wikidata_post(
        session,
        action="wbcreateclaim",
        entity=qid,
        property="P348",  # software version
        snaktype="value",
        value=json.dumps(version),
        token=csrf_token,
    )

    claim_id = data["claim"]["id"]
    print(f"Created claim {claim_id}")

    # Set the rank to preferred
    wikidata_post(
        session,
        action="wbsetclaimrank",
        claim=claim_id,
        rank="preferred",
        token=csrf_token,
    )
    print("Set rank to preferred")

    # Add publication date qualifier
    wikidata_post(
        session,
        action="wbsetqualifier",
        claim=claim_id,
        property="P577",  # publication date
        snaktype="value",
        value=json.dumps(
            {
                "time": f"+{release_date}T00:00:00Z",
                "timezone": 0,
                "before": 0,
                "after": 0,
                "precision": 11,  # day precision
                "calendarmodel": "http://www.wikidata.org/entity/Q1985727",  # Gregorian calendar
            }
        ),
        token=csrf_token,
    )
    print("Added publication date qualifier")


def get_csrf_token(session: requests.Session) -> str:
    """Get a CSRF token for editing."""
    data = wikidata_post(session, action="query", meta="tokens", type="csrf")
    token = data["query"]["tokens"]["csrftoken"]
    if isinstance(token, str):
        return token
    raise ValueError("Invalid CSRF token type returned from API")


def validate_qid(qid: str) -> str:
    """Validate that QID is in correct format."""
    if not qid.startswith("Q") or not qid[1:].isdigit():
        raise click.BadParameter("QID must be in format Q123456")
    return qid


def validate_date(date_str: str) -> str:
    """Validate that date is in ISO format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise click.BadParameter("Date must be in ISO format (YYYY-MM-DD)")


@click.command()
@click.argument("qid", callback=lambda ctx, param, value: validate_qid(value))
@click.argument("version")
@click.argument("release_date", callback=lambda ctx, param, value: validate_date(value))
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
@click.option(
    "--username", help="Wikidata bot username (overrides config file and environment)"
)
@click.option(
    "--password", help="Wikidata bot password (overrides config file and environment)"
)
@click.option(
    "--session-file",
    help="Path to session file (overrides config file and environment)",
)
@click.option(
    "--config-file",
    help="Path to config file (overrides environment variable and default)",
)
def main(
    qid: str,
    version: str,
    release_date: str,
    dry_run: bool,
    username: str | None,
    password: str | None,
    session_file: str | None,
    config_file: str | None,
) -> None:
    """Update software version information on Wikidata.

    QID: Wikidata item ID (e.g., Q305892 for dpkg)
    VERSION: Version number (e.g., 1.22.0)
    RELEASE_DATE: Release date in ISO format (YYYY-MM-DD)
    """
    try:
        session = get_authenticated_session(
            username, password, session_file, config_file
        )

        print(f"Updating software version for {qid}")
        print(f"New version: {version}")
        print(f"Release date: {release_date}")

        if dry_run:
            print("\n--- DRY RUN MODE ---")

        # Get existing version statements
        print("\nGetting existing version statements...")
        version_statements = get_version_statements(session, qid)

        if version_statements:
            print(f"Found {len(version_statements)} existing version statements")

            # Show current preferred versions
            preferred_versions = [
                s for s in version_statements if s.get("rank") == "preferred"
            ]
            if preferred_versions:
                print("Current preferred versions:")
                for stmt in preferred_versions:
                    version_val = stmt["mainsnak"]["datavalue"]["value"]
                    print(f"  - {version_val}")

            if not dry_run:
                # Downgrade existing preferred versions to normal rank
                print("\nDowngrading previous preferred versions to normal rank...")
                downgrade_version_ranks(session, version_statements)
        else:
            print("No existing version statements found")

        if not dry_run:
            # Add new version statement with preferred rank
            print(f"\nAdding new version statement...")
            add_version_statement(session, qid, version, release_date)

            print(f"\n✅ Successfully updated {qid} with version {version}")
        else:
            print(
                f"\n[DRY RUN] Would add version {version} with preferred rank and release date {release_date}"
            )

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
