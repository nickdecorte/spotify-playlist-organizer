import json

import pytest
from fake_spotify import FakeSpotify

from spotify_playlist_organizer import cli, playlists


def tid(n):
    return f"{n:022d}"


def song(n, main_genre, subgenre, main_mood):
    return playlists.Song(tid(n), main_genre, subgenre, main_mood)


SONGS = [
    song(1, "Rock & Metal", "Metal", "Hype"),
    song(2, "Pop", "Pop", "Mellow"),
    song(3, "Rock & Metal", "Punk", "Hype"),
    song(4, "Rock & Metal", "Metal", "Dark"),
]


def contents(sp):
    return {p["name"]: p["songs"] for p in sp.playlists}


def test_load_reports_every_problem_at_once(tmp_path):
    path = tmp_path / "song-categories.json"
    good = {"id": tid(1), "main_genre": "Pop", "subgenre": "Pop", "main_mood": "Hype"}
    path.write_text(json.dumps([
        good,
        {**good, "id": "not-an-id"},
        {**good, "id": tid(2), "main_mood": ""},
        dict(good),
        "text",
    ]))

    with pytest.raises(playlists.CategoriesFileError) as error:
        playlists.load(path)

    message = str(error.value)
    assert "song 2 has no valid Spotify track id" in message
    assert f"song 3 ({tid(2)}) is missing main_mood" in message
    assert f"song 4 ({tid(1)}) is listed twice" in message
    assert "song 5 is not an object" in message


def test_tree_puts_each_song_in_one_genre_and_one_mood_playlist_biggest_first():
    tree = playlists.tree(SONGS)

    assert list(tree.items()) == [
        (("Genres", "Rock & Metal", "Metal"), [tid(1), tid(4)]),
        (("Genres", "Rock & Metal", "Punk"), [tid(3)]),
        (("Genres", "Pop", "Pop"), [tid(2)]),
        (("Moods", "Hype", "Metal"), [tid(1)]),
        (("Moods", "Hype", "Punk"), [tid(3)]),
        (("Moods", "Dark", "Metal"), [tid(4)]),
        (("Moods", "Mellow", "Pop"), [tid(2)]),
    ]


def test_dry_run_changes_nothing(capsys):
    sp = FakeSpotify()

    cli.sync_playlists(sp, SONGS, apply=False)

    out = capsys.readouterr().out
    assert sp.playlists == [] and sp.writes == []
    assert "  Rock & Metal (3)\n    Metal  " in out
    assert "Total: 7 playlists (7 new, 0 changed, 0 unchanged), 8 songs to add, 0 to remove" in out


def test_resync_moves_resorted_songs_and_empties_playlists_no_longer_needed(capsys):
    theirs = {"id": "x", "name": "Mine", "description": "Genres › Pop › Pop",
              "owner": {"id": "me"}, "songs": [tid(9)]}
    sp = FakeSpotify(playlists=[theirs])
    cli.sync_playlists(sp, SONGS, apply=True)
    assert all(p["public"] is False for p in sp.playlists[1:])
    assert contents(sp)["Genres › Rock & Metal › Metal"] == [tid(1), tid(4)]

    # song 3 moves from Punk to Metal, so nothing is Punk anymore; song 5 is new
    resorted = [*SONGS[:2], song(3, "Rock & Metal", "Metal", "Hype"), SONGS[3],
                song(5, "Pop", "Pop", "Hype")]
    capsys.readouterr()
    cli.sync_playlists(sp, resorted, apply=True)

    after = contents(sp)
    assert after["Genres › Rock & Metal › Metal"] == [tid(1), tid(4), tid(3)]
    assert after["Genres › Rock & Metal › Punk"] == []
    assert after["Moods › Hype › Pop"] == [tid(5)]
    assert after["Mine"] == [tid(9)]
    assert "No longer in the song categories" in capsys.readouterr().out

    cli.sync_playlists(sp, resorted, apply=False)
    assert "(0 new, 0 changed, 6 unchanged), 0 songs to add, 0 to remove" in capsys.readouterr().out


def test_songs_are_added_at_most_100_per_request():
    many = [song(n, "Pop", "Pop", "Hype") for n in range(250)]
    sp = FakeSpotify()

    cli.sync_playlists(sp, many, apply=True)

    assert [count for _, playlist, count in sp.writes if playlist == "p0"] == [100, 100, 50]
