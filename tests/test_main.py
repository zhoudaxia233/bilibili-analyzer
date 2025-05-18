"""Unit tests for main.py module."""

import os
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import argparse

import pytest

from bilibili_client import VideoInfo
from main import (
    load_credentials,
    format_duration,
    display_video_info,
    save_content,
    main,
)


def test_load_credentials():
    """Test loading credentials from environment."""
    # Test with all credentials set
    test_env = {
        "BILIBILI_SESSDATA": "test_sessdata",
        "BILIBILI_BILI_JCT": "test_bili_jct",
        "BILIBILI_BUVID3": "test_buvid3",
    }

    with patch.dict(os.environ, {}, clear=True):  # Start with empty environment
        with patch.dict(os.environ, test_env):  # Then add only our test values
            with patch("pathlib.Path") as MockPath:
                # Mock .env file loading
                mock_path_instance = MagicMock()
                MockPath.return_value = mock_path_instance
                mock_path_instance.__truediv__.return_value = mock_path_instance

                # Mock dotenv.load_dotenv to do nothing
                with patch("main.load_dotenv") as mock_load_dotenv:
                    # Call function
                    creds = load_credentials()

                    # Verify dotenv was attempted to be loaded
                    mock_load_dotenv.assert_called_once()

                    # Verify credentials were loaded from environment
                    assert creds["sessdata"] == "test_sessdata"
                    assert creds["bili_jct"] == "test_bili_jct"
                    assert creds["buvid3"] == "test_buvid3"

    # Test with no credentials set
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path") as MockPath:
            # Mock .env file loading
            mock_path_instance = MagicMock()
            MockPath.return_value = mock_path_instance
            mock_path_instance.__truediv__.return_value = mock_path_instance

            # Mock dotenv.load_dotenv to do nothing
            with patch("main.load_dotenv") as mock_load_dotenv:
                # Mock print to capture warning
                with patch("main.print") as mock_print:
                    # Call function
                    creds = load_credentials()

                    # Verify warning was printed
                    mock_print.assert_called_once()
                    # Verify empty credentials were returned
                    assert creds["sessdata"] is None
                    assert creds["bili_jct"] is None
                    assert creds["buvid3"] is None


def test_format_duration():
    """Test duration formatting."""
    # Test various duration formats using test cases
    test_cases = [
        (0, "00:00:00"),  # 0 seconds
        (30, "00:00:30"),  # 30 seconds
        (65, "00:01:05"),  # 1 minute 5 seconds
        (3600, "01:00:00"),  # 1 hour
        (3665, "01:01:05"),  # 1 hour 1 minute 5 seconds
        (86400, "24:00:00"),  # 24 hours
    ]

    for seconds, expected in test_cases:
        assert format_duration(seconds) == expected


def test_display_video_info(mock_video_info):
    """Test displaying video information."""
    # Create video info object
    video = VideoInfo(**mock_video_info)

    # Capture console output
    with patch("rich.console.Console.print") as mock_print:
        display_video_info(video)

        # Verify console.print was called with a table
        mock_print.assert_called_once()

        # Instead of checking the string representation of the entire table,
        # we'll just verify that a Table object was passed to print
        from rich.table import Table

        table = mock_print.call_args[0][0]
        assert isinstance(table, Table)

        # Verify table title contains video title
        assert video.title in table.title


def test_save_content():
    """Test saving content to file."""
    # Test with output path specified
    test_content = "# Test Content\nThis is test content."

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "output.md")

        with patch("main.rprint") as mock_print:
            # Call function
            save_content(test_content, output_path)

            # Verify file was created with correct content
            with open(output_path, "r") as f:
                saved_content = f.read()
                assert saved_content == test_content

            # Verify success message was printed
            mock_print.assert_called_once()
            assert "Content saved to:" in str(mock_print.call_args[0][0])

    # Test without output path (displays to console)
    with patch("rich.console.Console.print") as mock_print:
        # Call function
        save_content(test_content)

        # Verify content was printed to console
        mock_print.assert_called_once()


