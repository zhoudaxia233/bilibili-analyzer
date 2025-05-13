# Bilibili Analyzer

A Python tool to fetch video information from Bilibili using either a video URL/BVID or user UID.

## Features

- Fetch detailed information about a single video using its URL or BVID
- Fetch all videos from a user using their UID
- Extract video subtitles using multiple methods (API, yt-dlp, Whisper AI)
- Beautiful console output using rich formatting with progress indicators
- Support for both bilibili.com and b23.tv URLs
- Automatic handling of video duration and timestamp formatting
- LLM post-processing for Whisper transcripts

## Requirements

- Python >= 3.12, < 4.0
- Poetry for dependency management
- ffmpeg (for audio extraction)

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

This will:
- Fetch all videos uploaded by the user with the given UID
- Display a table with video details (BVID, title, duration, view count, upload time)
- Show the total number of videos found

## Extract Video Text Content

You can extract all text content from a video, including description, subtitles, and comments.

### Extract with default settings

```bash
python main.py BV1xx411c7mD --text
```

This will attempt to extract subtitles using three methods in order:
1. Bilibili API
2. yt-dlp subtitle extraction
3. Whisper AI audio transcription (if the first two methods fail)

### Authentication for premium content

For videos that require authentication:

```bash
python main.py BV1xx411c7mD --text --browser chrome
```

This extracts cookies directly from your browser for authenticated access.

### Control which content to include

```bash
python main.py BV1xx411c7mD --text --content subtitles,comments,uploader
```

### Format options

```bash
python main.py BV1xx411c7mD --text --format markdown
```

### Save output to file

```bash
python main.py BV1xx411c7mD --text -o output.md
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `identifier` | Bilibili video URL, BVID, or user UID (required) |
| `--user` | Fetch all videos from a user (requires UID as identifier) |
| `--text` | Get video text content including subtitles in markdown format |
| `--content` | Comma-separated list of content to include (subtitles,comments,uploader) |
| `--format` | Format for subtitles (plain or markdown) |
| `--comment-limit` | Number of top comments to include (default: 10) |
| `--output`, `-o` | Output file path (if not specified, print to console) |
| `--browser` | Browser to extract cookies from (chrome or firefox) for authenticated access |
| `--debug` | Enable debug logging output |
| `--retry-llm` | Retry LLM post-processing for an existing Whisper transcript |

## Logging and Debug Output

Control the verbosity of logs:

```bash
# Show detailed debug information
python main.py BV1xx411c7mD --text --debug

# Normal operation with only important info
python main.py BV1xx411c7mD --text
```

The debug mode shows:
- Detailed yt-dlp commands and outputs
- API request details
- Whisper processing details
- LLM processing information

## Subtitle Extraction Features

### Subtitle Source Priority

1. **Bilibili Official API**: Attempts to get subtitles through the official API
2. **yt-dlp Subtitle Extraction**: Uses yt-dlp to extract available subtitles
3. **Whisper AI Transcription**: Fallback method that downloads audio and uses Whisper AI for transcription

### Retry LLM Post-Processing

If the LLM post-processing of Whisper transcripts fails or you want to reprocess:

```bash
python main.py BV1xx411c7mD --retry-llm
```

## Environment Variables

Create a `.env` file with the following variables:

```
# Bilibili credentials (optional)
BILIBILI_SESSDATA=your_sessdata
BILIBILI_BILI_JCT=your_bili_jct
BILIBILI_BUVID3=your_buvid3

# LLM configuration for transcript improvement
LLM_MODEL=openai:gpt-4.1-nano
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com # or your custom endpoint
```

## Output

The tool will display the information in a nicely formatted table, including:
- Video title and description
- Duration (in seconds)
- View, like, coin, favorite, and share counts
- Upload time (in YYYY-MM-DD HH:MM:SS format)
- Uploader information

For video text content, it will include:
- Video basic info
- Uploader details
- Tags and categories
- Subtitles (from API, yt-dlp or Whisper)
- Top comments

## Notes

- Rate limiting may apply
- Some videos require authentication for subtitle access
- Whisper transcription quality varies depending on audio quality
- LLM post-processing requires a valid API key and connection
