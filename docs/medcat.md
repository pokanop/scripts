# 📚 medcat — Media Stack Ingest Tool · v2.4.0

**Ingest media files into your media stack with metadata enrichment.**

`medcat` · Python 3 · `rich` · `ebooklib` · `pymupdf` · `musicbrainzngs` · `requests` · optional: `yt-dlp`, `ia`

```bash
medcat setup                              # First-time interactive wizard
medcat identify ~/Downloads/*.epub        # Preview metadata, no moves
medcat ingest book.epub                   # Ingest (auto-detect type)
medcat grab https://youtube.com/watch?v=… # URL → download + route
```

---

## Quick start

```bash
# First-time setup (interactive wizard)
medcat setup

# Identify files — see metadata without moving anything
medcat identify ~/Downloads/*.epub

# Ingest books (auto-detected from file type)
medcat ingest book.epub

# Dry run first
medcat ingest --dest comics ./new-comics/ --dry-run

# Auto-confirm + trigger scan after
medcat ingest --dest books ~/Downloads/ --scan --yes
```

---

## Direct URL Grab (New in v2.1)

`medcat grab` accepts any URL and auto-routes to the correct handler:

```bash
# YouTube — extracts video or audio
medcat grab https://youtube.com/watch?v=dQw4w9WgXcQ
medcat grab https://youtube.com/watch?v=... --audio --dest music

# Magnet links — sends to torrent client
medcat grab magnet:?xt=urn:btih:... --type movies

# Internet Archive — downloads with metadata
medcat grab https://archive.org/details/example --type books

# Direct file URLs — detects content type
medcat grab https://example.com/book.epub --dest books --scan

# Torrent files — fetches and sends to torrent client
medcat grab https://example.com/file.torrent

# Just preview metadata without downloading
medcat grab URL --info

# Dry run — show what would happen
medcat grab URL --dry-run
```

The `search` command also auto-detects URLs — paste a YouTube link as the search query and it transparently routes to grab mode:

```bash
medcat search https://youtube.com/watch?v=... --type music
```

Downloads show live progress when the source supports it. Direct HTTP and
Internet Archive transfers display bytes, speed, and ETA through `scriptkit`;
`wget`, `yt-dlp`, and `ia` retain their native progress displays.

### URL Routing Table

| URL Pattern | Detected As | Handler |
|---|---|---|
| `youtube.com/watch?v=` / `youtu.be/` / `music.youtube.com/` | `youtube` | yt-dlp download (video or audio) |
| `magnet:?xt=urn:btih:` | `magnet` | Torrent client (Deluge/qBittorrent) |
| `archive.org/details/` / `archive.org/download/` | `archive` | Internet Archive download |
| `*.torrent` | `torrent` | Fetched + sent to torrent client |
| Everything else (`http://` / `https://`) | `direct` | Content-type probing + wget/requests download |

### Media Type Auto-Detection (Direct URLs)

For direct URLs, medcat probes the `Content-Type` header and URL extension:

| Content-Type / Extension | Media Type |
|---|---|
| `application/epub+zip`, `.epub` | `books` |
| `application/pdf`, `.pdf` | `books` |
| `audio/mpeg`, `.mp3`, `.flac` | `music` |
| `audio/m4b`, `audio/aac`, `.m4b` | `audiobooks` |
| `video/mp4`, `video/x-matroska`, `.mkv`, `.mp4` | `movies` |
| `.cbz`, `.cbr` | `comics` |

Override auto-detection with `--dest <type>` or `--type <type>`.

### Grab Command Options

| Option | Description |
|---|---|
| `--dest`, `-d` TYPE | Destination/media type (books, movies, music, etc.) |
| `--audio` | Force audio extraction (YouTube → MP3) |
| `--scan`, `-s` | Trigger library scan after download |
| `--no-ingest` | Download only, don't auto-ingest |
| `--dry-run`, `-n` | Show what would happen |
| `--info` | Only show URL metadata, don't download |

---

## Supported Media Types

| Type | Extensions | Typical Scan Service |
|------|-----------|---------------------|
| `books` | .epub, .pdf | Kavita |
| `comics` | .cbz, .cbr | Kavita |
| `audiobooks` | .m4b, .aa, .aax, .mp3* | Audiobookshelf |
| `movies` | .mkv, .mp4, .avi | Radarr |
| `shows` | .mkv, .mp4 | Sonarr |
| `music` | .flac, .mp3, .opus | Lidarr |
| `documentaries` | .mkv, .mp4 | Radarr |

\* MP3 audiobooks are detected via ffprobe heuristics (genre, ISBN tag, or long single-file duration). Use `--dest audiobooks` to force classification.

TV episodes are auto-detected from filenames containing `S01E01`-style patterns. Documentaries require `--dest documentaries`.

---

## Metadata Sources

| File Type | Internal Metadata | API Enrichment |
|-----------|-------------------|----------------|
| EPUB | OPF (title, author, ISBN, publisher, date) | Google Books, Open Library |
| PDF | XMP + document info | Google Books, Open Library |
| CBZ/CBR | ComicInfo.xml (title, series, issue, writer) | — |
| M4B/MP3 | ffprobe tags (title, artist, album, ISBN) | Google Books |
| MKV/MP4 | Filename heuristics (show/season/episode) | — |
| FLAC/MP3 | ffprobe tags (title, artist, album, track) | MusicBrainz |

CBR archives require `7z`, `unar`, or `bsdtar` on PATH for ComicInfo.xml extraction.

---

## Configuration

### Interactive Setup

