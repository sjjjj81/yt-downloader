"""Integration tests for Flask routes with mocked yt-dlp."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from app import create_app
from app.jobs import Job, JobStatus


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def make_dummy_job(job_id=None, status=JobStatus.PENDING, progress=0, speed=None,
                   downloaded_size=None, total_size=None, eta=None, title="Test Video"):
    jid = job_id or ("a" * 32)
    job = Job(
        job_id=jid,
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ",
        mode="video",
        status=status,
        progress=progress,
        speed=speed,
        downloaded_size=downloaded_size,
        total_size=total_size,
        eta=eta,
        title=title,
        thumbnail="https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        duration=212,
    )
    return job


@pytest.fixture
def mock_job_manager():
    """Provide a mock JobManager that returns canned job data."""
    with patch("app.routes.get_job_manager") as mock:
        jm = MagicMock()
        default_job = make_dummy_job()

        jm.create_job.return_value = default_job
        jm.get_job.return_value = default_job
        jm.cancel_job.return_value = True
        jm.update_progress.return_value = default_job
        jm.complete_download.return_value = default_job
        jm.fail_job.return_value = default_job
        jm.cleanup_old_jobs.return_value = None
        jm.list_jobs.return_value = []

        mock.return_value = jm
        yield jm


class TestValidate:
    def test_validate_valid_url(self, client, mock_job_manager):
        response = client.get("/api/validate?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["video_id"] == "dQw4w9WgXcQ"

    def test_validate_invalid_domain(self, client, mock_job_manager):
        response = client.get("/api/validate?url=https://evil.com/watch?v=dQw4w9WgXcQ")
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False

    def test_validate_empty_url(self, client, mock_job_manager):
        response = client.get("/api/validate?url=")
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False

    def test_validate_ip_address(self, client, mock_job_manager):
        response = client.get("/api/validate?url=http://127.0.0.1/watch?v=dQw4w9WgXcQ")
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False


class TestMetadata:
    def test_metadata_success(self, client, mock_job_manager):
        with patch("app.routes.get_metadata") as mock_meta:
            mock_meta.return_value = {
                "title": "Test Video",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "uploader": "Test Channel",
                "duration": 212,
                "formats": [{"quality": "1080p", "ext": "mp4", "filesize": 1024000}],
            }
            response = client.get(
                "/api/metadata?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["title"] == "Test Video"
            assert data["duration"] == 212

    def test_metadata_invalid_url(self, client, mock_job_manager):
        response = client.get("/api/metadata?url=https://evil.com/watch?v=dQw4w9WgXcQ")
        assert response.status_code in (400, 200)
        data = response.get_json()
        assert "error" in data or data.get("valid") is False


class TestDownloadStart:
    def test_download_start_success(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            job = make_dummy_job(status=JobStatus.PENDING)
            jm.create_job.return_value = job
            jm.submit_job.return_value = None
            jm.list_jobs.return_value = []

            response = client.post(
                "/api/download",
                json={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "mode": "video",
                    "quality": "best",
                    "audio_format": "mp3",
                }
            )
            assert response.status_code == 202
            data = response.get_json()
            assert data["status"] == "pending"
            assert data["job_id"] == job.job_id

    def test_download_start_invalid_url(self, client, mock_job_manager):
        response = client.post(
            "/api/download",
            json={
                "url": "https://evil.com/watch?v=dQw4w9WgXcQ",
                "mode": "video",
                "quality": "best",
                "audio_format": "mp3",
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestJobStatus:
    def test_job_status_found(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            job = make_dummy_job(status=JobStatus.COMPLETE, title="Test Video")
            jm.get_job.return_value = job

            response = client.get("/api/status/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            assert response.status_code == 200
            data = response.get_json()
            assert data["job_id"] == job.job_id
            assert data["status"] == "complete"
            assert data["title"] == "Test Video"

    def test_job_status_not_found(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            jm.get_job.return_value = None

            # Valid 32-char hex ID that is not found
            response = client.get("/api/status/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
            assert response.status_code == 404
            data = response.get_json()
            assert data["error"] == "Job not found"

    def test_job_status_invalid_id(self, client, mock_job_manager):
        response = client.get("/api/status/abc")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_job_status_with_progress(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            job = make_dummy_job(
                status=JobStatus.RUNNING,
                progress=42,
                speed="1.5 MiB/s",
                downloaded_size="5000000",
                total_size="12000000",
                eta="00:03:20",
                title="Downloading...",
            )
            jm.get_job.return_value = job

            response = client.get("/api/status/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            assert response.status_code == 200
            data = response.get_json()
            assert data["progress"] == 42
            assert data["speed"] == "1.5 MiB/s"
            assert data["eta"] == "00:03:20"


class TestCancel:
    def test_cancel_running_job(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            job = make_dummy_job(status=JobStatus.RUNNING)
            jm.get_job.return_value = job
            jm.cancel_job.return_value = True

            response = client.post("/api/cancel/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "cancelled"

    def test_cancel_pending_job(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            job = make_dummy_job(status=JobStatus.PENDING)
            jm.get_job.return_value = job
            jm.cancel_job.return_value = True

            response = client.post("/api/cancel/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "cancelled"

    def test_cancel_nonexistent_job(self, client, mock_job_manager):
        with patch("app.routes.get_job_manager") as mock_get_jm:
            jm = mock_get_jm.return_value
            jm.get_job.return_value = None
            jm.cancel_job.return_value = False

            response = client.post("/api/cancel/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data


class TestFileDownload:
    def test_download_file_valid(self, client, mock_job_manager):
        with patch("os.path.isfile", return_value=True), \
             patch("app.routes.send_from_directory") as mock_send:
            mock_send.return_value = ("file_content", 200)
            response = client.get("/downloads/test.mp4")
            assert response.status_code == 200

    def test_download_file_invalid(self, client, mock_job_manager):
        response = client.get("/downloads/../../../etc/passwd")
        assert response.status_code in (400, 403, 404)

    def test_download_file_missing(self, client, mock_job_manager):
        with patch("os.path.isfile", return_value=False):
            response = client.get("/downloads/nonexistent.mp4")
            assert response.status_code == 404


class TestOriginCheck:
    def test_origin_allowed(self, client, mock_job_manager):
        """Allowed origins are our own hostname."""
        with patch("app.routes.get_job_manager"):
            response = client.post(
                "/api/cancel/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                headers={"Origin": "http://localhost"}
            )
            # Origin http://localhost matches localhost test host
            assert response.status_code != 403

    def test_origin_blocked(self, client, mock_job_manager):
        """Cross-origin requests are blocked."""
        with patch("app.routes.get_job_manager"):
            response = client.post(
                "/api/cancel/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                headers={"Origin": "https://evil-site.com"},
                json={"job_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
            )
            assert response.status_code == 403
