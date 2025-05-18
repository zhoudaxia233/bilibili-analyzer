# Bilibili Analyzer

A Python tool to fetch video information from Bilibili using either a video URL/BVID or user UID.

## Features

- Fetch detailed information about a single video using its URL or BVID
- Fetch all videos from a user using their UID
- Auto-detect if an identifier is a user UID or video BVID
- Extract video subtitles using multiple methods (API, yt-dlp, Whisper AI)
- Export all subtitles from a user's videos to a single text file
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

Using a user's UID (automatic detection):
```bash
poetry run python main.py 123456
```

You can also explicitly specify to fetch user videos:
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

- Subtitles are always exported as plain text. There is no markdown formatting option.

### Format options

- Subtitles are always exported as plain text. The --format option is no longer available.

### Save output to file

```bash
python main.py BV1xx411c7mD --text -o output.txt
```

## Export All User Subtitles

You can export all subtitles from a user's videos into a single text file:

```bash
python main.py 12345678 --export-user-subtitles
```

This will:
1. Get the list of all videos from the user
2. Extract subtitles from each video using the same 3-step approach (API → yt-dlp → Whisper)
3. Clean up and remove timestamps from the subtitles
4. Add video information header to each video's subtitles
5. Combine all subtitles into a single text file
6. Save the file in a folder named after the user's UID (e.g., `user_12345678/all_subtitles.txt`)
7. Generate a statistics file with processing details

### Authentication for subtitle export

For users with private or premium videos, authentication is required:

```bash
python main.py 12345678 --export-user-subtitles --browser chrome
```

If authentication is needed but not provided, the program will exit early with a clear message.

### Customize the export process

Limit the number of videos to process:
```bash
python main.py 12345678 --export-user-subtitles --subtitle-limit 10
```

Exclude video descriptions from headers:
```bash
python main.py 12345678 --export-user-subtitles --no-description
```

Specify output file:
```bash
python main.py 12345678 --export-user-subtitles -o custom_output.txt
```

### Output files

The tool creates a folder structure for the output:
```
user_12345678/
  ├── all_subtitles.txt    # Combined subtitles from all videos
  └── stats.txt            # Statistics about the processing
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `identifier` | Bilibili video URL, BVID, or user UID (required) |
| `--user` | Explicitly fetch videos from a user (overrides auto-detection) |
| `--text` | Get video text content including subtitles in plain text format |
| `--content` | Comma-separated list of content to include (subtitles,comments,uploader) |
| `--comment-limit` | Number of top comments to include (default: 10) |
| `--output`, `-o` | Output file path (if not specified, print to console) |
| `--browser` | Browser to extract cookies from (chrome or firefox) for authenticated access |
| `--debug` | Enable debug logging output |
| `--retry-llm` | Retry LLM post-processing for an existing Whisper transcript |
| `--export-user-subtitles` | Export all subtitles from a user's videos to a single text file |
| `--subtitle-limit` | Limit the number of videos to process when exporting subtitles |
| `--no-description` | Don't include video descriptions in exported subtitles |
| `--no-meta-info` | Don't include meta info (title, views, coins, etc.) in the header of each video in exported subtitles |
| `--force-charging` | Force download attempt for charging exclusive videos without confirmation prompts |
| `--skip-charging` | Skip charging exclusive videos completely when batch processing |

## Auto-Detection

The tool automatically detects if the identifier is a user UID or a video BVID/URL:
- If the identifier is a purely numeric value with 10 or fewer digits, it's treated as a user UID
- Otherwise, it's treated as a video BVID or URL
- The `--user` flag can be used to override this detection and force user mode

# Handling Charging Exclusive Videos

The tool detects Bilibili's charging exclusive videos (付费充电视频) which require payment for full access:

```bash
# Video info will show charging status
python main.py BV1xx411c7mD
```

When downloading charging exclusive videos:
- By default, the tool warns you that only a preview (typically ~1 minute) is available
- You can choose to continue with the limited content or cancel the download
- After downloading, the tool verifies if the content is complete or truncated

Options for handling charging videos:
```bash
# Skip charging videos entirely when batch processing
python main.py 12345678 --export-user-subtitles --skip-charging

# Force download attempts without confirmation prompts
python main.py 12345678 --export-user-subtitles --force-charging
```

Note: These options do not bypass Bilibili's content protection. You will still only get the free preview portion without proper payment.

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

# Streamlit Web Interface

The project now includes a beautiful Streamlit web interface for easier use of the Bilibili Analyzer.

## Starting the Streamlit App

Since the project uses Poetry for dependency management, you can start the Streamlit app directly after installing dependencies:

```bash
# After running poetry install
poetry run streamlit run app.py
```

Or run it directly after activating the Poetry environment:

```bash
# After activating the environment
streamlit run app.py
```

## Streamlit App Features

The Streamlit interface provides a user-friendly way to use the Bilibili Analyzer:

- **Video Analysis**: Fetch information and text content from Bilibili videos
- **User Analysis**: Export subtitles from a user's videos
- **Visualizations**: Generate charts and graphs to analyze a user's content
- **Settings**: Configure default options for the application
- **Help**: Access comprehensive documentation

## Screenshots

![Bilibili Analyzer Streamlit Interface](https://i.imgur.com/placeholder.png)
