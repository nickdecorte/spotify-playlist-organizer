# spotify-playlist-organizer

Sort your liked Spotify songs into genre and mood playlists.

1. **Fetch** all your liked songs as JSON (`spotify-playlist-organizer export-liked-songs`).
2. **Sort** them with an AI chat of your choice, using the prompt in [`prompt.md`](prompt.md): every song gets a main genre, a subgenre and a main mood.
3. **Build** the playlists in Spotify from that sorting (`spotify-playlist-organizer playlists`), with a dry-run first. Rerun it after a new sorting to keep the playlists in sync.

Everything runs locally; the script only talks to Spotify. The AI step is done by hand in a chat, so you choose the AI and see what it gets.

## Requirements

- macOS or Linux with [uv](https://docs.astral.sh/uv/getting-started/installation/) (`brew install uv`). uv installs the right Python (3.12+) and the dependencies by itself.
- [jq](https://jqlang.org) for splitting and combining the AI batches (`brew install jq`).
- A Spotify account with **Premium**: Spotify only lets development-mode apps run while the app owner has Premium.

## Installation

### 1. Get the code

```sh
git clone <repository-url> spotify-playlist-organizer
cd spotify-playlist-organizer
uv sync
```

`uv sync` creates `.venv/` with the dependencies. The `uv run …` commands below also do this on first use, so this step is optional.

### 2. Create your own Spotify app

The script signs in through an app you own in Spotify's developer dashboard; no client secret is needed.

1. Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), sign in and click **Create app**.
2. Fill in any name and description.
3. Set **Redirect URI** to exactly `http://127.0.0.1:8888/callback` and click **Add**. Spotify doesn't accept `localhost`.
4. Under **Which API/SDKs are you planning to use?**, tick **Web API**, accept the terms and save.
5. Open the app's **Settings** and copy the **Client ID**.

The app runs in development mode, which is enough: you can use it with your own account. To let someone else use your app, add their Spotify e-mail under **User Management** (at most 5 people).

### 3. Configure

```sh
cp .env.example .env
```

Open `.env`, paste your Client ID after `SPOTIPY_CLIENT_ID=` and leave `SPOTIPY_REDIRECT_URI` as it is. `.env` is git-ignored.

### 4. Check that it works

```sh
uv run spotify-playlist-organizer --help
```

## Usage

Run every command from the project folder. `--env-file .env` passes your settings to the script.

### Step 1: fetch your liked songs

```sh
uv run --env-file .env spotify-playlist-organizer export-liked-songs > liked-songs.json
```

The first run opens your browser to sign in to Spotify (see [Spotify sign-in](#spotify-sign-in)). The command prints every liked song, newest first, as a JSON list:

```json
[
  {
    "id": "2JiDi0qAXsPwhPqA2qaKGt",
    "name": "Bohemian Rhapsody",
    "artists": ["Queen"],
    "release_date": "1975-11-21"
  }
]
```

- A song with several artists lists them all.
- `release_date` is the album's release date. For some old releases Spotify only knows the year (`"1975"`) or month (`"1975-11"`).
- Local files are left out.

### Step 2: sort the songs with an AI

[`prompt.md`](prompt.md) tells the AI to give every song:

| Field | Values |
|---|---|
| `main_genre` and `subgenre` | 14 subgenres under 7 main genres: Rock & Metal, Electronic, Pop, Hip-Hop & R&B, Folk & Country, Soundtrack & Orchestral, Other |
| `main_mood` | Hype, Dark, Feel Good or Mellow |
| `moods` | 1–3 of 16 moods, the first one belonging to the main mood |

The fixed lists keep the answers consistent across batches. To change the genres or moods, edit the tables in `prompt.md`; the script builds its playlists from whatever values `song-categories.json` contains.

A full library is too long for one AI answer, so send it in batches of about 200 songs:

1. Copy the first batch: `jq '.[0:200]' liked-songs.json | pbcopy` (on Linux: `| xclip -selection clipboard`). For the next batches use `.[200:400]`, `.[400:600]` and so on, until the batch is empty (`jq length liked-songs.json` gives the total).
2. In a new AI chat, paste everything in `prompt.md` below the `---` line, then paste the batch.
3. Save the answer as `categories-batch-1.json`, `categories-batch-2.json`, … in the project folder. If the AI wrapped the answer in ```` ``` ```` fences, remove them.
4. Combine the batches and check that every song came back:

   ```sh
   jq -s 'add' categories-batch-*.json > song-categories.json
   jq length liked-songs.json song-categories.json    # both numbers must be equal
   ```

The genres and moods are the AI's judgement, not data from Spotify: well-known songs are usually right, obscure ones can be guesses. You can correct `song-categories.json` by hand before step 3.

The script needs `id`, `main_genre`, `subgenre` and `main_mood` for every song; other fields such as `moods` are ignored.

### Step 3: build the playlists

`playlists` turns `song-categories.json` into two playlist trees. Every song lands in exactly one playlist of each:

- `Genres › <main genre> › <subgenre>`, e.g. `Genres › Rock & Metal › Metal`
- `Moods › <main mood> › <subgenre>`, e.g. `Moods › Hype › Metal`

First do a dry-run. It shows the tree with the number of songs per playlist and what would change, and writes nothing:

```sh
uv run --env-file .env spotify-playlist-organizer playlists
```

```
Genres
  Rock & Metal (240)
    Metal                     128  new
    Rock                      112  +3 −1
…
Total: 24 playlists (22 new, 1 changed, 1 unchanged), 480 songs to add, 1 to remove

Dry-run: nothing was changed. Add --apply to write this to Spotify.
```

`new` means the playlist will be created, `+3 −1` that 3 songs will be added and 1 removed.

When the tree looks right, create the playlists:

```sh
uv run --env-file .env spotify-playlist-organizer playlists --apply
```

How it behaves:

- **Private:** all playlists are created private.
- **Only its own playlists:** the script recognises its playlists by their description, `spotify-playlist-organizer: <path>`, and never touches any other playlist. You can rename its playlists, but don't change the description: the script would no longer recognise the playlist and would create a new one.
- **Reruns sync:** after a new `song-categories.json`, run it again. It adds new songs, removes songs that moved to another playlist, and empties playlists the new sorting no longer needs (listed under "No longer in the song categories"). It never deletes playlists; delete emptied ones yourself if you like.
- **Interrupted runs:** if `--apply` stops halfway (network error, Spotify rate limit, Ctrl-C), run it again. Finished playlists are kept and only the rest changes.
- **Other input file:** `--categories PATH` reads another file than `song-categories.json`. A broken file is reported with every problem at once, before Spotify is contacted.

### Folders

Spotify's Web API can't create folders or put playlists in them ([Spotify docs](https://developer.spotify.com/documentation/web-api/concepts/playlists#folders)). That's why the tree path is part of each playlist's name: Spotify sorts playlists by name, so each tree stays together.

To get real folders, create them once in the Spotify desktop app (for example *Genres* with a folder per main genre inside, and the same for *Moods*) and drag the playlists in. Reruns keep them there: the script only changes the songs of existing playlists, it never moves or recreates them. Only playlists that are new in a later run (shown as `new` in the dry-run) appear outside the folders.

### Updating later

When you've liked new songs, run the three steps again. To avoid sorting everything again, sort only the new songs and add them to `song-categories.json`:

```sh
uv run --env-file .env spotify-playlist-organizer export-liked-songs > liked-songs.json
jq --slurpfile done song-categories.json '($done[0] | map({key: .id, value: true}) | from_entries) as $have | map(select($have[.id] | not))' liked-songs.json > uncategorized-songs.json
```

Sort `uncategorized-songs.json` with the AI as in step 2, save the answer as `categories-batch-new.json`, then combine and apply:

```sh
jq -s 'add' song-categories.json categories-batch-new.json > song-categories-next.json && mv song-categories-next.json song-categories.json
uv run --env-file .env spotify-playlist-organizer playlists            # check
uv run --env-file .env spotify-playlist-organizer playlists --apply
```

Songs you unliked stay in `song-categories.json` and their playlists until you remove them from `song-categories.json`.

## Commands

| Command | What it does |
|---|---|
| `spotify-playlist-organizer export-liked-songs` | Print all liked songs as JSON |
| `spotify-playlist-organizer playlists` | Dry-run: show the playlist tree from `song-categories.json` and what would change |
| `spotify-playlist-organizer playlists --apply` | Create and update the playlists in Spotify |
| `spotify-playlist-organizer playlists --categories PATH` | Use another file than `song-categories.json` |
| `spotify-playlist-organizer <command> --help` | Help for a command |

Exit codes: `0` success, `1` Spotify or sign-in error, `2` missing setting or broken `song-categories.json`, `130` interrupted.

## Spotify sign-in

The first run opens your browser to sign in to Spotify and approve the app. The sign-in uses PKCE, so no client secret is involved. The app asks to:

- read your liked songs (`user-library-read`),
- read your private playlists, to find its own (`playlist-read-private`),
- create and change private playlists (`playlist-modify-private`).

The token is stored in `~/.cache/spotify-playlist-organizer/token.json`, readable only by you, and refreshed automatically. To sign out, delete that file. If a new version of the script needs more permissions, the browser opens once more to approve them.

## Troubleshooting

| Problem | Fix |
|---|---|
| `SPOTIPY_CLIENT_ID is not set` | Create `.env` (see [Configure](#3-configure)) and run with `uv run --env-file .env …` from the project folder. |
| Browser shows `INVALID_CLIENT: Invalid redirect URI` | The redirect URI in the dashboard must be exactly `http://127.0.0.1:8888/callback`, and the same as in `.env`. |
| `Spotify error 403` | The app owner needs Premium, and anyone else must be added under **User Management** in the dashboard. |
| `song-categories.json has problems` | Every listed song is missing a field or has a wrong ID. Fix those entries or sort those songs again. |
| `jq: error … parse error` | One of the batch files isn't plain JSON: remove ```` ``` ```` fences or text the AI added around the list. |

## Development

```sh
uv run pytest        # tests
uv run ruff check    # lint
```

Code layout:

| File | Role |
|---|---|
| `src/spotify_playlist_organizer/cli.py` | The `spotify-playlist-organizer` command and its subcommands |
| `src/spotify_playlist_organizer/auth.py` | Spotify sign-in (PKCE) and settings |
| `src/spotify_playlist_organizer/library.py` | The only module that calls Spotify |
| `src/spotify_playlist_organizer/playlists.py` | Reading `song-categories.json`, building the tree, planning the sync and the dry-run output |
| `tests/` | Tests, with an in-memory Spotify stand-in (`fake_spotify.py`) |
