import subprocess
from pathlib import Path
from rich import print as rprint


def ensure_bilibili_url(identifier: str) -> str:
    """If identifier is a BVID, assemble the full Bilibili video URL."""
    if (identifier.startswith("BV") or identifier.startswith("bv")) and len(
        identifier
    ) >= 12:
        return f"https://www.bilibili.com/video/{identifier}"
    return identifier


def download_with_ytdlp(
    url: str,
    output_path: str = None,
    download_type: str = "audio",
    credentials=None,  # Keeping parameter for backward compatibility
    browser=None,
):
    """Download media from a Bilibili video using yt-dlp.

    Args:
        url: Bilibili video URL
        output_path: Output path (optional)
        download_type: 'audio', 'subtitles', or 'all'
        credentials: Deprecated, use browser parameter instead
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

    # Handle authentication - use browser cookies when available
    if browser:
        # Use browser cookies directly (preferred method)
        cmd.extend(["--cookies-from-browser", browser])
        rprint(f"[cyan]Using cookies from {browser} browser for authentication[/cyan]")
    elif credentials:
        # Legacy warning
        rprint(
            "[yellow]Warning: The credentials parameter is deprecated, please use --browser instead[/yellow]"
        )

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

        # Provide more specific success message based on download type
        if download_type == "subtitles":
            rprint(f"[green]Subtitle download complete.[/green]")
        elif download_type == "audio":
            rprint(f"[green]Audio download complete.[/green]")
        else:
            rprint(f"[green]All requested content download complete.[/green]")
    except subprocess.CalledProcessError as e:
        # Provide more context in error messages to help debugging
        if download_type == "subtitles" and not browser:
            rprint(
                f"[red]yt-dlp subtitle download failed. You might need authentication with --browser.[/red]"
            )
        elif download_type == "audio" and not browser:
            rprint(
                f"[red]yt-dlp audio download failed. You might need authentication with --browser.[/red]"
            )
        else:
            rprint(f"[red]yt-dlp download failed with error code {e.returncode}[/red]")
        raise
