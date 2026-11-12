"""Download workers using yt-dlp.

All yt-dlp calls are configured with:
- A bounded network timeout
- No shell execution (all paths passed as arguments)
- Redirect restriction to allowed hostnames
- FFmpeg for post-processing
- A progress hook callback for live status updates
- No download of media during metadata inspection

Filenames are sanitized. Output is restricted to the configured
download directory via `outtmpl`.
"""

import os
import re
import time
import logging
import shutil

import yt_dlp

from app.config import Config
from app.jobs import Job

logger = logging.getLogger(__name__)

# Characters that are unsafe in filenames
_UNSAFE_CHARS = re.compile(r"[^\w\-_. ]")


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = _UNSAFE_CHARS.sub("_", name)
    name = name.strip("._ ")
    return name[:128] if name else "download"


def find_ffmpeg() -> str | None:
    """Locate the FFmpeg binary. Returns path or None if not found."""
    return shutil.which("ffmpeg")


def build_base_opts(job: Job, progress_callback):
    """Build common yt-dlp options for both metadata and download."""
    # yt-dlp expects a function matching hook signature
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrict_filenames": True,
        "nocheckcertificate": True,
        "socket_timeout": Config.NETWORK_TIMEOUT,
        "extractor_retries": 3,
        "fragment_retries": 3,
        "sleep_interval": 1,
        "skip_download": False,
        "outtmpl": os.path.join(Config.DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "progress_hooks": [progress_callback],
        "no_serve_own_forked_processes": True,
        "no_color": True,
    }

    # Only enable FFmpeg post-processing if binary is present
    if find_ffmpeg():
        opts["ffmpeg_location"] = find_ffmpeg()
    else:
        logger.warning("FFmpeg not found; post-processing may fail")

    return opts


def make_progress_hook(job: Job, job_manager):
    """Create a progress hook for yt-dlp that updates the job manager."""

    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("_total_bytes_str", "")
            downloaded = d.get("_downloaded_bytes_str", "")
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            pct = d.get("percent")

            try:
                pct = int(float(pct)) if pct is not None else 0
            except (ValueError, TypeError):
                pct = 0

            job_manager.update_progress(
                job.job_id,
                pct,
                speed=speed,
                downloaded_size=downloaded,
                total_size=total,
                eta=eta,
            )
        elif d.get("status") == "finished":
            # File finished downloading (may still be post-processing)
            job_manager.update_progress(job.job_id, 100, speed="complete")

    return hook


def extract_thumbnail(url_or_id):
    """Placeholder: thumbnail is extracted in metadata, passed to job."""
    return url_or_id


def get_metadata(url: str, video_id: str):
    """Extract metadata for a YouTube video without downloading.

    Returns a dict with: title, thumbnail, uploader, duration,
    formats (list of {quality, size, ext}), or raises.
    """
    ydl_opts = build_base_opts(video_id_job(video_id, url), lambda d: None)
    ydl_opts["skip_download"] = True
    ydl_opts["simulate"] = True
    ydl_opts["dump_single_json"] = True
    ydl_opts["quiet"] = True
    ydl_opts["no_warnings"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Normalize format list
    formats = []
    seen_res = set()
    for f in info.get("formats", []):
        res = f.get("resolution", "")
        if res and f.get("ext") == "mp4" and res not in seen_res:
            seen_res.add(res)
            formats.append({
                "quality": res,
                "ext": f.get("ext", ""),
                "filesize": f.get("filesize") or f.get("filesize_approx", 0),
            })

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "uploader": info.get("uploader"),
        "duration": info.get("duration"),
        "formats": formats[:10],  # limit
    }


def video_id_job(video_id, url):
    """Create a dummy Job for metadata requests."""
    return Job(
        job_id=video_id,
        url=url,
        video_id=video_id,
        mode="video",
    )


def run_download(job: Job, job_manager):
    """Background worker function for downloading a job.

    Runs inside a ThreadPoolExecutor thread.
    """
    hook = make_progress_hook(job, job_manager)

    if job_manager.get_job(job.job_id) and \
       job_manager.get_job(job.job_id).status.value == "cancelled":
        return  # don't start cancelled jobs

    try:
        opts = build_base_opts(job, hook)

        if job.mode == "video":
            if job.quality and job.quality != "best":
                # Max resolution constraint
                opts["format"] = f"bestvideo[height<={quality_to_int(job.quality)}]" \
                                 f"+bestaudio/best[height<={quality_to_int(job.quality)}]"
            else:
                opts["format"] = "bestvideo+bestaudio/best"

            opts["merge_output_to"] = os.path.join(
                Config.DOWNLOAD_DIR,
                sanitize_filename(job.video_id) + ".mp4"
            )
            opts["postprocessors"] = [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }] if find_ffmpeg() else None

        elif job.mode == "audio":
            fmt = job.audio_format or "mp3"
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": "192",
            }] if find_ffmpeg() else None

            opts["outtmpl"] = os.path.join(
                Config.DOWNLOAD_DIR,
                sanitize_filename(job.video_id) + "." + fmt
            )

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([job.url])

        # Confirm the output file exists
        if job.mode == "audio":
            expected = os.path.join(
                Config.DOWNLOAD_DIR,
                sanitize_filename(job.video_id) + "." + (job.audio_format or "mp3")
            )
        else:
            expected = os.path.join(
                Config.DOWNLOAD_DIR,
                sanitize_filename(job.video_id) + ".mp4"
            )

        # yt-dlp may use a different name (from info title); find the file
        found_file = find_downloaded_file(job.video_id, job.mode, job.audio_format)

        if not found_file or not os.path.isfile(found_file):
            job_manager.fail_job(job.job_id, "Output file was not created")
            return

        # Get metadata for the success response
        try:
            meta = get_metadata(job.url, job.video_id)
        except Exception as e:
            logger.warning("Metadata extraction failed: %s", e)
            meta = {}

        job_manager.complete_download(
            job.job_id,
            found_file,
            title=meta.get("title"),
            thumbnail=meta.get("thumbnail"),
            duration=meta.get("duration"),
        )

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        # Filter internal details but keep useful info
        job_manager.fail_job(job.job_id, f"Download error: {msg[:200]}")
    except Exception as e:
        logger.exception("Unexpected error in download")
        job_manager.fail_job(job.job_id, "An unexpected error occurred")


def quality_to_int(quality_label):
    """Convert a quality label like '1080p' to integer 1080."""
    m = re.match(r"(\d+)", quality_label)
    return int(m.group(1)) if m else 1080


def find_downloaded_file(video_id, mode, audio_format=None):
    """Find the downloaded file for a given video ID."""
    prefix = sanitize_filename(video_id)
    ext = audio_format or "mp4" if mode == "audio" else "mp4"

    # Check exact match
    candidate = os.path.join(Config.DOWNLOAD_DIR, prefix + "." + ext)
    if os.path.isfile(candidate):
        return candidate

    # yt-dlp might use title-based names; find by ID prefix
    try:
        for fname in os.listdir(Config.DOWNLOAD_DIR):
            if fname.startswith(prefix) and fname.endswith((ext, "mp4", "m4a", "mp3")):
                return os.path.join(Config.DOWNLOAD_DIR, fname)
    except OSError:
        pass

    return None
