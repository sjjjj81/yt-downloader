# YouTube Downloader

Local browser-based YouTube downloader using Flask and yt-dlp.

## Requirements

- **Python 3.11+** — [python.org/downloads/](https://www.python.org/downloads/)
- **FFmpeg** (recommended) — for audio extraction and video merging:
  - [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
  - Chocolatey: `choco install ffmpeg`
  - winget: `winget install FFmpeg`
- **Node.js** (optional) — some yt-dlp extractors benefit from it:
  - [nodejs.org](https://nodejs.org/)

## Quick Start (Windows)

```bat
setup.bat    # Creates virtual environment and installs dependencies
start.bat    # Starts the application
```

Then open **http://127.0.0.1:5000** in your browser.

## Manual Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # On Windows
pip install -r requirements.txt
python run.py
```

## Running Tests

```bash
pytest tests/
```

## Usage

1. Paste a YouTube URL into the input field.
2. The app fetches video metadata automatically (title, thumbnail, available formats).
3. Choose **Video** or **Audio** mode.
4. Select quality (video) or format (audio).
5. Click **Download**.
6. Track progress in real-time; cancel anytime.
7. Downloaded files appear in the **Recent Downloads** list.
8. Most importantly create a Data folder then inside it create a downloads folder,all your downloads will be saved their
Supported URL formats:
- `https://www.youtube.com/watch?v=<id>`
- `https://youtu.be/<id>`
- `https://www.youtube.com/shorts/<id>`
- `https://www.youtube.com/embed/<id>`

## Configuration

Edit `app/config.py` to change defaults:

| Setting | Default | Description |
|---|---|---|
| `DOWNLOAD_DIR` | `data/downloads` | Where files are saved |
| `MAX_CONCURRENT_DOWNLOADS` | 2 | Parallel download limit |
| `NETWORK_TIMEOUT` | 30 | Seconds before connection timeout |
| `JOB_TTL` | 1 hour | How long job records are kept |
| `PORT` | 5000 | Flask server port (`start.bat`) |

## Troubleshooting

### "Python is not found in PATH"
During Python installation, check **Add Python to PATH**. Then restart your terminal.

### "FFmpeg not found"
Install FFmpeg (see Requirements above). Without it, audio extraction fails and video streams may not merge. Direct video downloads still work.

### "Port 5000 is already in use"
```bat
netstat -ano | findstr ":5000"
```
Find the PID and close the process, or edit `start.bat` to use a different port.

### "Required packages are missing"
Re-run `setup.bat`. If that fails, delete the `.venv` folder and run `setup.bat` again.

### "Virtual environment not found"
Run `setup.bat` first. It creates `.venv` and installs all dependencies.

## Limitations

- **Browser-only**: The app runs as a local web server. No standalone desktop executable.
- **YouTube only**: Only YouTube and YouTube Shorts URLs are accepted.
- **Windows batch files**: `setup.bat` and `start.bat` are Windows-only. macOS/Linux users should use the manual setup steps above.
- **No account login**: This tool does not support downloading copyrighted content you do not have rights to access.
- **Rate limits**: YouTube may rate-limit requests. Space out your downloads.
- **FFmpeg required for audio**: Audio extraction (mp3/m4a) requires FFmpeg. Without it, only raw video downloads work.
- **Single-user**: The server binds to `127.0.0.1` only. It is not accessible from other machines on the network.

## Security

- All URLs are validated against a strict hostname allowlist (youtube.com, youtu.be only).
- IP addresses, localhost, and arbitrary domains are rejected.
- Filenames are sanitized; path traversal is blocked.
- State-changing endpoints check the `Origin` header.
- The server binds only to `127.0.0.1` — it is not exposed to the network.
- Untrusted metadata from YouTube is HTML-escaped before display.

## Project Structure

```
├── app/
│   ├── __init__.py        # Flask application factory
│   ├── config.py          # Configuration
│   ├── routes.py          # HTTP endpoints
│   ├── jobs.py            # Job tracking and state
│   ├── validation.py      # URL validation
│   ├── downloader.py      # yt-dlp integration
│   ├── templates/
│   │   └── index.html     # Frontend page
│   └── static/
│       ├── css/style.css  # Styles
│       └── js/app.js      # Frontend logic
├── tests/                 # pytest test suite
├── data/downloads/        # Downloaded files
├── setup.bat              # One-click setup (Windows)
├── start.bat              # One-click start (Windows)
├── run.py                 # Entry point
└── requirements.txt       # Python dependencies
```
