"""A stand-in for spotipy.Spotify that keeps liked songs and playlists in memory."""

import html


def pages(items: list, size: int) -> dict | None:
    """Chain `items` into spotipy-style pages of `size`, linked through `next`."""
    chunks = [items[i:i + size] for i in range(0, len(items), size)] or [[]]
    page = None
    for chunk in reversed(chunks):
        page = {"items": chunk, "next": page}
    return page


class FakeSpotify:
    def __init__(self, liked=(), playlists=(), user_id="me", page_size=2):
        self.liked_pages = pages([{"track": t} for t in liked], page_size)
        self.playlists = [dict(p, songs=list(p.get("songs", []))) for p in playlists]
        self.user_id = user_id
        self.page_size = page_size
        self.writes = []  # ("add" | "remove", playlist ID, number of songs) per request

    def _playlist(self, playlist_id):
        return next(p for p in self.playlists if p["id"] == playlist_id)

    def next(self, page):
        return page["next"]

    def current_user(self):
        return {"id": self.user_id}

    def current_user_saved_tracks(self, limit=20, offset=0, market=None):
        return self.liked_pages

    def current_user_playlists(self, limit=50, offset=0):
        listed = [{key: value for key, value in p.items() if key != "songs"}
                  for p in self.playlists]
        return pages(listed, self.page_size)

    def playlist_items(self, playlist_id, fields=None, limit=50, offset=0, market=None,
                       additional_types=("track", "episode")):
        return pages([{"item": {"id": song}} for song in self._playlist(playlist_id)["songs"]],
                     self.page_size)

    def current_user_playlist_create(self, name, public=True, collaborative=False,
                                     description=""):
        playlist = {"id": f"p{len(self.playlists)}", "name": name, "public": public,
                    "description": html.escape(description, quote=False),  # as Spotify does
                    "owner": {"id": self.user_id}, "songs": []}
        self.playlists.append(playlist)
        return {key: value for key, value in playlist.items() if key != "songs"}

    def playlist_add_items(self, playlist_id, items, position=None):
        self.writes.append(("add", playlist_id, len(items)))
        self._playlist(playlist_id)["songs"].extend(items)

    def playlist_remove_all_occurrences_of_items(self, playlist_id, items, snapshot_id=None):
        self.writes.append(("remove", playlist_id, len(items)))
        playlist = self._playlist(playlist_id)
        playlist["songs"] = [song for song in playlist["songs"] if song not in items]
