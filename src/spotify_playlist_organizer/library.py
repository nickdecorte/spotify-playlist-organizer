"""The only module that talks to Spotify: a thin layer over a spotipy client."""

PAGE_SIZE = 50
ITEM_BATCH = 100  # adding or removing playlist items accepts at most 100 per request


def _all_items(sp, page: dict | None) -> list[dict]:
    items = []
    while page:
        items.extend(page["items"])
        page = sp.next(page)
    return items


def liked_tracks(sp) -> list[dict]:
    """All your liked songs as Spotify track objects, newest first; local files are left out."""
    tracks = (entry.get("track") for entry in
              _all_items(sp, sp.current_user_saved_tracks(limit=PAGE_SIZE)))
    return [track for track in tracks if track and track.get("id")]


def current_user_id(sp) -> str:
    return sp.current_user()["id"]


def own_playlists(sp, user_id: str) -> list[dict]:
    """The playlists you own; followed ones are left out."""
    playlists = _all_items(sp, sp.current_user_playlists(limit=PAGE_SIZE))
    return [p for p in playlists if p and p["owner"]["id"] == user_id]


def playlist_track_ids(sp, playlist_id: str) -> list[str]:
    """The IDs of the songs in a playlist you own, in playlist order; local files are left out."""
    entries = _all_items(sp, sp.playlist_items(playlist_id, limit=PAGE_SIZE,
                                               additional_types=("track",)))
    items = (entry.get("item") for entry in entries)
    return [item["id"] for item in items if item and item.get("id")]


def create_private_playlist(sp, name: str, description: str) -> str:
    """Create an empty private playlist and return its ID."""
    return sp.current_user_playlist_create(name, public=False, description=description)["id"]


def add_tracks(sp, playlist_id: str, track_ids: list[str]) -> None:
    """Append the songs in the given order, at most 100 per request."""
    for start in range(0, len(track_ids), ITEM_BATCH):
        sp.playlist_add_items(playlist_id, track_ids[start:start + ITEM_BATCH])


def remove_tracks(sp, playlist_id: str, track_ids: list[str]) -> None:
    """Remove every occurrence of the songs, at most 100 per request."""
    for start in range(0, len(track_ids), ITEM_BATCH):
        sp.playlist_remove_all_occurrences_of_items(playlist_id,
                                                    track_ids[start:start + ITEM_BATCH])
