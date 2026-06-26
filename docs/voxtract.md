# 🌊 voxtract — Voice Extract Tool

**Extract and isolate speech from any media source — YouTube, Jellyfin, Plex, Spotify, podcasts, direct URLs, or local files.**

`voxtract` · Python 3 · `ffmpeg`

```bash
voxtract fetch https://youtube.com/watch?v=…     # Download + cache audio
voxtract clip URL --start 1:30 --end 2:00        # Clip by timestamp
voxtract clip URL --start 1:30 --isolate         # Clip + Demucs voice isolation
voxtract list jellyfin://home                      # Browse a media server
```

---

## Quick start

```bash
# Clip a YouTube video (downloads on first run, caches thereafter)
voxtract clip https://youtube.com/watch?v=dQw4w9WgXcQ --start 0:30 --end 1:00

# Isolate speech from a local file
voxtract clip /path/to/podcast.mp3 --isolate --format mp3

# Connect a media server, then browse and fetch
voxtract sources add jellyfin --name home --url http://jellyfin:8096 --key YOUR_KEY
voxtract list jellyfin://home
```

---

## Architecture

```
Source Adapters → fetch audio to cache → clip by timestamp (ffmpeg) → isolate speech (Demucs NN)
```

Plugin-based source adapters. Each implements `can_handle(uri)`, `fetch(uri, dest)`, and `list_items(uri)`.

Current adapters: YouTubeAdapter, SpotifyAdapter, JellyfinAdapter, PlexAdapter, PodcastAdapter, DirAdapter, HTTPAdapter, LocalFileAdapter.

---

## Commands

### `voxtract fetch <uri>`
Download and cache audio from any source.
- `--force` / `-f` — Re-download even if cached

### `voxtract clip <uri>`
Extract an audio clip by timestamp.
- `--start` / `-s` — Start time (e.g. `1:30`, `90`, `1:00:00`)
- `--end` / `-e` — End time
- `--duration` / `-d` — Duration in seconds
- `--isolate` / `-i` — Remove music & background, extract voice only
- `--format` / `-f` — Output format: `mp3`, `wav`, `flac`, `ogg`, `m4a`
- `--output-dir` / `-o` — Output directory

### `voxtract list <uri>`
Search or browse items in a source.
- `--query` / `-q` — Search term
- `--type` / `-t` — Filter by type
- `--limit` / `-n` — Max results (default: 20)

### `voxtract isolate <uri>`
Isolate speech from a cached source.
- `--force` — Re-process even if vocals exist

### `voxtract cache <action>`
Manage cached media.
- `list` — Show all cached sources
- `clean` — Remove everything
- `remove <uri>` — Remove one source
- `info <uri>` — Show metadata

### `voxtract sources <action>`
Manage media server connections.
- `list` — Show configured servers
- `add <type>` — Add a server (jellyfin, plex, spotify)
- `remove <type>` — Remove a server

---

## Source URI Reference

- **YouTube** — `youtube://VIDEO_ID` or any `https://youtube.com/...` URL
- **Spotify** — `spotify://track/ID`, `spotify://album/ID`, `spotify://show/ID`, `spotify://episode/ID`, `spotify://search`
- **Jellyfin** — `jellyfin://SERVER/Items/ID`
- **Plex** — `plex://SERVER/metadata/KEY`
- **Podcast** — `podcast://FEED_URL` or `podcast://FEED_URL#ep-N`
- **HTTP** — Any `http(s)://` URL
- **Directory** — `dir:///absolute/path`
- **Local file** — `/absolute/path/file.mp3`

---

## Connecting to Media Servers

```bash
# Spotify (Client ID + Secret from https://developer.spotify.com/dashboard)
voxtract sources add spotify --id YOUR_CLIENT_ID --secret YOUR_CLIENT_SECRET

# Jellyfin (API key from Dashboard → API Keys, or user/password)
voxtract sources add jellyfin --name home --url http://jellyfin:8096 --key YOUR_API_KEY
voxtract sources add jellyfin --name home --url http://jellyfin:8096 --user admin --pass password

# Plex (token from https://plex.tv/claim or server settings)
voxtract sources add plex --name home --url http://plex:32400 --token YOUR_PLEX_TOKEN
```

---

## Speech Isolation

Uses Meta's **Demucs** Hybrid Transformer model (`htdemucs`) for neural audio separation.

Environment variable `VOXTRACT_DEMUCS_MODEL` overrides the model:
- `htdemucs` — Default, fast, good quality
- `htdemucs_ft` — Fine-tuned, best quality, slower
- `hdemucs_mmi` — Alternative model

Model downloads automatically on first `--isolate` use (~300MB), then cached.

---

## Caching

- Source audio cached by content hash in `~/.voxtract/cache/<id>/`
- Metadata in `meta.json`, isolated vocals in `vocals.wav`
- Multiple clips from the same source reuse both audio and isolated vocals
- Override cache directory with `VOXTRACT_CACHE` env var

---

## Related tools

Built on **[scriptkit](scriptkit.md)** — the shared CLI library (color, messages, progress, tables, config, subprocess). Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

Part of the [scripts](../README.md) toolkit — [keyferry](keyferry.md) · [medcat](medcat.md) · [netsy](netsy.md) · [pluck](pluck.md) · [aikit](aikit.md)

---

## License

MIT — see [LICENSE](../LICENSE).
