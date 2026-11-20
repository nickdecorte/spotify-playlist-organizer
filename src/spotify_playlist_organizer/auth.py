"""Spotify sign-in: PKCE, no client secret."""

import os
from pathlib import Path

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyPKCE

SCOPES = " ".join([
    "user-library-read",
    "playlist-read-private",
    "playlist-modify-private",
])
TOKEN_DIR = Path.home() / ".cache" / "spotify-playlist-organizer"


class ConfigError(Exception):
    """A required setting is missing from the environment."""


def setting(name: str) -> str:
    """A required setting from the environment (`.env`)."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} is not set. Copy .env.example to .env, fill it in and run with "
            "`uv run --env-file .env spotify-playlist-organizer …` (see README).")
    return value


def client() -> spotipy.Spotify:
    """A Spotify client signed in as you; opens the browser the first time."""
    client_id = setting("SPOTIPY_CLIENT_ID")
    redirect_uri = setting("SPOTIPY_REDIRECT_URI")
    TOKEN_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    TOKEN_DIR.chmod(0o700)
    manager = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=SCOPES,
        cache_handler=CacheFileHandler(cache_path=str(TOKEN_DIR / "token.json")),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=manager)
