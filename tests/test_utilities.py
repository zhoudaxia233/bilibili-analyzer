"""Unit tests for utilities.py module."""

import json
import time
from pathlib import Path

from utilities import (
    get_credentials_path,
    load_cached_credentials,
    save_credentials,
    ensure_bilibili_url,
    format_time_ago,
    remove_timestamps,
    format_subtitle_header,
)


def test_get_credentials_path(mocker):
    """Test credentials path generation."""
    mock_home = mocker.patch("pathlib.Path.home")
    mock_home.return_value = Path("/home/user")
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")

    path = get_credentials_path()
    assert path == Path("/home/user/.config/bilibili_analyzer/credentials.json")
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_load_cached_credentials_no_file(mocker):
    """Test loading credentials when file doesn't exist."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    assert load_cached_credentials() == {}
    assert load_cached_credentials(browser="chrome") is None


def test_load_cached_credentials(mocker, mock_credentials_file, mock_credentials):
    """Test loading credentials from file."""
    mocker.patch("utilities.get_credentials_path", return_value=mock_credentials_file)
    # Mock the current time to be 1 hour after the fixtures' timestamp
    mocker.patch("time.time", return_value=1684000000 + 3600)

    # Test loading all credentials
    creds = load_cached_credentials()
    assert "chrome" in creds
    assert creds["chrome"]["cookies"] == mock_credentials

    # Test loading specific browser credentials
    browser_creds = load_cached_credentials(browser="chrome")
    assert browser_creds == mock_credentials

    # Test browser not in credentials
    assert load_cached_credentials(browser="firefox") is None


def test_load_cached_credentials_expired(mocker):
    """Test loading expired credentials."""
    mock_path = mocker.patch("utilities.get_credentials_path")
    mock_path.return_value = Path("credentials.json")
    mocker.patch("pathlib.Path.exists", return_value=True)
    mock_read = mocker.patch("pathlib.Path.read_text")

    # Create credentials with timestamp from 31 days ago
    current_time = time.time()
    old_timestamp = current_time - (31 * 24 * 3600)
    mock_read.return_value = json.dumps(
        {
            "chrome": {
                "cookies": {"sessdata": "test"},
                "timestamp": old_timestamp,
            }
        }
    )

    # Mock current time to be 31 days after the timestamp
    mocker.patch("time.time", return_value=current_time)

    # Should return None for expired credentials
    assert load_cached_credentials(browser="chrome") is None


def test_save_credentials(mocker, mock_temp_dir, mock_credentials):
    """Test saving credentials to file."""
    creds_path = mock_temp_dir / "test_creds.json"

    mocker.patch("utilities.get_credentials_path", return_value=creds_path)
    mocker.patch("utilities.load_cached_credentials", return_value={})
    mock_chmod = mocker.patch("os.chmod")

    # Save credentials
    result = save_credentials("chrome", mock_credentials)
    assert result is True

    # Verify file content
    saved_data = json.loads(creds_path.read_text())
    assert "chrome" in saved_data
    assert saved_data["chrome"]["cookies"] == mock_credentials
    assert "timestamp" in saved_data["chrome"]

    # Verify permissions were set
    mock_chmod.assert_called_once_with(creds_path, 0o600)


def test_ensure_bilibili_url():
    """Test URL normalization for BVIDs."""
    # Test with BVID
    assert (
        ensure_bilibili_url("BV1xx411c7mD")
        == "https://www.bilibili.com/video/BV1xx411c7mD"
    )

    # Test with lowercase BVID
    assert (
        ensure_bilibili_url("bv1xx411c7mD")
        == "https://www.bilibili.com/video/bv1xx411c7mD"
    )

    # Test with existing URL
    url = "https://www.bilibili.com/video/BV1xx411c7mD"
    assert ensure_bilibili_url(url) == url

    # Test with short BVID (should return as-is)
    short_id = "BV1"
    assert ensure_bilibili_url(short_id) == short_id

    # Test with numeric string (not a BVID)
    uid = "12345678"
    assert ensure_bilibili_url(uid) == uid


def test_format_time_ago():
    """Test human-readable time conversion."""
    now = time.time()

    # Test all time ranges with meaningful cases
    test_cases = [
        (now - 30, "30 seconds ago"),  # seconds
        (now - 60, "1 minute ago"),  # single minute
        (now - 120, "2 minutes ago"),  # multiple minutes
        (now - 3600, "1 hour ago"),  # single hour
        (now - 7200, "2 hours ago"),  # multiple hours
        (now - 86400, "1 day ago"),  # single day
        (now - 172800, "2 days ago"),  # multiple days
    ]

    for timestamp, expected in test_cases:
        assert format_time_ago(timestamp) == expected


def test_remove_timestamps():
    """Test timestamp removal from subtitle text."""
    # Test with standard SRT format
    srt_text = "1\n00:00:01,000 --> 00:00:05,000\nFirst line\n\n2\n00:00:06,000 --> 00:00:10,000\nSecond line"
    expected = "First line\n\nSecond line"
    assert remove_timestamps(srt_text) == expected

    # Test with empty string
    assert remove_timestamps("") == ""

    # Test with text without timestamps
    plain_text = "Just some text\nwithout timestamps"
    assert remove_timestamps(plain_text) == plain_text

    # Test with malformed timestamps
    malformed = "1\n00:00:01 -> 00:00:05\nMalformed\n\n2\n00:00:06,000 --> 00:00:10,000\nSecond line"
    expected_malformed = "1\n00:00:01 -> 00:00:05\nMalformed\n\nSecond line"
    assert remove_timestamps(malformed) == expected_malformed


def test_format_subtitle_header(mock_video_info):
    """Test subtitle header formatting."""
    # Test with all info included
    result = format_subtitle_header(
        mock_video_info, include_description=True, include_meta_info=True
    )

    # Check that the header contains expected information
    assert "# Test Video Title" in result
    assert "This is a test video description" in result
    assert "Views: 12,345" in result
    assert "Likes: 1,000" in result

    # Test without description
    result_no_desc = format_subtitle_header(
        mock_video_info, include_description=False, include_meta_info=True
    )
    assert "This is a test video description" not in result_no_desc
    assert "Views: 12,345" in result_no_desc

    # Test without meta info
    result_no_meta = format_subtitle_header(
        mock_video_info, include_description=True, include_meta_info=False
    )
    assert "This is a test video description" in result_no_meta
    assert "Views:" not in result_no_meta
    assert "Likes:" not in result_no_meta
