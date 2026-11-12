"""Tests for job tracking and management."""
import time
import pytest
from unittest.mock import Mock, patch

from app.jobs import (
    JobManager, JobStatus, generate_job_id, is_valid_job_id
)


class TestJobManager:
    @pytest.fixture
    def jm(self):
        """Create a fresh JobManager for each test."""
        return JobManager(max_workers=1, job_ttl_seconds=3600)

    def test_create_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
            quality="720p",
            audio_format=None,
        )
        assert job.job_id is not None
        assert is_valid_job_id(job.job_id)
        assert job.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert job.video_id == "dQw4w9WgXcQ"
        assert job.mode == "video"
        assert job.status == JobStatus.PENDING

    def test_get_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        retrieved = jm.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_nonexistent_job(self, jm):
        assert jm.get_job("invalid") is None
        assert jm.get_job("a" * 32) is None

    def test_cancel_pending_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        result = jm.cancel_job(job.job_id)
        assert result is True
        assert job.status == JobStatus.CANCELLED

    def test_cannot_cancel_completed_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        job.status = JobStatus.COMPLETE
        job.finished_at = time.time()
        result = jm.cancel_job(job.job_id)
        assert result is False
        assert job.status == JobStatus.COMPLETE

    def test_submit_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )

        def dummy_fn(j):
            pass

        future = jm.submit_job(job, dummy_fn)
        assert future is not None
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_update_progress(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        updated = jm.update_progress(job.job_id, 50, speed="1.2 MiB/s")
        assert updated.progress == 50
        assert updated.speed == "1.2 MiB/s"

    def test_complete_download(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        completed = jm.complete_download(
            job.job_id,
            "/downloads/dQw4w9WgXcQ.mp4",
            title="Test Video",
            thumbnail="https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            duration=212,
        )
        assert completed.status == JobStatus.COMPLETE
        assert completed.result_path == "/downloads/dQw4w9WgXcQ.mp4"
        assert completed.title == "Test Video"
        assert completed.thumbnail == "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
        assert completed.duration == 212

    def test_fail_job(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        failed = jm.fail_job(job.job_id, "Network error")
        assert failed.status == JobStatus.FAILED
        assert failed.error == "Network error"

    def test_cleanup_old_jobs(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        job.status = JobStatus.COMPLETE
        job.created_at = time.time() - 7200  # 2 hours ago

        jm.cleanup_old_jobs()
        assert jm.get_job(job.job_id) is None

    def test_dont_cleanup_running_jobs(self, jm):
        job = jm.create_job(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            video_id="dQw4w9WgXcQ",
            mode="video",
        )
        job.status = JobStatus.RUNNING
        job.created_at = time.time() - 7200

        jm.cleanup_old_jobs()
        assert jm.get_job(job.job_id) is not None


class TestJobId:
    def test_generate_job_id_format(self):
        job_id = generate_job_id()
        assert is_valid_job_id(job_id)
        assert len(job_id) == 32
        assert all(c in "0123456789abcdef" for c in job_id)

    def test_is_valid_job_id(self):
        # Job IDs are secrets.token_hex(16): exactly 32 lowercase hex chars
        assert is_valid_job_id("a" * 32) is True
        assert is_valid_job_id("0" * 32) is True
        assert is_valid_job_id("f" * 32) is True

    def test_is_valid_job_id_rejects_non_hex(self):
        assert is_valid_job_id("z" * 32) is False
        assert is_valid_job_id("Z" * 32) is False

    def test_is_valid_job_id_false(self):
        assert is_valid_job_id("") is False
        assert is_valid_job_id("abc") is False
        assert is_valid_job_id("a" * 31) is False
        assert is_valid_job_id("a" * 33) is False
        assert is_valid_job_id("g" * 32) is False
        assert is_valid_job_id(None) is False
        assert is_valid_job_id(123) is False
        assert is_valid_job_id("../etc/passwd") is False