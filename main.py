import os
from pathlib import Path
import asyncio
import argparse
import subprocess
import logging
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.markdown import Markdown
from bilibili_client import BilibiliClient, VideoInfo, VideoTextConfig


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


def download_with_ytdlp(
    url: str,
    output_path: str = None,
    download_type: str = "audio",
    credentials=None,
    browser=None,
):
    """Download media from a Bilibili video using yt-dlp.

    Args:
        url: Bilibili video URL
        output_path: Output path (optional)
        download_type: 'audio', 'subtitles', or 'all'
        credentials: Dictionary with 'sessdata', 'bili_jct', and 'buvid3' values for authentication
        browser: Browser to extract cookies from (e.g., 'chrome', 'firefox')
    """
    cmd = ["yt-dlp"]

    # Skip actual video/audio download if only subtitles are requested
    if download_type == "subtitles":
        cmd.append("--skip-download")

    # Add format specification based on download type
    if download_type in ["audio", "all"]:
        cmd.extend(["-f", "ba"])

    # Add subtitles option if requested
    if download_type in ["subtitles", "all"]:
        cmd.extend(["--write-subs", "--write-auto-subs", "--sub-langs", "all"])

    # Handle authentication
    if browser:
        # Use browser cookies directly (preferred method)
        cmd.extend(["--cookies-from-browser", browser])
        rprint(f"[cyan]Using cookies from {browser} browser for authentication[/cyan]")
    elif credentials:
        # Create a temporary cookie file if credentials are provided
        cookies_file = Path("temp_cookies.txt")

        # Format cookies in Netscape/Mozilla format
        cookie_content = [
            "# Netscape HTTP Cookie File",
            "# https://curl.se/docs/http-cookies.html",
            "# This file was generated by yt-dlp. Edit at your own risk.",
            "",
        ]

        # Add cookies in the required format
        domain = ".bilibili.com"
        for name, value in credentials.items():
            if name == "sessdata" and value:
                cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tSESSDATA\t{value}")
            elif name == "bili_jct" and value:
                cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tbili_jct\t{value}")
            elif name == "buvid3" and value:
                cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tbuvid3\t{value}")

        # Write cookies to file
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write("\n".join(cookie_content))

        # Add cookies file to command
        cmd.extend(["--cookies", str(cookies_file)])
        rprint(f"[cyan]Using cookies for authentication with yt-dlp[/cyan]")

    # Add URL and output template if specified
    cmd.append(url)
    if output_path:
        cmd.extend(["-o", output_path])

    # Add verbose output for debugging
    cmd.append("-v")

    # Run the command
    try:
        rprint(f"[cyan]Running yt-dlp command: {' '.join(cmd)}[/cyan]")
        subprocess.run(cmd, check=True)
        rprint(f"[green]{download_type.capitalize()} download complete.[/green]")
    except subprocess.CalledProcessError as e:
        rprint(f"[red]yt-dlp download failed with error code {e.returncode}[/red]")
        raise
    finally:
        # Clean up temporary cookies file
        if credentials and not browser:
            cookies_file = Path("temp_cookies.txt")
            if cookies_file.exists():
                cookies_file.unlink()


def ensure_bilibili_url(identifier: str) -> str:
    """If identifier is a BVID, assemble the full Bilibili video URL."""
    if (identifier.startswith("BV") or identifier.startswith("bv")) and len(
        identifier
    ) >= 12:
        return f"https://www.bilibili.com/video/{identifier}"
    return identifier


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
        "--sessdata",
        help="SESSDATA cookie value (overrides .env)",
        default=None,
    )
    parser.add_argument(
        "--bili-jct",
        help="bili_jct cookie value (overrides .env)",
        default=None,
    )
    parser.add_argument(
        "--buvid3",
        help="buvid3 cookie value (overrides .env)",
        default=None,
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
        "--use-cookies",
        action="store_true",
        help="Use Bilibili cookies with yt-dlp for authenticated downloads",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox"],
        help="Browser to extract cookies from (alternative to --use-cookies)",
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

    # Override with command line arguments if provided
    if args.sessdata:
        credentials["sessdata"] = args.sessdata
    if args.bili_jct:
        credentials["bili_jct"] = args.bili_jct
    if args.buvid3:
        credentials["buvid3"] = args.buvid3

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

            # Determine authentication method
            browser = args.browser
            download_credentials = credentials if args.use_cookies else None

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
