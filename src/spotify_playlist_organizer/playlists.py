"""The playlist tree built from `song-categories.json`, and how to sync it with the playlists in
Spotify.

Two trees, each song in exactly one playlist of each:
- Genres › main genre › subgenre
- Moods › main mood › subgenre

Spotify's API can't make folders, so the path is the playlist name. The script recognises its
own playlists by the path in their description, so renamed playlists are still found.
"""

import html
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

GENRES = "Genres"
MOODS = "Moods"
SEPARATOR = " › "
MARKER = "spotify-playlist-organizer: "
FIELDS = ("main_genre", "subgenre", "main_mood")
TRACK_ID = re.compile(r"[0-9A-Za-z]{22}")


class CategoriesFileError(Exception):
    """song-categories.json is missing, unreadable or has entries the tree can't be built from."""


@dataclass(frozen=True)
class Song:
    id: str
    main_genre: str
    subgenre: str
    main_mood: str


def load(path: Path) -> list[Song]:
    """The songs of a song-categories.json file; every problem is reported at once."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CategoriesFileError(
            f"{path} not found. Categorize your songs first (see README).") from None
    except (OSError, ValueError) as error:
        raise CategoriesFileError(f"{path} is not readable JSON: {error}") from None
    if not isinstance(data, list):
        raise CategoriesFileError(f"{path} must contain a JSON list of songs")

    songs, problems, seen = [], [], set()
    for number, entry in enumerate(data, 1):
        if not isinstance(entry, dict):
            problems.append(f"song {number} is not an object")
            continue
        song_id = entry.get("id")
        if not isinstance(song_id, str) or not TRACK_ID.fullmatch(song_id):
            problems.append(f"song {number} has no valid Spotify track id: {song_id!r}")
            continue
        missing = [name for name in FIELDS
                   if not isinstance(entry.get(name), str) or not entry[name].strip()]
        if missing:
            problems.append(f"song {number} ({song_id}) is missing {', '.join(missing)}")
            continue
        if song_id in seen:
            problems.append(f"song {number} ({song_id}) is listed twice")
            continue
        seen.add(song_id)
        songs.append(Song(song_id, *(entry[name].strip() for name in FIELDS)))
    if problems:
        raise CategoriesFileError(f"{path} has problems:\n"
                                  + "\n".join(f"- {problem}" for problem in problems))
    return songs


def tree(songs: list[Song]) -> dict[tuple[str, ...], list[str]]:
    """Every playlist path with its song IDs in file order. Genres come before Moods;
    within a tree, bigger branches and playlists come first."""
    playlists: dict[tuple[str, ...], list[str]] = {}
    for root, branch_of in ((GENRES, lambda s: s.main_genre), (MOODS, lambda s: s.main_mood)):
        branch_size = Counter(branch_of(song) for song in songs)
        leaves: dict[tuple[str, ...], list[str]] = {}
        for song in songs:
            leaves.setdefault((root, branch_of(song), song.subgenre), []).append(song.id)
        for path in sorted(leaves, key=lambda p: (-branch_size[p[1]], p[1],
                                                  -len(leaves[p]), p[2])):
            playlists[path] = leaves[path]
    return playlists


def name(path: tuple[str, ...]) -> str:
    return SEPARATOR.join(path)


def description(path: tuple[str, ...]) -> str:
    return MARKER + name(path)


def own_path(playlist_description: str | None) -> tuple[str, ...] | None:
    """The tree path of a playlist this script made, from its description; None for others.
    Spotify returns descriptions HTML-escaped (`&amp;`)."""
    text = html.unescape(playlist_description or "").strip()
    if not text.startswith(MARKER):
        return None
    path = tuple(part.strip() for part in text[len(MARKER):].split(SEPARATOR.strip()))
    return path if len(path) == 3 and path[0] in (GENRES, MOODS) and all(path) else None


@dataclass
class PlaylistPlan:
    path: tuple[str, ...]
    playlist_id: str | None  # None: the playlist will be created
    size: int  # songs after the sync
    add: list[str] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)

    @property
    def obsolete(self) -> bool:
        """A playlist of this script that the song categories no longer need; it gets emptied."""
        return self.playlist_id is not None and self.size == 0


def plan(wanted: dict[tuple[str, ...], list[str]],
         existing: dict[tuple[str, ...], tuple[str, list[str]]]) -> list[PlaylistPlan]:
    """What to create, add and remove so the script's playlists match `wanted`.
    `existing` maps a path to (playlist ID, current song IDs)."""
    plans = []
    for path, ids in wanted.items():
        playlist_id, current = existing.get(path, (None, []))
        target, have = set(ids), set(current)
        plans.append(PlaylistPlan(
            path, playlist_id, len(ids),
            add=[i for i in ids if i not in have],
            remove=list(dict.fromkeys(i for i in current if i not in target))))
    for path, (playlist_id, current) in existing.items():
        if path not in wanted and current:
            plans.append(PlaylistPlan(path, playlist_id, 0, remove=list(dict.fromkeys(current))))
    return plans


def _change(item: PlaylistPlan) -> str:
    if item.playlist_id is None:
        return "new"
    parts = [f"+{len(item.add)}" if item.add else "", f"−{len(item.remove)}" if item.remove else ""]
    return " ".join(p for p in parts if p) or "unchanged"


def render(plans: list[PlaylistPlan]) -> str:
    """The playlist tree with the song count and change of each playlist, then totals."""
    lines, root, branch = [], None, None
    current = [p for p in plans if not p.obsolete]
    width = max((len(p.path[2]) for p in current), default=0)
    for item in current:
        if item.path[0] != root:
            root, branch = item.path[0], None
            lines.append(root)
        if item.path[1] != branch:
            branch = item.path[1]
            total = sum(p.size for p in current if p.path[:2] == item.path[:2])
            lines.append(f"  {branch} ({total})")
        lines.append(f"    {item.path[2]:<{width}}  {item.size:>4}  {_change(item)}")

    obsolete = [p for p in plans if p.obsolete]
    if obsolete:
        lines.append("")
        lines.append("No longer in the song categories "
                     "(emptied; delete them in Spotify if you like):")
        lines.extend(f"  {name(p.path)}  −{len(p.remove)}" for p in obsolete)

    new = sum(p.playlist_id is None for p in current)
    unchanged = sum(_change(p) == "unchanged" for p in current)
    lines.append("")
    lines.append(f"Total: {len(current)} playlists ({new} new, "
                 f"{len(current) - new - unchanged} changed, {unchanged} unchanged), "
                 f"{sum(len(p.add) for p in plans)} songs to add, "
                 f"{sum(len(p.remove) for p in plans)} to remove")
    return "\n".join(lines)
