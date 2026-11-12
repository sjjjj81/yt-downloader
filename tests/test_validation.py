"""Tests for URL validation."""
import pytest
from app.validation import validate_url, extract_video_id


class TestValidation:
    # Valid YouTube URLs
    VALID_URLS = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share", "dQw4w9WgXcQ"),
    ]

    INVALID_URLS = [
        # Empty / None
        ("", "URL is required"),
        ("   ", "URL is required"),
        (None, "URL is required"),
        # Unsupported schemes
        ("ftp://youtube.com/watch?v=dQw4w9WgXcQ", "Unsupported URL scheme"),
        ("file:///etc/passwd", "Unsupported URL scheme"),
        ("javascript:alert(1)", "Unsupported URL scheme"),
        # IP address hostnames
        ("http://127.0.0.1/watch?v=dQw4w9WgXcQ", "IP address URLs are not allowed"),
        ("http://192.168.1.1/watch?v=dQw4w9WgXcQ", "IP address URLs are not allowed"),
        # Localhost (falls under IP check)
        ("http://localhost/watch?v=dQw4w9WgXcQ", "Localhost URLs are not allowed"),
        ("http://127.0.0.1:8080/watch?v=dQw4w9WgXcQ", "IP address URLs are not allowed"),
        # Malformed URLs (caught by scheme check first)
        ("not a url", "Unsupported URL scheme"),
        # Disallowed hostnames
        ("https://evil.com/watch?v=dQw4w9WgXcQ", "Hostname not allowed"),
        ("https://www.evil.com/watch?v=dQw4w9WgXcQ", "Hostname not allowed"),
        ("https://sub.evil.com/watch?v=dQw4w9WgXcQ", "Hostname not allowed"),
        ("https://youtube.evil.com/watch?v=dQw4w9WgXcQ", "Hostname not allowed"),
        # Malformed (caught by scheme check first)
        ("not a url", "Unsupported URL scheme"),
        ("http://", "Missing hostname"),
        ("https://youtube.com", "Unsupported YouTube URL format"),
        ("https://youtu.be", "Unsupported YouTube URL format"),
        # Unsupported YouTube paths
        ("https://www.youtube.com/user/test", "Unsupported YouTube URL format"),
        ("https://www.youtube.com/channel/test", "Unsupported YouTube URL format"),
        ("https://www.youtube.com/playlist?list=PL123", "Unsupported YouTube URL format"),
    ]

    @pytest.mark.parametrize("url,expected_id", VALID_URLS)
    def test_valid_urls(self, url, expected_id):
        is_valid, error, video_id = validate_url(url)
        assert is_valid is True
        assert error is None
        assert video_id == expected_id

    @pytest.mark.parametrize("url,expected_error", INVALID_URLS)
    def test_invalid_urls(self, url, expected_error):
        is_valid, error, video_id = validate_url(url)
        assert is_valid is False
        assert expected_error in error
        assert video_id is None

    def test_extract_video_id_valid(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self):
        assert extract_video_id("https://evil.com/watch?v=dQw4w9WgXcQ") is None
        assert extract_video_id("") is None