"""Flask application routes for YouTube Downloader Phase 3.

Endpoints:
- GET  /api/validate?url=...   Validate a YouTube URL
- GET  /api/metadata?url=...   Extract metadata (title, thumbnail, formats)
- POST /api/download          Start a download job
- GET  /api/status/<job_id>   Poll job status/progress
- POST /api/cancel/<job_id>   Cancel a running job
- GET  /downloads/<filename>  Serve downloaded file (sanitized)

All endpoints validate job IDs and inputs. State-changing routes
are protected with CSRF-style origin checking.
"""

import os
import re
from flask import (
    Blueprint, render_template, jsonify, request, send_from_directory,
    current_app, abort
)

from app.config import Config
from app.validation import validate_url
from app.downloader import get_metadata, run_download
from app.jobs import (
    JobManager, JobStatus, is_valid_job_id, generate_job_id
)

main = Blueprint("main", __name__)

# Module-level singleton
job_manager = None


def get_job_manager():
    """Lazily initialize the job manager."""
    global job_manager
    if job_manager is None:
        job_manager = JobManager(
            max_workers=Config.MAX_CONCURRENT_DOWNLOADS,
            job_ttl_seconds=int(Config.JOB_TTL.total_seconds()),
        )
        # Register cancellation callback
        job_manager.set_cancel_callback(_on_job_cancelled)
    return job_manager


def _on_job_cancelled(job):
    """Called when a job is cancelled - can be expanded for yt-dlp cleanup."""
    pass


def check_origin():
    """Reject cross-origin state-changing requests."""
    origin = request.headers.get("Origin", "")
    if origin:
        # Allow only our own origin
        host = request.host
        allowed = [
            f"http://{host}",
            f"https://{host}",
            "",
        ]
        if origin not in allowed:
            abort(403, "Cross-origin request blocked")


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@main.route("/api/validate")
def validate():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"valid": False, "error": "URL parameter is required"}), 200

    is_valid, error, video_id = validate_url(url)
    if not is_valid:
        return jsonify({"valid": False, "error": error}), 200

    return jsonify({"valid": True, "video_id": video_id}), 200


@main.route("/api/metadata")
def metadata():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400

    is_valid, error, video_id = validate_url(url)
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        data = get_metadata(url, video_id)
        return jsonify(data), 200
    except Exception as e:
        # Avoid leaking internal details
        return jsonify({"error": "Could not extract metadata"}), 500


@main.route("/api/download", methods=["POST"])
def start_download():
    check_origin()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    url = data.get("url", "").strip()
    mode = data.get("mode", "video")
    quality = data.get("quality", "best")
    audio_format = data.get("audio_format", "mp3")

    # Validate URL
    is_valid, error, video_id = validate_url(url)
    if not is_valid:
        return jsonify({"error": error}), 400

    # Validate mode
    if mode not in ("video", "audio"):
        return jsonify({"error": "Invalid mode"}), 400

    # Validate quality for video mode
    if mode == "video" and quality not in ("best", "1080", "720", "480"):
        return jsonify({"error": "Invalid quality"}), 400

    # Validate audio format
    if mode == "audio" and audio_format not in ("mp3", "m4a"):
        return jsonify({"error": "Invalid audio format"}), 400

    # Convert quality label to resolution int for downloader
    quality_label = quality if quality != "best" else "best"
    if mode == "video" and quality != "best":
        quality_label = f"{quality}p"

    # Check capacity
    jm = get_job_manager()
    jm.cleanup_old_jobs()

    running_count = sum(
        1 for j in jm.list_jobs()
        if j.status in (JobStatus.RUNNING, JobStatus.PENDING)
    )
    if running_count >= Config.MAX_CONCURRENT_DOWNLOADS:
        return jsonify({"error": "Maximum concurrent downloads reached. Please wait."}), 429

    # Create job
    job = jm.create_job(
        url=url,
        video_id=video_id,
        mode=mode,
        quality=quality_label,
        audio_format=audio_format if mode == "audio" else None,
    )

    # Submit to background worker
    jm.submit_job(job, lambda j: run_download(j, jm))

    return jsonify({
        "job_id": job.job_id,
        "status": "pending",
        "message": "Download started"
    }), 202


@main.route("/api/status/<job_id>")
def job_status(job_id):
    if not is_valid_job_id(job_id):
        return jsonify({"error": "Invalid job ID"}), 400

    jm = get_job_manager()
    job = jm.get_job(job_id)

    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict()), 200


@main.route("/api/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    check_origin()

    if not is_valid_job_id(job_id):
        return jsonify({"error": "Invalid job ID"}), 400

    jm = get_job_manager()
    cancelled = jm.cancel_job(job_id)

    if not cancelled:
        return jsonify({"error": "Cannot cancel job"}), 400

    return jsonify({"status": "cancelled"}), 200


@main.route("/downloads/<path:filename>")
def download_file(filename):
    """Serve a downloaded file if it exists in the download directory.

    Only allows filenames matching a safe pattern (alphanumeric, dash,
    underscore, dot) to prevent path traversal.
    """
    # Sanitize filename
    if not re.match(r"^[A-Za-z0-9_\-\.]+$", filename):
        abort(400, "Invalid filename")

    # Prevent directory traversal
    safe_path = os.path.normpath(filename)
    if safe_path.startswith("..") or safe_path.startswith("/"):
        abort(400, "Invalid path")

    download_dir = os.path.abspath(Config.DOWNLOAD_DIR)
    full_path = os.path.abspath(os.path.join(download_dir, safe_path))

    # Ensure the resolved path is inside the download directory
    if not full_path.startswith(download_dir):
        abort(403, "Access denied")

    if not os.path.isfile(full_path):
        abort(404, "File not found")

    return send_from_directory(download_dir, safe_path)
