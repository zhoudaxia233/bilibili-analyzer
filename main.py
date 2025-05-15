import os
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.markdown import Markdown

from bilibili_client import BilibiliClient, VideoInfo, VideoTextConfig
from utilities import (
    get_browser_cookies,
    check_credentials,
)

# Setup logger
logger = logging.getLogger(__name__)


def load_credentials():
    """Load credentials from .env file and environment variables"""
    # Try to load from .env file in the current directory
    env_path = Path(".") / ".env"
    load_dotenv(env_path, override=True)

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
        help="Explicitly fetch videos from a user (overrides auto-detection)",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Get video text content including subtitles in markdown format",
    )
    parser.add_argument(
        "--content",
        help="Comma-separated list of content to include (subtitles,comments,uploader)",
        default="subtitles,comments,uploader",
    )
    parser.add_argument(
        "--format",
        help="Format for subtitles (plain or markdown)",
        choices=["plain", "markdown"],
        default="plain",
    )
    parser.add_argument(
        "--comment-limit",
        type=int,
        default=10,
        help="Number of top comments to include (default: 10)",
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
        "--retry-llm",
        action="store_true",
        help="Retry LLM post-processing for an existing whisper transcript",
    )
    parser.add_argument(
        "--export-user-subtitles",
        action="store_true",
        help="Export all subtitles from a user's videos to a single text file",
    )
    parser.add_argument(
        "--subtitle-limit",
        type=int,
        help="Limit the number of videos to process when exporting subtitles",
        default=None,
    )
    parser.add_argument(
        "--no-description",
        action="store_true",
        help="Don't include video descriptions in exported subtitles",
    )
    # Add credential management options
    parser.add_argument(
        "--force-login",
        action="store_true",
        help="Force refresh of Bilibili credentials even if cached",
    )
    parser.add_argument(
        "--clear-credentials",
        action="store_true",
        help="Clear all stored Bilibili credentials",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Configure bilibili_client logger separately to control its verbosity
    bilibili_logger = logging.getLogger("bilibili_client")
    if args.debug:
        bilibili_logger.setLevel(logging.DEBUG)
    else:
        bilibili_logger.setLevel(logging.INFO)

    # Suppress verbose logs from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    # Check for credentials and prompt if needed
    check_credentials(args)

    # Load credentials from .env
    credentials = load_credentials()

    # Initialize client with credentials
    client = BilibiliClient(**credentials)

    try:
        # Auto-detect if identifier is a UID
        is_uid = False
        if (
            not args.text and not args.retry_llm and not args.export_user_subtitles
        ):  # Don't auto-detect for specific modes
            # Check if identifier is numeric (likely a UID)
            if args.identifier.isdigit():
                # UID is typically a number less than 10 digits
                if len(args.identifier) <= 10:
                    is_uid = True

        # Use explicit --user flag to override auto-detection if specified
        if args.user:
            is_uid = True

        # Handle export-user-subtitles mode - this requires a UID
        if args.export_user_subtitles:
            # Verify the identifier is a UID (must be a number)
            if not args.identifier.isdigit():
                rprint(
                    "[red]Error: User UID must be a numeric value for exporting subtitles[/red]"
                )
                return

            uid = int(args.identifier)

            # Ask for confirmation if no limit is set to avoid accidental processing of many videos
            subtitle_limit = args.subtitle_limit
            if subtitle_limit is None:
                console = Console()

                # Fetch user info to display
                try:
                    console.print(f"[cyan]Fetching user information...[/cyan]")
                    user_info = await client._get_user_profile(uid)

                    # Format and display user info
                    console.print(f"[cyan bold]User Information:[/cyan bold]")
                    console.print(
                        f"[cyan]Username: [white]{user_info.get('name', 'Unknown')}[/white][/cyan]"
                    )
                    console.print(
                        f"[cyan]Bio: [white]{user_info.get('sign', 'No bio')}[/white][/cyan]"
                    )
                    console.print(
                        f"[cyan]Followers: [white]{user_info.get('follower_count', 0):,}[/white][/cyan]"
                    )
                    console.print(
                        f"[cyan]Total videos: [white]{user_info.get('video_count', len(videos)):,}[/white][/cyan]"
                    )
                except Exception as e:
                    logger.debug(f"Error fetching user details: {str(e)}")
                    console.print(
                        "[yellow]Could not fetch detailed user information[/yellow]"
                    )

                console.print(
                    "[yellow]Warning: You're about to export subtitles from all videos of this user.[/yellow]"
                )
                response = input(
                    "Enter a number to limit videos, or press Enter to process all: "
                )
                if response.strip().isdigit():
                    subtitle_limit = int(response.strip())
                    console.print(f"[cyan]Limiting to {subtitle_limit} videos[/cyan]")

                # Handle special case: user entered 0 videos
                if subtitle_limit == 0:
                    console.print(
                        "[yellow]You specified 0 videos to process. Exiting without processing any videos.[/yellow]"
                    )
                    return

            # Create folder with user UID
            user_folder = Path(f"user_{uid}")
            user_folder.mkdir(exist_ok=True)

            # Define output file name inside user folder
            output_file = args.output
            if not output_file:
                output_file = user_folder / "all_subtitles.txt"
            elif not Path(output_file).is_absolute():
                # If relative path provided, place inside user folder
                output_file = user_folder / output_file

            # Execute the subtitle export
            console = Console()
            console.print(f"[cyan]Starting subtitle export for user {uid}...[/cyan]")
            console.print(f"[cyan]Output will be saved to {output_file}[/cyan]")

            # Handle browser authentication first if provided
            browser = args.browser
            if browser:
                # Initialize credentials early to ensure cookie extraction happens before any API calls
                console.print(
                    f"[cyan]Extracting cookies from {browser} browser...[/cyan]"
                )
                try:
                    # Use browser but don't actually download anything yet, just to extract cookies
                    cookie_file = get_browser_cookies(browser)
                    if cookie_file:
                        console.print(
                            f"[green]Successfully extracted cookies from {browser}[/green]"
                        )
                    else:
                        console.print(
                            f"[yellow]No cookies found in {browser}. Make sure you're logged into Bilibili.[/yellow]"
                        )
                except Exception as e:
                    logger.debug(f"Error extracting cookies: {str(e)}")
                    console.print(
                        f"[yellow]Warning: Could not extract cookies from {browser}: {str(e)}[/yellow]"
                    )
            # If browser authentication is required but not provided, prompt user
            elif not browser:
                console.print(
                    "[yellow]Do you want to use browser authentication? (Recommended for better results)[/yellow]"
                )
                console.print(
                    "[yellow]This will help access more videos and obtain better quality subtitles[/yellow]"
                )
                auth_response = (
                    input("Enter 'chrome', 'firefox', or press Enter to skip: ")
                    .strip()
                    .lower()
                )

                if auth_response in ["chrome", "firefox"]:
                    browser = auth_response
                    console.print(f"[cyan]Using {browser} for authentication[/cyan]")

                    # Initialize browser cookies immediately
                    try:
                        cookie_file = get_browser_cookies(browser)
                        if cookie_file:
                            console.print(
                                f"[green]Successfully extracted cookies from {browser}[/green]"
                            )
                        else:
                            console.print(
                                f"[yellow]No cookies found in {browser}. Make sure you're logged into Bilibili.[/yellow]"
                            )
                    except Exception as e:
                        logger.debug(f"Error extracting cookies: {str(e)}")
                        console.print(
                            f"[yellow]Warning: Could not extract cookies from {browser}: {str(e)}[/yellow]"
                        )

            # Clear any previous status messages and show a fresh start message
            console.print("")  # Add an empty line for visual separation
            console.print(
                f"[bold cyan]Starting subtitle extraction process with all inputs confirmed...[/bold cyan]"
            )
            console.print("")  # Add an empty line for visual separation

            # Get user info for statistics with the browser authentication already set up
            try:
                user_info = await client._get_user_profile(
                    uid, credential_browser=browser
                )
            except Exception as e:
                logger.debug(f"Error getting user profile in main: {str(e)}")
                user_info = {"uid": uid, "name": f"UID:{uid}"}

            # Get all user subtitles
            include_description = not args.no_description
            combined_text, stats = await client.get_all_user_subtitles(
                uid,
                browser=browser,  # Use the possibly user-provided browser choice
                limit=subtitle_limit,
                include_description=include_description,
            )

            # Save to file
            if combined_text:
                # Create directory if it doesn't exist
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                # Add user info header to the combined text
                user_header = []
                user_header.append(
                    f"# B站用户 {user_info.get('name', f'UID:{uid}')} 的视频字幕集合"
                )
                user_header.append(f"UID: {uid}")
                if user_info.get("sign"):
                    user_header.append(f"个人简介: {user_info.get('sign', '')}")
                user_header.append(f"粉丝数: {user_info.get('follower_count', 0):,}")
                if "video_count" in user_info:
                    user_header.append(f"视频总数: {user_info.get('video_count', 0):,}")
                if "level" in user_info:
                    user_header.append(f"等级: {user_info.get('level', 0)}")
                user_header.append(
                    f"字幕提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                user_header.append(f"处理的视频数: {stats['processed_videos']}")
                user_header.append(
                    f"成功获取字幕的视频数: {stats['videos_with_subtitles']}"
                )
                user_header.append("\n" + "=" * 80 + "\n")

                # Write header followed by combined text
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(user_header) + "\n\n" + combined_text)

                # Save statistics to file as well
                stats_file = user_folder / "stats.txt"
                with open(stats_file, "w", encoding="utf-8") as f:
                    f.write(f"# 字幕提取统计 - 用户ID: {uid}\n")
                    # Add user info if available
                    if user_info:
                        f.write(f"用户名: {user_info.get('name', 'Unknown')}\n")
                        if user_info.get("sign"):
                            f.write(f"个人简介: {user_info.get('sign', '')}\n")
                        f.write(f"粉丝数: {user_info.get('follower_count', 0):,}\n")
                        if "video_count" in user_info:
                            f.write(f"视频总数: {user_info.get('video_count', 0):,}\n")
                        if "level" in user_info:
                            f.write(f"等级: {user_info.get('level', 0)}\n")
                        f.write("\n")

                    f.write(
                        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )
                    f.write(f"总视频数: {stats['total_videos']}\n")
                    f.write(f"处理视频数: {stats['processed_videos']}\n")
                    f.write(f"有字幕的视频数: {stats['videos_with_subtitles']}\n")
                    f.write(
                        f"无字幕的视频数: {stats['processed_videos'] - stats['videos_with_subtitles']}\n\n"
                    )
                    f.write(f"字幕来源:\n")
                    f.write(f"  - Bilibili API: {stats['subtitle_sources']['api']}\n")
                    f.write(f"  - yt-dlp: {stats['subtitle_sources']['yt-dlp']}\n")
                    f.write(f"  - Whisper: {stats['subtitle_sources']['whisper']}\n")
                    f.write(f"  - 失败: {stats['subtitle_sources']['failed']}\n\n")
                    f.write(f"估计的token数: {int(stats['total_tokens']):,}\n")

                # Report success
                console.print(
                    f"[green]Successfully saved {stats['videos_with_subtitles']} video subtitles to {output_file}[/green]"
                )
                console.print(f"[green]Statistics saved to {stats_file}[/green]")

                # Show summary stats
                console.print("[cyan]--- Summary ---[/cyan]")
                console.print(f"Total videos processed: {stats['processed_videos']}")
                console.print(
                    f"Videos with subtitles: {stats['videos_with_subtitles']}"
                )
                console.print(
                    f"Videos without subtitles: {stats['processed_videos'] - stats['videos_with_subtitles']}"
                )
                console.print(f"Subtitle sources:")
                console.print(f"  - Bilibili API: {stats['subtitle_sources']['api']}")
                console.print(f"  - yt-dlp: {stats['subtitle_sources']['yt-dlp']}")
                console.print(f"  - Whisper: {stats['subtitle_sources']['whisper']}")
                console.print(f"  - Failed: {stats['subtitle_sources']['failed']}")
                console.print(f"Estimated tokens: {int(stats['total_tokens']):,}")
            else:
                console.print(
                    "[yellow]No subtitles were found or all processing failed.[/yellow]"
                )

            return

        elif is_uid:
            # Handle user videos
            uid = int(args.identifier)
            rprint(f"[cyan]Starting to fetch videos for user {uid}...[/cyan]")
            videos = await client.get_user_videos(uid)
            display_user_videos(videos)
            if videos:
                rprint(f"[green]Retrieved {len(videos)} videos from user {uid}[/green]")
            else:
                rprint("[yellow]No videos found for this user[/yellow]")
        elif args.retry_llm:
            # Check if identifier is provided
            if not args.identifier:
                rprint(
                    "[red]Error: Video identifier is required for --retry-llm option[/red]"
                )
                return

            try:
                corrected_transcript = await client.retry_llm_processing(
                    args.identifier
                )

                # If output file is specified, save to file; otherwise print to console
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(corrected_transcript)
                    rprint(
                        f"[green]Corrected transcript saved to {args.output}[/green]"
                    )
                else:
                    rprint("[bold]Corrected Transcript:[/bold]")
                    console = Console()
                    console.print(Markdown(corrected_transcript))

            except Exception as e:
                rprint(f"[red]Error during LLM post-processing: {str(e)}[/red]")
            return
        elif args.text:
            # Parse content parameter
            content_options = args.content.lower().split(",") if args.content else []

            # Create config from content options
            config = VideoTextConfig(
                include_subtitles="subtitles" in content_options,
                include_comments="comments" in content_options,
                include_uploader_info="uploader" in content_options,
                comment_limit=args.comment_limit,
                subtitle_markdown=args.format == "markdown",
            )

            # Check if browser is specified for authentication
            if "subtitles" in content_options and not args.browser:
                rprint(
                    "[yellow]Note: Some videos require authentication to access. "
                    "If subtitle extraction fails, try adding --browser chrome or --browser firefox[/yellow]"
                )

            # Try to get video text content with subtitles using all available methods
            try:
                rprint(
                    "[cyan]Getting video text content (using unified subtitle extraction)...[/cyan]"
                )

                # If browser is specified, mention that cookies will be extracted once
                if args.browser:
                    rprint(
                        f"[cyan]Note: Browser cookies will be extracted once and reused for all operations[/cyan]"
                    )

                # Get video text content with unified subtitle extraction
                content = await client.get_video_text_content(
                    args.identifier, config, browser=args.browser
                )

                # Save or display the content
                save_content(content.to_markdown(), args.output)

                if args.output:
                    rprint(
                        f"[green]Successfully saved content to {args.output}[/green]"
                    )

            except Exception as e:
                error_msg = str(e).lower()
                if "authentication" in error_msg and not args.browser:
                    rprint(
                        "[red]Error: This video requires authentication to access.[/red]"
                    )
                    rprint("[yellow]Please retry with browser authentication:[/yellow]")
                    rprint(
                        f"[yellow]  python main.py {args.identifier} --text --browser chrome[/yellow]"
                    )
                else:
                    rprint(f"[red]Error:[/red] {str(e)}")
        else:
            # Handle single video
            video = await client.get_video_info(args.identifier)
            display_video_info(video)
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
