import subprocess
import os
import logging
import re
import tempfile
import json
import time
from pathlib import Path
from rich import print as rprint
from extract_cookies import get_bilibili_cookies


# Global cache for cookie files to avoid extracting them multiple times
_cookie_file_cache = {}
logger = logging.getLogger("bilibili_client")


def get_credentials_path():
    """Returns path for credentials storage"""
    home = Path.home()
    config_dir = home / ".config" / "bilibili_analyzer"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "credentials.json"


def load_cached_credentials(browser=None):
    """Load cached credentials

    Args:
        browser: Specific browser to load credentials for

    Returns:
        Browser credentials dict if browser specified, all credentials if not,
        or None/empty dict if no credentials found
    """
    cred_path = get_credentials_path()
    if not cred_path.exists():
        return None if browser else {}

    try:
        creds = json.loads(cred_path.read_text())
        if browser:
            # Check if credentials exist for this browser and not expired
            browser_creds = creds.get(browser)
            if not browser_creds:
                return None

            # Check if expired (default 30 days)
            timestamp = browser_creds.get("timestamp", 0)
            if (time.time() - timestamp) > 30 * 24 * 3600:
                return None

            return browser_creds.get("cookies")
        return creds
    except:
        return None if browser else {}


def save_credentials(browser, cookies):
    """Save credentials to file

    Args:
        browser: Browser name ('chrome' or 'firefox')
        cookies: Cookie dictionary to save

    Returns:
        bool: Whether saving was successful
    """
    creds = load_cached_credentials() or {}
    creds[browser] = {"cookies": cookies, "timestamp": time.time()}

    cred_path = get_credentials_path()
    try:
        cred_path.write_text(json.dumps(creds, indent=2))
        os.chmod(cred_path, 0o600)  # Make readable/writable only by user
        return True
    except Exception as e:
        logger.warning(f"Failed to save credentials: {e}")
        return False


def ensure_bilibili_url(identifier: str) -> str:
    """If identifier is a BVID, assemble the full Bilibili video URL."""
    if (identifier.startswith("BV") or identifier.startswith("bv")) and len(
        identifier
    ) >= 12:
        return f"https://www.bilibili.com/video/{identifier}"
    return identifier


def get_browser_cookies(browser: str, force_refresh=False) -> str:
    """Get cookie file for the specified browser, creating it if necessary.

    Args:
        browser: Browser name ('chrome' or 'firefox')
        force_refresh: Force refresh credentials even if cached

    Returns:
        Path to the cookie file
    """
    global _cookie_file_cache

    # If force refresh is requested, clear any existing cache entries
    if force_refresh and browser in _cookie_file_cache:
        logger.debug(f"Force refresh requested for {browser}, clearing cache")
        _cookie_file_cache.pop(browser, None)

    # If cookie file already exists in in-memory cache, return it
    if (
        browser in _cookie_file_cache
        and os.path.exists(_cookie_file_cache[browser])
        and not force_refresh
    ):
        return _cookie_file_cache[browser]

    # Check disk cache if not forcing refresh
    if not force_refresh:
        cookies = load_cached_credentials(browser)
        if cookies:
            # Create temporary cookie file
            cookie_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=".cookies", mode="w"
            )

            # Format cookies in Netscape format
            cookie_lines = [
                "# Netscape HTTP Cookie File",
                "# https://curl.se/docs/http-cookies.html",
                "# This file was generated from cached credentials.",
                "",
            ]

            # Add cookies in the required format
            domain = ".bilibili.com"
            for name, value in cookies.items():
                if value:
                    if name == "SESSDATA":
                        cookie_lines.append(
                            f"{domain}\tTRUE\t/\tTRUE\t0\tSESSDATA\t{value}"
                        )
                    elif name == "bili_jct":
                        cookie_lines.append(
                            f"{domain}\tTRUE\t/\tTRUE\t0\tbili_jct\t{value}"
                        )
                    elif name == "buvid3":
                        cookie_lines.append(
                            f"{domain}\tTRUE\t/\tTRUE\t0\tbuvid3\t{value}"
                        )

            cookie_file.write("\n".join(cookie_lines))
            cookie_file.close()

            _cookie_file_cache[browser] = cookie_file.name
            rprint(f"[green]Using cached Bilibili credentials from {browser}.[/green]")
            return cookie_file.name

    # Extract new cookies from browser - this is always executed when force_refresh is true
    rprint(
        f"[cyan]Extracting Bilibili cookies from {browser} {'(forced refresh)' if force_refresh else ''}...[/cyan]"
    )
    cookies = get_bilibili_cookies(browser)

    if not cookies:
        rprint(
            "[red]No Bilibili cookies found. Please ensure you are logged into Bilibili in your browser.[/red]"
        )
        return None

    # Create temporary cookie file
    cookie_file = tempfile.NamedTemporaryFile(delete=False, suffix=".cookies", mode="w")

    # Format cookies in Netscape format
    cookie_content = [
        "# Netscape HTTP Cookie File",
        "# https://curl.se/docs/http-cookies.html",
        "# This file was generated by Bilibili analyzer. Edit at your own risk.",
        "",
    ]

    # Add cookies in the required format
    domain = ".bilibili.com"
    for name, value in cookies.items():
        if name == "SESSDATA" and value:
            cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tSESSDATA\t{value}")
        elif name == "bili_jct" and value:
            cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tbili_jct\t{value}")
        elif name == "buvid3" and value:
            cookie_content.append(f"{domain}\tTRUE\t/\tTRUE\t0\tbuvid3\t{value}")

    # Write cookies to file
    cookie_file.write("\n".join(cookie_content))
    cookie_file.close()

    # Cache the cookie file path for future use
    _cookie_file_cache[browser] = cookie_file.name

    # Save credentials to persistent cache
    save_credentials(browser, cookies)

    rprint(f"[green]Bilibili cookies extracted and saved for reuse.[/green]")
    return cookie_file.name


