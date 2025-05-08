# Bilibili Analyzer

A Python tool to fetch video information from Bilibili using either a video URL/BVID or user UID.

## Features

- Fetch detailed information about a single video using its URL or BVID
- Fetch all videos from a user using their UID
- Beautiful console output using rich formatting
- Support for both bilibili.com and b23.tv URLs
- Automatic handling of video duration and timestamp formatting

## Requirements

- Python >= 3.12, < 4.0
- Poetry for dependency management

## Installation

1. Clone this repository
2. Install dependencies using Poetry:
```bash
poetry install
```

## Usage

### Fetch information about a single video

Using a Bilibili URL:
```bash
poetry run python main.py "https://www.bilibili.com/video/BV1xx411c7mD"
```

Using a BVID:
```bash
poetry run python main.py "BV1xx411c7mD"
```

### Fetch all videos from a user

Using a user's UID:
```bash
poetry run python main.py 123456 --user
```

## Download Audio Only

You can download only the audio track of a Bilibili video using the `--audio` flag. This uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) under the hood and requires [ffmpeg](https://ffmpeg.org/) to be installed on your system.

### Usage

```bash
python main.py <video_url_or_BVID> --audio
```

This will download the best available audio stream for the given video URL or BVID.

**Note:**
- [ffmpeg](https://ffmpeg.org/) must be installed and available in your system PATH for audio extraction to work.

## Output

The tool will display the information in a nicely formatted table, including:
- Video title and description
- Duration (in seconds)
- View, like, coin, favorite, and share counts
- Upload time (in YYYY-MM-DD HH:MM:SS format)
- Uploader information


For user videos, it will show a list of all videos with their basic information.

## Notes

- Rate limiting may apply
- Some information might not be available for all videos
