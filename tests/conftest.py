"""Common fixtures for Bilibili Analyzer tests."""

import os
import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def mock_temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield Path(temp_dir)
        os.chdir(old_cwd)


@pytest.fixture
def mock_credentials():
    """Sample credentials for testing."""
    return {
        "sessdata": "test_sessdata",
        "bili_jct": "test_bili_jct",
        "buvid3": "test_buvid3",
    }


@pytest.fixture
def mock_credentials_file(mock_temp_dir, mock_credentials):
    """Create a mock credentials file."""
    creds_path = mock_temp_dir / "credentials.json"
    creds_data = {
        "chrome": {
            "cookies": mock_credentials,
            "timestamp": 1684000000,  # Fixed timestamp for testing
        }
    }
    creds_path.write_text(json.dumps(creds_data))
    return creds_path


@pytest.fixture
def mock_video_info():
    """Sample video info for testing."""
    return {
        "bvid": "BV1xx411c7mD",
        "title": "Test Video Title",
        "description": "This is a test video description",
        "duration": 300,  # 5 minutes
        "view_count": 12345,
        "like_count": 1000,
        "coin_count": 500,
        "favorite_count": 300,
        "share_count": 200,
        "comment_count": 100,
        "upload_time": "2023-01-01 12:00:00",
        "owner_name": "TestUser",
        "owner_mid": 12345678,
    }


@pytest.fixture
def mock_video_api_response():
    """Sample Bilibili API response for a video."""
    return {
        "code": 0,
        "message": "0",
        "ttl": 1,
        "data": {
            "bvid": "BV1xx411c7mD",
            "aid": 12345678,
            "videos": 1,
            "tid": 28,
            "tname": "原创音乐",
            "copyright": 1,
            "pic": "http://i0.hdslb.com/test.jpg",
            "title": "Test Video Title",
            "pubdate": 1672563600,  # 2023-01-01 12:00:00
            "ctime": 1672563600,
            "desc": "This is a test video description",
            "duration": 300,
            "owner": {
                "mid": 12345678,
                "name": "TestUser",
                "face": "http://i1.hdslb.com/user.jpg",
            },
            "stat": {
                "aid": 12345678,
                "view": 12345,
                "danmaku": 200,
                "reply": 100,
                "favorite": 300,
                "coin": 500,
                "share": 200,
                "now_rank": 0,
                "his_rank": 0,
                "like": 1000,
                "dislike": 0,
            },
            "cid": 87654321,
        },
    }


@pytest.fixture
def mock_user_videos_response():
    """Sample Bilibili API response for user videos."""
    return {
        "code": 0,
        "message": "0",
        "ttl": 1,
        "data": {
            "list": {
                "vlist": [
                    {
                        "comment": 100,
                        "typeid": 28,
                        "play": 12345,
                        "pic": "http://i0.hdslb.com/test1.jpg",
                        "subtitle": "",
                        "description": "Test video 1",
                        "copyright": "1",
                        "title": "Test Video 1",
                        "review": 0,
                        "author": "TestUser",
                        "mid": 12345678,
                        "created": 1672563600,
                        "length": "05:00",
                        "video_review": 200,
                        "aid": 12345678,
                        "bvid": "BV1xx411c7mD",
                        "hide_click": False,
                        "is_pay": 0,
                        "is_union_video": 0,
                        "is_steins_gate": 0,
                        "is_live_playback": 0,
                    },
                    {
                        "comment": 50,
                        "typeid": 28,
                        "play": 5000,
                        "pic": "http://i0.hdslb.com/test2.jpg",
                        "subtitle": "",
                        "description": "Test video 2",
                        "copyright": "1",
                        "title": "Test Video 2",
                        "review": 0,
                        "author": "TestUser",
                        "mid": 12345678,
                        "created": 1671354000,
                        "length": "03:30",
                        "video_review": 100,
                        "aid": 87654321,
                        "bvid": "BV2xx411c7mD",
                        "hide_click": False,
                        "is_pay": 0,
                        "is_union_video": 0,
                        "is_steins_gate": 0,
                        "is_live_playback": 0,
                    },
                ]
            },
            "page": {"pn": 1, "ps": 30, "count": 2},
        },
    }


@pytest.fixture
def mock_subtitle_content():
    """Sample subtitle content for testing."""
    return "1\n00:00:01,000 --> 00:00:05,000\nThis is the first subtitle line\n\n2\n00:00:06,000 --> 00:00:10,000\nThis is the second subtitle line"
