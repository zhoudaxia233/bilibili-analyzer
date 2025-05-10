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

## New Feature: Subtitle Downloading with yt-dlp

You can now download subtitles from Bilibili videos using yt-dlp integration. This feature can help extract AI-generated subtitles and other subtitle tracks available for the video.

### Usage Examples

**Download subtitles with authentication:**
```bash
python main.py BV1xx411c7mD --subtitles --use-cookies
```

**Download subtitles directly using browser cookies (recommended):**
```bash
python main.py BV1xx411c7mD --subtitles --browser chrome
```

**Download both audio and subtitles:**
```bash
python main.py https://www.bilibili.com/video/BV1xx411c7mD --download-all --use-cookies
```

**Skip video/audio download and only get subtitles:**
```bash
python main.py BV1xx411c7mD --download-all --browser chrome --skip-download
```

### Command Line Arguments

- `--subtitles`: Download available subtitles for the video
- `--download-all`: Download both audio and subtitles
- `--use-cookies`: Utilize your Bilibili credentials when downloading (required for premium content and some subtitles)
- `--browser {chrome,firefox}`: Extract cookies directly from your browser (alternative to --use-cookies)
- `--skip-download`: Skip downloading actual media files (for subtitle-only downloads)

### Authentication

There are multiple ways to authenticate for accessing subtitles:

1. **Direct browser cookie extraction (recommended):**
   ```bash
   python main.py BV1xx411c7mD --subtitles --browser chrome
   ```
   This extracts cookies directly from your browser, which works best for subtitles.

2. Using the `extract_cookies.py` script to extract cookies first:
   ```bash
   python extract_cookies.py
   python main.py BV1xx411c7mD --subtitles --use-cookies
   ```

3. Providing credentials directly via command line arguments:
   ```bash
   python main.py BV1xx411c7mD --subtitles --use-cookies --sessdata "your_sessdata" --bili-jct "your_bili_jct" --buvid3 "your_buvid3"
   ```

4. Adding credentials to a `.env` file in the project directory:
   ```
   BILIBILI_SESSDATA=your_sessdata
   BILIBILI_BILI_JCT=your_bili_jct
   BILIBILI_BUVID3=your_buvid3
   ```

### Note About Subtitle Formats

Bilibili provides several types of subtitles:

1. **Danmaku**: These are scrolling comments, not traditional subtitles. They are saved in XML format.
2. **AI Subtitles**: Machine-generated subtitles that may be available for some videos.
3. **Manual Subtitles**: User-provided subtitle tracks.

Not all videos have all types of subtitles, and some require authentication to access.

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
