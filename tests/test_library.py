from fake_spotify import FakeSpotify

from spotify_playlist_organizer import library


def test_liked_tracks_returns_track_objects_across_pages_without_local_files():
    tracks = [{"id": "a", "name": "A"}, {"id": None, "name": "Local file"},
              {"id": "b", "name": "B"}, {"id": "c", "name": "C"}]
    sp = FakeSpotify(liked=tracks)

    assert library.liked_tracks(sp) == [tracks[0], tracks[2], tracks[3]]
