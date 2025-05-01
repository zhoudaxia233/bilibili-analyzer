import asyncio
import argparse
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from bilibili_client import BilibiliClient, VideoInfo


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
    table = Table(title="User Videos")

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


async def main():
    parser = argparse.ArgumentParser(description="Bilibili Video Information Fetcher")
    parser.add_argument("identifier", help="Bilibili video URL, BVID, or user UID")
    parser.add_argument(
        "--user",
        action="store_true",
        help="Fetch all videos from a user (requires UID)",
    )

    args = parser.parse_args()
    client = BilibiliClient()

    try:
        if args.user:
            # Handle user videos
            uid = int(args.identifier)
            videos = await client.get_user_videos(uid)
            display_user_videos(videos)
        else:
            # Handle single video
            video = await client.get_video_info(args.identifier)
            display_video_info(video)
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
