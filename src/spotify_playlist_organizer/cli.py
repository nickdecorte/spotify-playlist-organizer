"""The `spotify-playlist-organizer` command: fetch your liked songs, and turn the AI's sorting
of them into playlists."""

import argparse
import json
import sys
from pathlib import Path

from spotipy import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from spotify_playlist_organizer import auth, library, playlists


def export_liked_songs(sp) -> None:
    songs = [{"id": track["id"], "name": track["name"],
              "artists": [artist["name"] for artist in track["artists"]],
              "release_date": track["album"]["release_date"]}
             for track in library.liked_tracks(sp)]
    print(json.dumps(songs, ensure_ascii=False, indent=2))


def sync_playlists(sp, songs: list[playlists.Song], apply: bool) -> None:
    user_id = library.current_user_id(sp)
    existing = {}
    for playlist in library.own_playlists(sp, user_id):
        path = playlists.own_path(playlist.get("description"))
        if path and path not in existing:
            existing[path] = (playlist["id"], library.playlist_track_ids(sp, playlist["id"]))
    result = playlists.plan(playlists.tree(songs), existing)
    print(playlists.render(result))
    if not apply:
        print("\nDry-run: nothing was changed. Add --apply to write this to Spotify.")
        return

    print()
    for item in result:
        if not (item.playlist_id is None or item.add or item.remove):
            continue
        playlist_id = item.playlist_id or library.create_private_playlist(
            sp, playlists.name(item.path), playlists.description(item.path))
        library.remove_tracks(sp, playlist_id, item.remove)
        library.add_tracks(sp, playlist_id, item.add)
        action = "Created" if item.playlist_id is None else "Updated"
        print(f"{action} {playlists.name(item.path)}", flush=True)
    print("Done.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="spotify-playlist-organizer", description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "export-liked-songs",
        help="print your liked songs as JSON",
        description="Print all your liked songs, newest first, as a JSON list of "
                    "{id, name, artists, release_date}.")
    sync = commands.add_parser(
        "playlists",
        help="show or make the genre and mood playlists from song-categories.json",
        description="Show the playlist tree (Genres › main genre › subgenre and "
                    "Moods › main mood › subgenre) that song-categories.json gives, and what "
                    "would change in Spotify. Only reads unless --apply is given.")
    sync.add_argument("--categories", type=Path, default=Path("song-categories.json"),
                      help="the AI's genre and mood per song (default: song-categories.json)")
    sync.add_argument("--apply", action="store_true",
                      help="create and update the playlists in Spotify")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    resume = ""
    try:
        if args.command == "export-liked-songs":
            export_liked_songs(auth.client())
        else:
            songs = playlists.load(args.categories)
            if args.apply:
                resume = "Run the same command again to continue: finished playlists are kept."
            sync_playlists(auth.client(), songs, args.apply)
    except (auth.ConfigError, playlists.CategoriesFileError) as error:
        print(error, file=sys.stderr)
        return 2
    except SpotifyException as error:
        print(f"Spotify error {error.http_status}: {error.msg}", file=sys.stderr)
        if resume:
            print(resume, file=sys.stderr)
        return 1
    except SpotifyOauthError as error:
        print(f"Spotify sign-in failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"\nInterrupted. {resume}".rstrip(), file=sys.stderr)
        return 130
    return 0
