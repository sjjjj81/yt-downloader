"""Application configuration."""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "data", "downloads")

# Maximum concurrent downloads
MAX_CONCURRENT_DOWNLOADS = 2

# Network timeouts (seconds)
NETWORK_TIMEOUT = 30
EXTRACTOR_TIMEOUT = 60

# Job cleanup: remove completed/failed jobs after this time
JOB_TTL = timedelta(hours=1)

# Maximum request body size
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DOWNLOAD_DIR = DOWNLOAD_DIR
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    MAX_CONCURRENT_DOWNLOADS = MAX_CONCURRENT_DOWNLOADS
    NETWORK_TIMEOUT = NETWORK_TIMEOUT
    EXTRACTOR_TIMEOUT = EXTRACTOR_TIMEOUT
    JOB_TTL = JOB_TTL