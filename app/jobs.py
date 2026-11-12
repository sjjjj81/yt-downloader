"""Thread-safe job tracking and background download workers.

Uses a ThreadPoolExecutor with a bounded number of workers.
State changes are protected by a lock. Job IDs are generated
securely and validated against a strict pattern.
"""

import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.config import Config


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Representation of a single download job."""
    job_id: str
    url: str
    video_id: str
    mode: str  # "video" or "audio"
    quality: Optional[str] = None
    audio_format: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    speed: Optional[str] = None
    downloaded_size: Optional[str] = None
    total_size: Optional[str] = None
    eta: Optional[str] = None
    error: Optional[str] = None
    result_path: Optional[str] = None
    result_url: Optional[str] = None  # relative path safe for client
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "speed": self.speed,
            "downloaded_size": self.downloaded_size,
            "total_size": self.total_size,
            "eta": self.eta,
            "error": self.error,
            "result_url": self.result_url,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "mode": self.mode,
            "quality": self.quality,
            "audio_format": self.audio_format,
            "created_at": self.created_at,
        }

    @property
    def age_seconds(self):
        return time.time() - self.created_at


# Job ID validation: only accept secrets.token_hex(16) format
import re
JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def is_valid_job_id(job_id: str) -> bool:
    """Check that a job ID matches our secure format."""
    if not job_id or not isinstance(job_id, str):
        return False
    return bool(JOB_ID_PATTERN.match(job_id))


def generate_job_id() -> str:
    """Generate a secure random job ID."""
    return secrets.token_hex(16)


class JobManager:
    """Thread-safe manager for download jobs."""

    def __init__(self, max_workers: int = 2, job_ttl_seconds: int = 3600):
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="downloader"
        )
        self._job_ttl = job_ttl_seconds
        self._on_cancel = None  # callback for cancellation

    def set_cancel_callback(self, callback):
        """Set a callback invoked when a job is cancelled."""
        self._on_cancel = callback

    def create_job(self, url, video_id, mode, quality=None, audio_format=None) -> Job:
        """Create a new pending job."""
        job_id = generate_job_id()
        job = Job(
            job_id=job_id,
            url=url,
            video_id=video_id,
            mode=mode,
            quality=quality,
            audio_format=audio_format,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by ID."""
        if not is_valid_job_id(job_id):
            return None
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job. Returns True if cancellation was processed."""
        if not is_valid_job_id(job_id):
            return False
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.RUNNING, JobStatus.PENDING):
                job.status = JobStatus.CANCELLED
                job.finished_at = time.time()
                # Trigger downloader cancel hook if running
                if self._on_cancel and job.status == JobStatus.CANCELLED:
                    self._on_cancel(job)
                return True
            return False

    def submit_job(self, job: Job, fn):
        """Submit a job to the thread pool. Returns the Future."""
        with self._lock:
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
        return self._executor.submit(fn, job)

    def update_progress(self, job_id: str, progress: int, speed=None,
                        downloaded_size=None, total_size=None, eta=None):
        """Thread-safe progress update from downloader hook."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.progress = progress
            job.speed = speed
            job.downloaded_size = downloaded_size
            job.total_size = total_size
            job.eta = eta
            return job

    def complete_download(self, job_id: str, result_path: str, title=None,
                          thumbnail=None, duration=None):
        """Mark job as complete with result."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = JobStatus.COMPLETE
            job.finished_at = time.time()
            job.result_path = result_path
            job.result_url = "/downloads/" + os.path.basename(result_path)
            job.title = title
            job.thumbnail = thumbnail
            job.duration = duration
            return job

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.status = JobStatus.FAILED
            job.finished_at = time.time()
            job.error = error
            return job

    def cleanup_old_jobs(self):
        """Remove jobs older than TTL that are not running."""
        now = time.time()
        with self._lock:
            expired = [
                jid for jid, job in self._jobs.items()
                if (now - job.created_at) > self._job_ttl
                and job.status not in (JobStatus.RUNNING, JobStatus.PENDING)
            ]
            for jid in expired:
                del self._jobs[jid]

    def list_jobs(self) -> list:
        """List all jobs (for monitoring/debugging)."""
        with self._lock:
            return [job for job in self._jobs.values()]

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


import os