```bash
# Full interactive setup (first launch or reconfigure)
medcat setup

# Reconfigure a specific section
medcat setup --section transport
medcat setup --section destinations
medcat setup --section services
```

### CLI Config Management

```bash
# View full config (API keys masked)
medcat config --show

# Get a specific value
medcat config get services.kavita.url
medcat config get destinations.books.path

# Set a value
medcat config set services.kavita.url http://192.168.1.100:5080
medcat config set services.radarr.api_key YOUR_KEY_HERE
medcat config set transport.host 192.168.1.10
medcat config set destinations.books.path /media/books/books

# Remove a config key
medcat config unset services.lidarr

# List sections
medcat config list
medcat config list destinations
medcat config list services

# Validate config completeness
medcat config --check

# Test service connections
medcat config test
medcat config test kavita radarr

# Reset to clean defaults
medcat config --reset
```

### Environment Variable Overrides

Any config value can be overridden with a `MEDCAT_` environment variable using `__` as dot separator:

```bash
export MEDCAT_SERVICES__KAVITA__API_KEY=your_key
export MEDCAT_SERVICES__KAVITA__URL=http://192.168.1.100:5080
export MEDCAT_TRANSPORT__HOST=192.168.1.10
```

Environment variables take the highest priority, overriding file config.

### Config File Location

Config is stored at `~/.medcat/config.json`. Override with `MEDCAT_CONFIG` env var:

```bash
export MEDCAT_CONFIG=/path/to/custom/.medcat
```

---

## Diagnostics

```bash
medcat doctor
```

Checks the environment in one sectioned report: media tools (`ffmpeg`, `yt-dlp`,
`ia`, `wget`), Python packages (`ebooklib`, `pymupdf`, `musicbrainzngs`,
`yt-dlp`), and whether a config file exists. Exits non-zero if a required
dependency is missing. For service reachability use `medcat config --check` /
`medcat config test`.

---

## Architecture

Plugin-based handler pattern. Each media type has a handler class implementing:
- `extract_metadata()` — reads internal file metadata
- `enrich_metadata()` — queries external APIs
- `build_destination()` — constructs output path from template
- `writeback_metadata()` — writes enriched metadata back to file

Adding a new media type: create a handler subclass, register in the `HANDLERS` dict.

---

## Search & Download

medcat can search for media across multiple sources and trigger downloads directly from the CLI.

### Search Sources

| Source | Key | Config Required | Description |
|--------|-----|----------------|-------------|
| **Prowlarr** | `prowlarr` | URL + API key | Searches usenet/torrent indexers; pushes to download client |
| **Internet Archive** | `archive` | None | Free books, audio, movies from archive.org |
| **YouTube** | `youtube` | `yt-dlp` on PATH | Video/audio search and download |

### Basic Search

```bash
# Simple search (auto-selects sources by media type)
medcat search "Dune"

# Filter by media type
medcat search "Foundation" --type books
medcat search "Interstellar" --type movies

# Pick specific sources
medcat search "Dune" --source prowlarr,archive
medcat search "Miles Davis" --source all --limit 10

# List results only (no download prompt)
medcat search "1984 Orwell" --list-only
```

### Interactive Download

Without `--list-only`, medcat shows results and prompts for download:

```
Download (number, range, 'a'll, 'q'uit): 1
Download (number, range, 'a'll, 'q'uit): 3-5
Download (number, range, 'a'll, 'q'uit): a
Download (number, range, 'a'll, 'q'uit): q
```

Download behavior depends on the source:
- **Prowlarr**: Pushes release to configured download client (Deluge/qBittorrent via Prowlarr)
- **Internet Archive**: Downloads file directly (uses `ia` CLI if available, else HTTP)
- **YouTube**: Downloads via `yt-dlp` (audio extraction for music/audiobooks)

### Torrent Client Setup

To handle magnet links from Prowlarr or direct torrent downloads, configure a torrent client:

```bash
# Configure via setup wizard
medcat setup --section services

# Or manually
medcat config set services.deluge.url http://192.168.1.100:8112
medcat config set services.deluge.password your_password

medcat config set services.qbittorrent.url http://192.168.1.100:8080
medcat config set services.qbittorrent.username admin
medcat config set services.qbittorrent.password your_password
```

### Prowlarr Category Mapping

When searching with `--type`, medcat automatically maps media types to Prowlarr/Newznab category IDs:

| Media Type | Categories |
|------------|-----------|
| `books` | 7000 (Books), 7020 (eBooks) |
| `audiobooks` | 3030 (Audiobooks) |
| `comics` / `manga` | 7030 (Comics) |
| `movies` | 2000–2080 (Movies) |
| `shows` | 5000–5080 (TV) |
| `music` | 3000–3050 (Audio) |

---

## Transport

The tool auto-detects whether destination paths are available locally (mounted) or remote. If remote, it uses SCP via the configured transport host and SSH key. Configure with `medcat setup --section transport`.

### Zero Hardcoded Values

No IPs, URLs, API keys, or hostnames are hardcoded. Everything is user-configured via `medcat setup` or `medcat config set`. The tool is fully generic for any media stack.

---

## Related tools

Built on **[scriptkit](scriptkit.md)** — the shared CLI library (color, messages, progress, tables, config, subprocess). Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

Part of the [scripts](../README.md) toolkit — [keyferry](keyferry.md) · [voxtract](voxtract.md) · [netsy](netsy.md) · [pluck](pluck.md) · [aikit](aikit.md)

---

## License

MIT — see [LICENSE](../LICENSE).