@pytest.mark.asyncio
async def test_main_video_info(mock_video_info):
    """Test fetching video information."""
    # Create mock video info object
    video = VideoInfo(**mock_video_info)

    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        # Mock command line arguments
        mock_args = argparse.Namespace(
            identifier="BV1xx411c7mD",
            user=False,
            text=False,
            content="subtitles,uploader",
            output=None,
            browser=None,
            debug=False,
            retry_llm=False,
            export_user_subtitles=False,
            subtitle_limit=None,
            no_description=False,
            no_meta_info=False,
            force_login=False,
            clear_credentials=False,
        )
        mock_parse_args.return_value = mock_args

        # Create a mock client class that won't create unawaited coroutines
        mock_client = MagicMock()
        # Make get_video_info an AsyncMock to properly handle awaiting
        mock_client.get_video_info = AsyncMock(return_value=video)
        # Ensure no other async methods are called that might create coroutines
        mock_client.get_user_videos = AsyncMock()

        # Mock the BilibiliClient class to return our clean mock
        with patch("main.BilibiliClient", return_value=mock_client):
            # Mock display function
            with patch("main.display_video_info") as mock_display:
                # Call function
                await main()

                # Verify video info was fetched and displayed
                mock_client.get_video_info.assert_called_once_with("BV1xx411c7mD")
                mock_display.assert_called_once_with(video)


@pytest.mark.asyncio
async def test_main_user_videos():
    """Test fetching user videos."""
    # Create mock video list
    mock_videos = [
        VideoInfo(
            bvid="BV1xx411c7mD",
            title="Test Video 1",
            description="Description 1",
            duration=300,
            view_count=1000,
            like_count=100,
            coin_count=50,
            favorite_count=30,
            share_count=20,
            comment_count=10,
            upload_time="2023-01-01 12:00:00",
            owner_name="TestUser",
            owner_mid=12345678,
        ),
        VideoInfo(
            bvid="BV2xx411c7mD",
            title="Test Video 2",
            description="Description 2",
            duration=250,
            view_count=2000,
            like_count=200,
            coin_count=100,
            favorite_count=60,
            share_count=40,
            comment_count=20,
            upload_time="2023-01-02 12:00:00",
            owner_name="TestUser",
            owner_mid=12345678,
        ),
    ]

    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        # Mock command line arguments
        mock_args = argparse.Namespace(
            identifier="12345678",
            user=True,  # Explicitly request user videos
            text=False,
            content="subtitles,uploader",
            output=None,
            browser=None,
            debug=False,
            retry_llm=False,
            export_user_subtitles=False,
            subtitle_limit=None,
            no_description=False,
            no_meta_info=False,
            force_login=False,
            clear_credentials=False,
        )
        mock_parse_args.return_value = mock_args

        # Create a complete mock for BilibiliClient that doesn't call any real code
        mock_client = MagicMock()
        # Use AsyncMock for the get_user_videos method
        mock_client.get_user_videos = AsyncMock(return_value=mock_videos)

        # Mock the BilibiliClient class to return our mock client
        with patch("main.BilibiliClient", return_value=mock_client):
            # Mock display function
            with patch("main.display_user_videos") as mock_display:
                # Call main function
                await main()

                # Verify user videos were fetched and displayed
                mock_client.get_user_videos.assert_called_once_with(12345678)
                mock_display.assert_called_once_with(mock_videos)


@pytest.mark.asyncio
async def test_main_video_text():
    """Test getting video text content."""
    # Create mock text content
    mock_content = "# Test Video Title\nTest video content"

    with patch("argparse.ArgumentParser.parse_args") as mock_parse_args:
        # Mock command line arguments
        mock_args = argparse.Namespace(
            identifier="BV1xx411c7mD",
            user=False,
            text=True,  # Request text content
            content="subtitles,uploader",
            output=None,
            browser=None,
            debug=False,
            retry_llm=False,
            export_user_subtitles=False,
            subtitle_limit=None,
            no_description=False,
            no_meta_info=False,
            force_login=False,
            clear_credentials=False,
        )
        mock_parse_args.return_value = mock_args

        # Mock client
        with patch("main.BilibiliClient") as MockClient:
            mock_client = AsyncMock()
            mock_text_content = MagicMock()
            mock_text_content.to_markdown.return_value = mock_content
            mock_client.get_video_text_content = AsyncMock(
                return_value=mock_text_content
            )
            MockClient.return_value = mock_client

            # Mock save function
            with patch("main.save_content") as mock_save:
                # Call function
                await main()

                # Verify text content was fetched and saved
                mock_client.get_video_text_content.assert_called_once()
                mock_save.assert_called_once_with(mock_content, None)
