import os
import asyncio
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.markdown import Markdown
from bilibili_client import BilibiliClient, VideoInfo, VideoTextConfig
from utilities import ensure_bilibili_url, download_with_ytdlp


def load_credentials():
    """Load credentials from .env file and environment variables"""
    # Try to load from .env file in the current directory
    env_path = Path(".") / ".env"
    load_dotenv(env_path)

    # Get credentials from environment variables
    credentials = {
        "sessdata": os.getenv("BILIBILI_SESSDATA"),
        "bili_jct": os.getenv("BILIBILI_BILI_JCT"),
        "buvid3": os.getenv("BILIBILI_BUVID3"),
    }

    # Check if we have any credentials
    if not any(credentials.values()):
        print(
            "[yellow]Warning: No Bilibili credentials found. Some features like subtitles may not work.[/yellow]"
        )

    return credentials


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def display_video_info(video: VideoInfo):
    """Display video information in a formatted table"""
    console = Console()
    table = Table(title=f"Video Information: {video.title}")

    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("BVID", video.bvid)
    table.add_row("Title", video.title)
    table.add_row("Description", video.description)
    table.add_row("Duration", format_duration(video.duration))
    table.add_row("Views", str(video.view_count))
    table.add_row("Likes", str(video.like_count))
    table.add_row("Coins", str(video.coin_count))
    table.add_row("Favorites", str(video.favorite_count))
    table.add_row("Shares", str(video.share_count))
    table.add_row("Upload Time", video.upload_time)
    table.add_row("Uploader", f"{video.owner_name} (UID: {video.owner_mid})")

    console.print(table)


def display_user_videos(videos: list[VideoInfo]):
    """Display a list of videos in a formatted table"""
    console = Console()
    table = Table(title=f"User Videos (Total: {len(videos)})")

    table.add_column("BVID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Views", style="magenta")
    table.add_column("Upload Time", style="blue")

    for video in videos:
        table.add_row(
            video.bvid,
            video.title,
            format_duration(video.duration),
            str(video.view_count),
            video.upload_time,
        )

    console.print(table)


def display_markdown_content(content: str):
    """Display markdown content using rich"""
    console = Console()
    md = Markdown(content)
    console.print(md)


def save_content(content: str, output_path: str = None):
    """Save or display content"""
    if output_path:
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        rprint(f"[green]Content saved to:[/green] {output_path}")
    else:
        # Display in console
        console = Console()
        md = Markdown(content)
        console.print(md)


async def main():
    parser = argparse.ArgumentParser(description="Bilibili Video Information Fetcher")
    parser.add_argument("identifier", help="Bilibili video URL, BVID, or user UID")
    parser.add_argument(
        "--user",
        action="store_true",
        help="Fetch all videos from a user (requires UID)",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Get video text content in markdown format",
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Don't include subtitles in text content",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Don't include comments in text content",
    )
    parser.add_argument(
        "--no-uploader",
        action="store_true",
        help="Don't include detailed uploader info in text content",
    )
    parser.add_argument(
        "--comment-limit",
        type=int,
        default=10,
        help="Number of top comments to include (default: 10)",
    )
    parser.add_argument(
        "--subtitle-markdown",
        action="store_true",
        help="Format subtitles in markdown style",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (if not specified, print to console)",
        default=None,
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox"],
        help="Browser to extract cookies from for authenticated access",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Download audio file of the video using yt-dlp",
    )
    parser.add_argument(
        "--subtitles",
        action="store_true",
        help="Download video subtitles using yt-dlp",
    )
    parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download both audio and subtitles using yt-dlp",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading actual media files (for subtitle-only downloads)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.getLogger("bilibili_client").setLevel(logging.DEBUG)

    # Load credentials from .env
    credentials = load_credentials()

    # Handle download requests
    if args.audio or args.subtitles or args.download_all:
        try:
            url = ensure_bilibili_url(args.identifier)

            if args.download_all:
                download_type = "all"
            elif args.subtitles:
                download_type = "subtitles"
            else:
                download_type = "audio"

            # Force skip-download if the flag is set
            if args.skip_download and download_type != "subtitles":
                download_type = "subtitles"  # Change to subtitles-only mode
                rprint(
                    "[yellow]--skip-download flag set, only downloading subtitles[/yellow]"
                )

            # Determine authentication method - simplified
            browser = args.browser
            download_credentials = None  # Only use browser cookies now

            download_with_ytdlp(
                url=url,
                output_path=args.output,
                download_type=download_type,
                credentials=download_credentials,
                browser=browser,
            )

            return
        except Exception as e:
            rprint(f"[red]Download failed: {e}[/red]")
            return

    # Initialize client with credentials
    client = BilibiliClient(**credentials)

    try:
        if args.user:
            # Handle user videos
            uid = int(args.identifier)
            rprint(f"[cyan]Starting to fetch videos for user {uid}...[/cyan]")
            videos = await client.get_user_videos(uid)
            display_user_videos(videos)
            if videos:
                rprint(f"[green]Retrieved {len(videos)} videos from user {uid}[/green]")
            else:
                rprint("[yellow]No videos found for this user[/yellow]")
        elif args.text:
            # Handle text content
            config = VideoTextConfig(
                include_subtitles=not args.no_subtitles,
                include_comments=not args.no_comments,
                include_uploader_info=not args.no_uploader,
                comment_limit=args.comment_limit,
                subtitle_markdown=args.subtitle_markdown,
            )
            content = await client.get_video_text_content(args.identifier, config)
            save_content(content.to_markdown(), args.output)
        else:
            # Handle single video
            video = await client.get_video_info(args.identifier)
            display_video_info(video)
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
