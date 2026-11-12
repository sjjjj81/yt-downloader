"""URL validation for YouTube downloader.

Enforces a strict hostname allowlist and accepted YouTube URL forms.
Rejects arbitrary domains, IP-address URLs, localhost, unsupported schemes,
and malformed inputs.
"""

import ipaddress
import re
from urllib.parse import urlparse

# Hostname allowlist — only these YouTube hostnames are permitted.
ALLOWED_HOSTNAMES = frozenset({
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
})

VIDEO_ID_RE = r"[\w-]{11}"
CAPTURED_VIDEO_ID = r"([A-Za-z0-9_-]{11})"

# Accepted YouTube URL patterns. Each pattern captures the video ID in group 1.
YOUTUBE_PATTERNS = (
    re.compile(
        r"^https?://(?:www\.)?youtube\.com/watch\?v=" + CAPTURED_VIDEO_ID + r"(?:&.*)?$",
        re.IGNORECASE,
    ),
    re.compile(r"^https?://youtu\.be/" + CAPTURED_VIDEO_ID + r"$", re.IGNORECASE),
    re.compile(
        r"^https?://m\.youtube\.com/watch\?v=" + CAPTURED_VIDEO_ID + r"(?:&.*)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^https?://(?:www\.)?youtube\.com/embed/" + CAPTURED_VIDEO_ID + r"$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^https?://(?:www\.)?youtube\.com/shorts/" + CAPTURED_VIDEO_ID + r"$",
        re.IGNORECASE,
    ),
    re.compile(r"^https?://(?:www\.)?youtube\.com/v/" + CAPTURED_VIDEO_ID + r"$", re.IGNORECASE),
)


def validate_url(url):
    """Validate a YouTube URL.

    Returns (is_valid, error_message_or_None, video_id_or_None).
    """
    if not url or not isinstance(url, str):
        return False, "URL is required", None

    url = url.strip()
    if not url:
        return False, "URL is required", None

    # Quick rejects before parsing
    lower = url.lower()
    if lower.startswith("javascript:") or lower.startswith("data:"):
        return False, "Unsupported URL scheme", None

    # Basic URL format check
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return False, "Unsupported URL scheme", None

    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False, "Malformed URL", None

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname", None

    # Reject IP-address hostnames (includes 127.0.0.1)
    try:
        ipaddress.ip_address(hostname)
        return False, "IP address URLs are not allowed", None
    except ValueError:
        pass

    # Reject localhost (non-IP forms)
    if hostname.lower() in ("localhost", "::1", "0.0.0.0"):
        return False, "Localhost URLs are not allowed", None

    # Hostname allowlist
    if hostname.lower() not in ALLOWED_HOSTNAMES:
        return False, "Hostname not allowed", None

    # Pattern match against accepted YouTube forms
    for pattern in YOUTUBE_PATTERNS:
        m = pattern.match(url)
        if m:
            # Patterns have single group for video ID
            vid = m.group(1) if m.groups() else None
            if vid:
                return True, None, vid

    return False, "Unsupported YouTube URL format", None


def extract_video_id(url):
    """Extract the YouTube video ID from a validated URL string."""
    valid, _, vid = validate_url(url)
    return vid if valid else None


def is_safe_redirect(url):
    """Check that a redirect URL points to an allowed hostname.

    yt-dlp is configured to not follow redirects outside this list.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    return hostname.lower() in ALLOWED_HOSTNAMES