def check_credentials(args):
    """Check for valid credentials and prompt if needed

    Args:
        args: Command line arguments
    """
    # Handle credential clearing if requested
    if hasattr(args, "clear_credentials") and args.clear_credentials:
        cred_path = get_credentials_path()
        if cred_path.exists():
            cred_path.unlink()
            rprint("[green]Credentials successfully cleared.[/green]")
        else:
            rprint("[yellow]No stored credentials found.[/yellow]")
        return

    # Check if operation needs authentication
    needs_auth = (
        hasattr(args, "text")
        and args.text
        or hasattr(args, "retry_llm")
        and args.retry_llm
        or hasattr(args, "export_user_subtitles")
        and args.export_user_subtitles
    )

    force_refresh = hasattr(args, "force_login") and args.force_login

    if needs_auth and not args.browser:
        # Check if we have cached credentials for any browser (only if not forcing refresh)
        if not force_refresh:
            for browser in ["chrome", "firefox"]:
                if load_cached_credentials(browser):
                    rprint(
                        f"[green]Found valid cached credentials from {browser}.[/green]"
                    )
                    args.browser = browser
                    return

        # Prompt user to select browser for authentication
        rprint(
            "[yellow]Browser authentication is recommended for full functionality.[/yellow]"
        )
        response = (
            input("Enter 'chrome', 'firefox', or press Enter to skip: ").strip().lower()
        )

        if response in ["chrome", "firefox"]:
            args.browser = response

    # If force refresh is enabled and browser is specified, ensure we actually refresh
    if force_refresh and args.browser:
        rprint(
            f"[cyan]Force login requested. Will extract fresh credentials from {args.browser}.[/cyan]"
        )
        # Call get_browser_cookies with force_refresh=True to ensure new extraction
        get_browser_cookies(args.browser, force_refresh=True)


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

    # Handle authentication - use cached cookie file for browser
    cookie_file = None
    if browser:
        # Extract cookies first, before showing any download messages
        # Get cookie file from cache, extracting it only once if needed
        cookie_file = get_browser_cookies(browser)
        if cookie_file:
            cmd.extend(["--cookies", cookie_file])
            logger.debug(
                f"Using cached cookies from {browser} browser for authentication"
            )
        else:
            rprint(
                f"[yellow]Warning: No cookies found for {browser}. Download may fail if authentication is required.[/yellow]"
            )
    elif credentials:
        # Legacy warning
        rprint(
            "[yellow]Warning: The credentials parameter is deprecated, please use --browser instead[/yellow]"
        )

    # Add URL and output template if specified
    cmd.append(url)
    if output_path:
        cmd.extend(["-o", output_path])

    # Add verbose output only in debug mode
    if logger.isEnabledFor(logging.DEBUG):
        cmd.append("-v")
        # Show command in debug mode only
        logger.debug(f"Running yt-dlp command: {' '.join(cmd)}")
    else:
        # Add quiet flag to reduce output when not in debug mode
        cmd.append("-q")

    # Run the command - only show this message after we've handled cookies
    try:
        rprint(f"[cyan]Running yt-dlp command to download {download_type}...[/cyan]")
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


def remove_timestamps(subtitle_text: str) -> str:
    """Remove timestamps from subtitles.

    Works with various subtitle formats:
    - Whisper output: [00:00.000 --> 00:02.880] Text
    - SRT format: 1\n00:00:00,000 --> 00:00:02,880\nText
    - VTT format: 00:00.000 --> 00:00:02.880\nText

    Args:
        subtitle_text: The subtitle text with timestamps

    Returns:
        Cleaned subtitle text with timestamps removed
    """
    # Different patterns to match various subtitle formats
    patterns = [
        # Whisper style [00:00.000 --> 00:02.880]
        r"\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*",
        # SRT style timestamps (with line numbers)
        r"^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*\n",
        # VTT style timestamps
        r"^\d{2}:\d{2}[:.]\d{3}\s*-->\s*\d{2}:\d{2}[:.]\d{3}\s*\n",
        # Bilibili API style timestamps with from/to
        r"\[\d+\.\d+\]\s*",
    ]

    # Apply each pattern
    result = subtitle_text
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.MULTILINE)

    # Clean up multiple newlines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def format_subtitle_header(video_info, include_description=True) -> str:
    """Format a header with video information to prepend to subtitles.

    Args:
        video_info: VideoInfo object containing video metadata
        include_description: Whether to include video description

    Returns:
        Formatted header string
    """
    header = [
        f"# {video_info.title}",
        f"BVID: {video_info.bvid}",
        f"Uploader: {video_info.owner_name} (UID: {video_info.owner_mid})",
        f"Upload Time: {video_info.upload_time}",
        f"Views: {video_info.view_count:,}",
    ]

    if include_description and video_info.description:
        # Add a separator line
        header.append("\nDescription:")
        # Indent description lines
        description_lines = video_info.description.split("\n")
        for line in description_lines:
            header.append(f"> {line}")

    return "\n".join(header)
