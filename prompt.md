# Prompt: sort liked songs into genres and moods

Copy everything below the line into an AI chat, then paste a batch of songs from `liked-songs.json` after it (see README: about 200 songs per message).

---

You sort songs into playlists. Below this prompt is a JSON list of songs, each with `id`, `name`, `artists` and `release_date`.

For every song, choose:

1. **main_genre** and **subgenre**: exactly one subgenre from this list, together with the main genre it belongs to.

   | main_genre | subgenre | covers |
   |---|---|---|
   | Rock & Metal | Metal | heavy, power, symphonic, folk, nu, alternative, death, black metal, metalcore |
   | Rock & Metal | Rock | classic, hard, alternative, indie, soft rock, post-grunge |
   | Rock & Metal | Punk | punk rock, pop punk, post-hardcore, emo, ska punk |
   | Electronic | Electronic | house, EDM, trance, techno, drum and bass, dubstep, synthwave, eurodance |
   | Electronic | Hard Dance | hardstyle, hardcore, frenchcore, jumpstyle, hard trance |
   | Electronic | Ambient & Chill | ambient, lo-fi, downtempo, nature sounds, meditation |
   | Hip-Hop & R&B | Hip-Hop | rap, trap, pop rap, gangsta rap |
   | Hip-Hop & R&B | R&B & Soul | R&B, soul, funk, neo-soul, gospel |
   | Pop | Pop | pop, dance pop, synth-pop, indie pop, singer-songwriter pop |
   | Pop | Schlager & Party | schlager, carnival, après-ski, Dutch and German party songs |
   | Folk & Country | Folk | folk, medieval, pagan, celtic, Irish, sea shanties |
   | Folk & Country | Country | country, Americana, bluegrass |
   | Soundtrack & Orchestral | Soundtrack & Orchestral | film and game scores, trailer music, classical, orchestral, choir |
   | Other | Other | only when nothing above fits (comedy, spoken word, …) |

2. **main_mood** and **moods**: exactly one main mood, and 1 to 3 moods that fit the song itself, best fit first. The first mood must belong to the main mood; the others may come from any main mood.

   | main_mood | moods |
   |---|---|
   | Hype | energetic, aggressive, party, euphoric |
   | Dark | dark, epic |
   | Feel Good | happy, uplifting, playful, empowering |
   | Mellow | melancholic, romantic, nostalgic, chill, calm, dreamy |

Rules:
- Judge the song itself, not only the artist's usual style. A remix, cover or acoustic version can belong to another subgenre or mood than the original.
- Use the names exactly as written above (same spelling and capitals).
- Return every song exactly once, in the same order, and nothing else: no explanation, no Markdown fences.
- If you don't know a song, decide from the title, artists and release date. Still give an answer.

Answer with a JSON list in this exact shape:

[
  {"id": "2JiDi0qAXsPwhPqA2qaKGt", "main_genre": "Rock & Metal", "subgenre": "Rock", "main_mood": "Dark", "moods": ["epic", "melancholic"]}
]

Songs:
