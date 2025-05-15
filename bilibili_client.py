from typing import List, Optional
import os
import math
import logging
import subprocess
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import asyncio

import aiohttp
import requests
from bilibili_api import video, user, Credential
from pydantic import BaseModel, Field
import openai
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from utilities import (
    ensure_bilibili_url,
    download_with_ytdlp,
    remove_timestamps,
    format_subtitle_header,
    get_browser_cookies,
)

logger = logging.getLogger("bilibili_client")
console = Console()


class VideoInfo(BaseModel):
    """Model for Bilibili video information"""

    bvid: str = Field(..., description="Video ID")
    title: str = Field(..., description="Video title")
    description: str = Field(..., description="Video description")
    duration: int = Field(..., description="Video duration in seconds")
    view_count: int = Field(..., description="View count")
    like_count: int = Field(..., description="Like count")
    coin_count: int = Field(..., description="Coin count")
    favorite_count: int = Field(..., description="Favorite count")
    share_count: int = Field(..., description="Share count")
    upload_time: str = Field(..., description="Upload time")
    owner_name: str = Field(..., description="Uploader's name")
    owner_mid: int = Field(..., description="Uploader's ID")
    comment_count: int = Field(..., description="Comment count")


class VideoTextConfig(BaseModel):
    """Configuration for video text content extraction"""

    comment_limit: int = Field(
        default=10, description="Number of top comments to include"
    )
    include_subtitles: bool = Field(
        default=True, description="Whether to include video subtitles"
    )
    include_comments: bool = Field(
        default=True, description="Whether to include video comments"
    )
    include_uploader_info: bool = Field(
        default=True, description="Whether to include detailed uploader information"
    )
    include_meta_info: bool = Field(
        default=True,
        description="Whether to include meta info (title, views, coins, etc.) in the header",
    )


class VideoTextContent(BaseModel):
    """Model for video text content in markdown format"""

    basic_info: str = Field(..., description="Basic video information in markdown")
    uploader_info: Optional[str] = Field(
        None, description="Uploader information in markdown"
    )
    tags_and_categories: Optional[str] = Field(
        None, description="Tags and categories in markdown"
    )
    subtitles: Optional[str] = Field(None, description="Video subtitles in markdown")
    comments: Optional[str] = Field(None, description="Top comments in markdown")

    def to_markdown(self) -> str:
        """Convert all content to a single markdown string"""
        sections = [self.basic_info]

        if self.uploader_info:
            sections.append(self.uploader_info)
        if self.tags_and_categories:
            sections.append(self.tags_and_categories)
        if self.subtitles:
            sections.append(self.subtitles)
        if self.comments:
            sections.append(self.comments)

        return "\n\n".join(sections)


class SimpleLLM:
    """
    Unified LLM client supporting OpenAI-compatible APIs and local endpoints.
    Reads config from environment variables:
      - LLM_MODEL: '<provider>:<model_name>' (e.g., 'openai:gpt-4.1-nano', 'deepseek:deepseek-chat', 'ollama:gemma3:4b')
      - LLM_API_KEY: API key for OpenAI/DeepSeek (ignored for local)
      - LLM_BASE_URL: Base URL for API (e.g., https://api.deepseek.com or http://localhost:11434)
    """

    def __init__(self):
        # Add debugging for environment variables
        logger.debug("SimpleLLM init - Current environment variables:")
        logger.debug(f"  Raw LLM_MODEL env: {repr(os.getenv('LLM_MODEL'))}")
        logger.debug(f"  Raw LLM_BASE_URL env: {repr(os.getenv('LLM_BASE_URL'))}")
        logger.debug(
            f"  Raw LLM_API_KEY env: {repr(os.getenv('LLM_API_KEY', '[MASKED]'))}"
        )

        model_env = os.getenv("LLM_MODEL", "openai:gpt-4.1-nano")
        logger.debug(f"  Using model_env: {model_env}")

        if ":" in model_env:
            self.provider, self.model = model_env.split(":", 1)
            logger.debug(f"  Split into provider={self.provider}, model={self.model}")
        else:
            self.provider, self.model = "openai", model_env
            logger.debug(
                f"  No ':' found, using default provider={self.provider}, model={self.model}"
            )
        self.api_key = os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL")
        self.client = None
        # Initialize client for OpenAI/DeepSeek
        if self.provider in {"openai", "deepseek"}:
            if self.api_key is None:
                raise ValueError(f"{self.provider.upper()}: LLM_API_KEY is required.")
            if self.base_url:
                self.client = openai.OpenAI(
                    api_key=self.api_key, base_url=self.base_url
                )
            else:
                self.client = openai.OpenAI(api_key=self.api_key)

    def call(self, text):
        system_prompt = (
            "You are an expert in correcting automatic speech recognition (ASR) transcripts. "
            "Only fix obvious recognition errors, such as misspelled named entities, common words, or phrases, based on context and general knowledge. "
            "Do not change the sentence structure, style, or meaning. Do not polish or rewrite the text. "
            "The transcript is mostly in Chinese, with occasional English or other languages. "
            "Your response MUST follow this exact format with these exact section markers:\n"
            "CORRECTED_TRANSCRIPT:\n[The corrected transcript with no introduction or explanation]\n\n"
            "KEY_CORRECTIONS:\n[A bullet-point list of key corrections you made, using the format '* Original: X -> Corrected: Y']"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        match self.provider:
            case "openai" | "deepseek":
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, stream=False
                )
                return response.choices[0].message.content
            case "ollama":
                if not self.base_url:
                    raise ValueError("OLLAMA: LLM_BASE_URL is required.")
                url = self.base_url.rstrip("/") + "/api/chat"
                data = {"model": self.model, "messages": messages}
                try:
                    resp = requests.post(url, json=data, timeout=60)
                    resp.raise_for_status()  # Raise exception for non-200 responses

                    response_json = resp.json()
                    logger.debug(f"Ollama API raw response: {resp.text[:200]}")

                    # Handle various Ollama API response formats
                    if (
                        "message" in response_json
                        and "content" in response_json["message"]
                    ):
                        return response_json["message"]["content"]
                    elif "response" in response_json:
                        return response_json["response"]
                    else:
                        logger.debug(
                            f"Unexpected Ollama API response format: {response_json}"
                        )
                        return resp.text  # Return raw text as fallback
                except requests.RequestException as e:
                    logger.debug(f"Ollama API request error: {e}")
                    raise ValueError(f"Ollama API error: {e}")
                except ValueError as e:
                    logger.debug(f"Ollama API JSON parsing error: {e}")
                    # If JSON parsing fails, return the raw text
                    return resp.text
            case _:
                raise ValueError(f"Unknown LLM provider: {self.provider}")


class BilibiliClient:
    """Client for interacting with Bilibili API"""

    def __init__(
        self,
        sessdata: Optional[str] = None,
        bili_jct: Optional[str] = None,
        buvid3: Optional[str] = None,
    ):
        """Initialize the client with optional credentials

        Args:
            sessdata: SESSDATA cookie value
            bili_jct: bili_jct cookie value
            buvid3: buvid3 cookie value
        """
        self.credential = None
        if sessdata or bili_jct or buvid3:
            self.credential = Credential(
                sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3
            )

    def _extract_bvid(self, identifier: str) -> str:
        """Extract BVID from Bilibili URL or return BVID directly.

        Args:
            identifier: A Bilibili video URL or BVID (e.g. BV1xx411c7mD or https://www.bilibili.com/video/BV1xx411c7mD)
        Returns:
            str: The BVID
        """
        if identifier.startswith("BV") or identifier.startswith("bv"):
            return identifier

        bvid = urlparse(identifier).path.rstrip("/").split("/")[-1]
        if bvid.startswith("BV"):
            return bvid

        raise ValueError("Invalid Bilibili URL or BVID")

    def _parse_duration(self, duration_str: str) -> int:
        """Convert duration string (MM:SS) to seconds"""
        try:
            minutes, seconds = map(int, duration_str.split(":"))
            return minutes * 60 + seconds
        except (ValueError, AttributeError):
            return 0

    def _format_timestamp(self, timestamp: int) -> str:
        """Convert Unix timestamp to readable string"""
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return "Unknown"

    async def get_video_info(self, identifier: str) -> VideoInfo:
        """Get video information by BVID or URL"""
        bvid = self._extract_bvid(identifier)
        v = video.Video(bvid=bvid)
        info = await v.get_info()

        return VideoInfo(
            bvid=info["bvid"],
            title=info["title"],
            description=info["desc"],
            duration=info["duration"],
            view_count=info["stat"]["view"],
            like_count=info["stat"]["like"],
            coin_count=info["stat"]["coin"],
            favorite_count=info["stat"]["favorite"],
            share_count=info["stat"]["share"],
            upload_time=self._format_timestamp(info["pubdate"]),
            owner_name=info["owner"]["name"],
            owner_mid=info["owner"]["mid"],
            comment_count=info["stat"]["reply"],
        )

    async def get_user_videos(
        self, uid: int, page: int = 1, page_size: int = 30
    ) -> List[VideoInfo]:
        """Get all videos from a user

        Args:
            uid: User ID
            page: Starting page number (default: 1)
            page_size: Number of videos per page (default: 30)

        Returns:
            List of VideoInfo objects containing all user videos
        """
        u = user.User(uid)
        all_videos = []

        # First get the first page to determine total count
        console.print("[cyan]Fetching first page to determine total videos...[/cyan]")
        first_page = await u.get_videos(pn=1, ps=page_size)
        total_count = first_page["page"]["count"]
        total_pages = math.ceil(total_count / page_size)

        console.print(
            f"[cyan]Found {total_count} videos across {total_pages} pages[/cyan]"
        )

        # Collect all bvids from all pages
        bvids = [item["bvid"] for item in first_page["list"]["vlist"]]
        if total_pages > 1:
            for page_num in range(2, total_pages + 1):
                videos_page = await u.get_videos(pn=page_num, ps=page_size)
                bvids.extend([item["bvid"] for item in videos_page["list"]["vlist"]])

        # Fetch full info for each bvid (concurrently)
        async def fetch_video_info(bvid):
            v = video.Video(bvid=bvid)
            info = await v.get_info()
            return VideoInfo(
                bvid=info["bvid"],
                title=info["title"],
                description=info["desc"],
                duration=info["duration"],
                view_count=info["stat"]["view"],
                like_count=info["stat"]["like"],
                coin_count=info["stat"]["coin"],
                favorite_count=info["stat"]["favorite"],
                share_count=info["stat"]["share"],
                upload_time=self._format_timestamp(info["pubdate"]),
                owner_name=info["owner"]["name"],
                owner_mid=info["owner"]["mid"],
                comment_count=info["stat"]["reply"],
            )

        # Use asyncio.gather for concurrency
        all_videos = await asyncio.gather(*(fetch_video_info(bvid) for bvid in bvids))
        return all_videos

    async def _format_basic_info(self, info: dict) -> str:
        """Format basic video information as markdown"""
        upload_time = self._format_timestamp(info["pubdate"])
        duration_str = f"{info['duration'] // 60}:{info['duration'] % 60:02d}"
        stats = info["stat"]

        return f"""# {info['title']}

{info['desc']}

## Video Information
- Duration: {duration_str}
- Upload Time: {upload_time}
- Views: {stats['view']:,}
- Likes: {stats['like']:,}
- Coins: {stats['coin']:,}
- Favorites: {stats['favorite']:,}
- Shares: {stats['share']:,}"""

    async def _format_uploader_info(self, info: dict) -> str:
        """Format uploader information as markdown"""
        u = user.User(info["owner"]["mid"])
        user_info = await u.get_user_info()

        # Get follower count using get_relation_info
        relation_info = await u.get_relation_info()
        follower_count = relation_info["follower"]

        return f"""## Uploader Information
- Name: {user_info['name']}
- Level: {user_info['level']}
- Bio: {user_info.get('sign', 'No bio')}
- Followers: {follower_count:,}"""

    async def _format_tags_and_categories(self, v: video.Video) -> str:
        """Format video tags and categories as markdown"""
        tags = await v.get_tags()
        tag_names = [tag["tag_name"] for tag in tags]

        return f"""## Tags and Categories
{', '.join(tag_names)}"""

    async def _format_subtitles(self, v: video.Video, cid: int) -> Optional[str]:
        """Format video subtitles as plain text

        Args:
            v: Video object
            cid: Video CID
        Returns:
            Formatted subtitle text or None if no subtitles found
        """
        try:
            # Get all available subtitle lists
            subtitle_lists = await v.get_subtitle(cid=cid)
            logger.debug(f"Raw subtitle lists: {subtitle_lists}")

            if not subtitle_lists or not isinstance(subtitle_lists, dict):
                logger.debug("No subtitles found or invalid format")
                return None

            subtitles = subtitle_lists.get("subtitles", [])
            if not subtitles:
                logger.debug("No subtitles in the list")
                return None

            all_subtitles = []

            for subtitle in subtitles:
                logger.debug(f"Processing subtitle: {subtitle}")

                # Get subtitle language and url
                lang = subtitle.get("lan_doc", "unknown")
                subtitle_url = subtitle.get("subtitle_url", "")

                if not subtitle_url:
                    logger.debug(f"No subtitle URL for language {lang}")
                    continue

                # Add https: prefix if URL starts with //
                if subtitle_url.startswith("//"):
                    subtitle_url = f"https:{subtitle_url}"

                logger.debug(f"Fetching subtitle from URL: {subtitle_url}")

                # Format subtitle information
                all_subtitles.append(f"\nSubtitles ({lang})\n")

                # Get and process actual subtitle content
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(subtitle_url) as response:
                            if response.status != 200:
                                logger.debug(
                                    f"Failed to fetch subtitle content: HTTP {response.status}"
                                )
                                continue

                            raw_content = await response.json()
                            logger.debug(f"Raw content type: {type(raw_content)}")
                            if raw_content:
                                logger.debug(
                                    f"First subtitle entry: {str(raw_content)[:200]}"
                                )

                    if isinstance(raw_content, dict) and "body" in raw_content:
                        for line in raw_content["body"]:
                            start_time = line.get("from", 0)
                            content = line.get("content", "")
                            all_subtitles.append(f"[{start_time:.2f}] {content}")
                    else:
                        logger.debug(
                            f"Unexpected subtitle data format: {raw_content[:100] if raw_content else None}"
                        )
                except aiohttp.ClientError as e:
                    logger.debug(f"Network error fetching subtitle: {str(e)}")
                    continue
                except Exception as sub_error:
                    logger.debug(f"Error processing subtitle: {str(sub_error)}")
                    continue

            if not all_subtitles:
                logger.debug("No subtitle content processed")
                return None

            return "Video Subtitles\n" + "\n".join(all_subtitles)

        except Exception as e:
            logger.debug(f"Main error in subtitle processing: {str(e)}")
            return None

    async def _format_comments(self, v: video.Video, limit: int) -> Optional[str]:
        """Format video comments as markdown"""
        try:
            comments = await v.get_comments(page_index=1, page_size=limit)
            if not comments["replies"]:
                return None

            comment_text = []
            for comment in comments["replies"]:
                author = comment["member"]["uname"]
                content = comment["content"]["message"]
                likes = comment["like"]
                comment_text.append(f"**{author}** (👍 {likes:,}):\n{content}\n")

            return "## Top Comments\n" + "\n".join(comment_text)
        except Exception:
            return None

    async def get_video_text_content(
        self,
        identifier: str,
        config: Optional[VideoTextConfig] = None,
        browser: Optional[str] = None,
    ) -> VideoTextContent:
        """Get video text content in markdown format

        Args:
            identifier: A Bilibili video URL or BVID
            config: Configuration for text content extraction
            browser: Browser to extract cookies from for authentication (e.g., 'chrome', 'firefox')

        Returns:
            VideoTextContent object containing markdown formatted text
        """
        config = config or VideoTextConfig()
        bvid = self._extract_bvid(identifier)
        url = ensure_bilibili_url(identifier)  # Pre-compute URL for reuse
        base_dir = Path("video_texts") / bvid  # Pre-compute base directory for reuse
        base_dir.mkdir(parents=True, exist_ok=True)

        # Create video instance with credential if available
        v = video.Video(bvid=bvid, credential=self.credential)
        info = await v.get_info()
        logger.debug(f"Video info: bvid={bvid}, cid={info.get('cid')}")

        # Basic info is always included
        basic_info = await self._format_basic_info(info)

        # Optional sections based on config
        uploader_info = (
            await self._format_uploader_info(info)
            if config.include_uploader_info
            else None
        )

        tags_and_categories = await self._format_tags_and_categories(v)

        subtitles = None
        if config.include_subtitles:
            # Step 1: Try to get subtitles via API first
            try:
                logger.debug("Trying to get subtitles via Bilibili API...")
                console.print(
                    "[cyan]Trying to get subtitles via Bilibili API...[/cyan]"
                )
                subtitles = await self._format_subtitles(v, info["cid"])
                if subtitles:
                    logger.debug("Successfully retrieved subtitles via Bilibili API")
                    console.print(
                        "[green]Successfully retrieved subtitles via Bilibili API[/green]"
                    )
            except Exception as e:
                logger.debug(f"Error getting subtitles via API: {str(e)}")
                console.print(
                    f"[yellow]API subtitle extraction failed: {str(e)}[/yellow]"
                )

            # Step 2: If API fails, try to get subtitles via yt-dlp
            if not subtitles:
                # First check for existing subtitle files
                subtitle_files = list(base_dir.glob("*.vtt")) + list(
                    base_dir.glob("*.srt")
                )

                if subtitle_files:
                    logger.debug(f"Found existing subtitle files: {subtitle_files}")
                    console.print(
                        f"[green]Found existing subtitle files: {', '.join(str(f.name) for f in subtitle_files)}[/green]"
                    )

                    # Load the first subtitle file
                    subtitle_content = subtitle_files[0].read_text(encoding="utf-8")

                    # Format subtitle content
                    subtitles = subtitle_content
                else:
                    # No existing subtitle files, try to download with yt-dlp
                    try:
                        logger.debug("Trying to get subtitles via yt-dlp...")
                        console.print(
                            "[cyan]API subtitle extraction failed. Trying yt-dlp...[/cyan]"
                        )

                        # Use a progress indicator for subtitle download
                        with console.status(
                            "[bold cyan]Downloading subtitles with yt-dlp...[/bold cyan]",
                            spinner="dots",
                        ):
                            download_with_ytdlp(
                                url=url,
                                output_path=str(base_dir / bvid),
                                download_type="subtitles",
                                browser=browser,  # Browser cookie will be extracted once and cached
                            )

                        # Check if subtitles were downloaded
                        subtitle_files = list(base_dir.glob("*.vtt")) + list(
                            base_dir.glob("*.srt")
                        )
                        if subtitle_files:
                            logger.debug(
                                f"Downloaded subtitle files with yt-dlp: {subtitle_files}"
                            )
                            console.print(
                                f"[green]Successfully downloaded subtitles with yt-dlp[/green]"
                            )

                            # Load the first subtitle file
                            subtitle_content = subtitle_files[0].read_text(
                                encoding="utf-8"
                            )

                            # Format subtitle content
                            subtitles = subtitle_content
                        else:
                            logger.debug(
                                "No subtitle files found after yt-dlp download"
                            )
                            console.print(
                                "[yellow]No subtitle files found after yt-dlp download[/yellow]"
                            )
                    except Exception as e:
                        logger.debug(f"Error getting subtitles via yt-dlp: {str(e)}")
                        console.print(
                            f"[yellow]yt-dlp subtitle extraction failed: {str(e)}[/yellow]"
                        )

                        # If no browser was provided, exit with authentication message
                        if not browser:
                            error_msg = f"Authentication required to download subtitles for {bvid}."
                            console.print(f"[bold red]{error_msg}[/bold red]")
                            console.print(
                                f"[bold yellow]Please retry with browser authentication:[/bold yellow]"
                            )
                            command = f"python main.py {bvid} --text --browser chrome"

                            # For batch processing, suggest appropriate command
                            if "export_user_subtitles" in str(e):
                                uid = bvid.split("_")[1] if "_" in bvid else "UID"
                                command = f"python main.py {uid} --export-user-subtitles --browser chrome"

                            console.print(f"[bold cyan]{command}[/bold cyan]")
                            raise Exception(error_msg)

            # Step 3: Whisper fallback if both API and yt-dlp fail
            if not subtitles:
                audio_path = base_dir / "temp_audio.m4a"
                transcript_path = base_dir / "subtitles_raw.txt"
                corrected_path = base_dir / "subtitles.txt"

                # If transcripts already exist, use them
                if (
                    transcript_path.exists()
                    and corrected_path.exists()
                    and transcript_path.stat().st_size > 0
                    and corrected_path.stat().st_size > 0
                ):
                    console.print(
                        f"[yellow]Transcript and corrected transcript already exist. Using existing Whisper transcript.[/yellow]"
                    )
                    corrected = corrected_path.read_text(encoding="utf-8")
                    subtitles = "## Whisper Transcript (Corrected)\n" + corrected
                else:
                    try:
                        console.print(
                            "[cyan]Both API and yt-dlp failed to get subtitles. Falling back to Whisper audio transcription...[/cyan]"
                        )
                        logger.info("Falling back to Whisper audio transcription...")

                        # Download audio using same browser cookie (will be cached from previous step)
                        # This will now use the status indicator from the updated download_with_ytdlp function
                        download_with_ytdlp(
                            url=url,
                            output_path=str(audio_path),
                            download_type="audio",
                            browser=browser,  # Browser cookie will be reused from cache
                        )

                        if not audio_path.exists() or audio_path.stat().st_size == 0:
                            raise Exception("Audio download failed or file is empty")

                        logger.info(
                            f"Audio downloaded to {audio_path}. Running Whisper for ASR transcript..."
                        )

                        # Prepare Whisper command
                        cmd = [
                            "whisper",
                            str(audio_path),
                            "--model",
                            "turbo",
                            "--output_format",
                            "txt",
                            "--output_dir",
                            str(base_dir),
                        ]

                        # Run Whisper and show output to user so they can see progress
                        console.print(
                            "[cyan]Starting Whisper transcription (showing actual output):[/cyan]"
                        )

                        # Run Whisper with visible output
                        try:
                            # Use subprocess.run with no redirection to show output
                            result = subprocess.run(cmd, check=True)
                            console.print(
                                "[bold green]Transcription complete![/bold green]"
                            )
                        except subprocess.CalledProcessError as e:
                            logger.debug(
                                f"Whisper failed with return code {e.returncode}"
                            )
                            raise Exception(
                                f"Whisper failed with return code {e.returncode}"
                            )

                        # Move/rename output if needed
                        generated_txt = base_dir / (audio_path.stem + ".txt")
                        if generated_txt != transcript_path:
                            if generated_txt.exists():
                                generated_txt.rename(transcript_path)
                            else:
                                logger.debug(
                                    f"Expected generated file {generated_txt} not found"
                                )
                                raise Exception(
                                    "Whisper did not generate any transcript file"
                                )

                        if (
                            not transcript_path.exists()
                            or transcript_path.stat().st_size == 0
                        ):
                            raise Exception(
                                "Whisper transcript generation failed or file is empty"
                            )

                        logger.info(
                            f"Whisper transcript generated at {transcript_path}. Starting LLM post-processing..."
                        )
                        transcript = transcript_path.read_text(encoding="utf-8")

                        # LLM post-processing (all config from env)
                        llm = SimpleLLM()

                        # Use status for LLM processing
                        with console.status(
                            "[bold cyan]Running LLM post-processing of transcript...[/bold cyan]",
                            spinner="dots",
                        ) as status:
                            try:
                                # Get both corrected transcript and key corrections in one call
                                logger.debug(
                                    f"Preparing to process transcript with {llm.provider}:{llm.model}..."
                                )

                                full_response = llm.call(transcript)

                                # Extract sections using the markers
                                corrected_transcript = ""
                                key_corrections = ""

                                # Split the response into sections
                                if (
                                    "CORRECTED_TRANSCRIPT:" in full_response
                                    and "KEY_CORRECTIONS:" in full_response
                                ):
                                    parts = full_response.split(
                                        "CORRECTED_TRANSCRIPT:", 1
                                    )[1]
                                    if "KEY_CORRECTIONS:" in parts:
                                        corrected_transcript, key_corrections = (
                                            parts.split("KEY_CORRECTIONS:", 1)
                                        )
                                        corrected_transcript = (
                                            corrected_transcript.strip()
                                        )
                                        key_corrections = key_corrections.strip()
                                else:
                                    # Fallback if the LLM didn't follow the format
                                    corrected_transcript = full_response

                                # Save corrected transcript
                                corrected_path.write_text(
                                    corrected_transcript, encoding="utf-8"
                                )

                                # Save key corrections if available
                                if key_corrections:
                                    (base_dir / "subtitles_corrections.txt").write_text(
                                        key_corrections, encoding="utf-8"
                                    )

                                status.update(
                                    "[bold green]LLM post-processing complete.[/bold green]"
                                )
                                logger.info(
                                    "LLM post-processing complete. Corrected transcript ready."
                                )
                                subtitles = (
                                    "## Whisper Transcript (Corrected)\n"
                                    + corrected_transcript
                                )
                            except Exception as e:
                                logger.debug(f"LLM post-processing failed: {e}")
                                corrected_path.write_text(transcript, encoding="utf-8")
                                status.update(
                                    "[bold yellow]LLM post-processing failed. Using raw Whisper transcript.[/bold yellow]"
                                )
                                subtitles = "## Whisper Transcript\n" + transcript

                        # Clean up temp audio
                        if audio_path.exists():
                            audio_path.unlink(missing_ok=True)
                    except Exception as e:
                        logger.debug(f"Whisper transcription failed: {str(e)}")
                        console.print(
                            f"[red]Whisper transcription failed: {str(e)}[/red]"
                        )
                        if not browser:
                            raise Exception(
                                f"All subtitle extraction methods failed. Try using --browser option for authentication. Error: {str(e)}"
                            )
                        else:
                            raise Exception(
                                f"All subtitle extraction methods failed despite authentication. Error: {str(e)}"
                            )

        comments = (
            await self._format_comments(v, config.comment_limit)
            if config.include_comments
            else None
        )

        return VideoTextContent(
            basic_info=basic_info,
            uploader_info=uploader_info,
            tags_and_categories=tags_and_categories,
            subtitles=subtitles,
            comments=comments,
        )

    async def retry_llm_processing(self, identifier: str) -> str:
        """Retry LLM post-processing for an existing Whisper transcript.

        Args:
            identifier: A Bilibili video URL or BVID

        Returns:
            The corrected transcript text

        Raises:
            Exception: If the transcript file does not exist or LLM processing fails
        """
        # Extract BVID from URL if needed
        bvid = self._extract_bvid(identifier)
        logger.debug(f"Retrying LLM processing for BVID: {bvid}")

        # Define file paths
        base_dir = Path("video_texts") / bvid
        transcript_path = base_dir / "subtitles_raw.txt"
        corrected_path = base_dir / "subtitles.txt"

        # Check if transcript file exists
        if not transcript_path.exists():
            logger.debug(f"Transcript file not found at {transcript_path}")
            raise Exception(
                f"Whisper transcript file not found at {transcript_path}. Run with --text first."
            )

        # Read the transcript
        transcript = transcript_path.read_text(encoding="utf-8")
        if not transcript.strip():
            logger.debug(f"Transcript file is empty at {transcript_path}")
            raise Exception(f"Whisper transcript file is empty at {transcript_path}.")

        logger.debug(f"Loaded transcript with {len(transcript)} characters")

        # Create LLM instance
        llm = SimpleLLM()
        logger.debug(f"Initialized LLM with provider={llm.provider}, model={llm.model}")

        # Run LLM post-processing
        console.print(f"[cyan]Retrying LLM post-processing for {bvid}...[/cyan]")
        console.print(f"[cyan]Using {llm.provider}:{llm.model}[/cyan]")

        try:
            with console.status(
                "[bold green]Running LLM post-processing (this may take a while)...[/bold green]",
                spinner="dots",
            ):
                full_response = llm.call(transcript)
                logger.debug(
                    f"Received LLM response with {len(full_response)} characters"
                )
                if len(full_response) > 200:
                    logger.debug(f"Response preview: {full_response[:200]}...")
        except Exception as e:
            logger.debug(f"LLM call failed with error: {str(e)}")
            raise

        # Extract sections using the markers
        corrected_transcript = ""
        key_corrections = ""

        # Split the response into sections
        if (
            "CORRECTED_TRANSCRIPT:" in full_response
            and "KEY_CORRECTIONS:" in full_response
        ):
            logger.debug("Found both section markers in response")
            parts = full_response.split("CORRECTED_TRANSCRIPT:", 1)[1]
            if "KEY_CORRECTIONS:" in parts:
                corrected_transcript, key_corrections = parts.split(
                    "KEY_CORRECTIONS:", 1
                )
                corrected_transcript = corrected_transcript.strip()
                key_corrections = key_corrections.strip()
                logger.debug(
                    f"Extracted {len(corrected_transcript)} chars of corrected transcript and {len(key_corrections)} chars of key corrections"
                )
        else:
            # Fallback if the LLM didn't follow the format
            logger.debug(
                "Response format didn't match expected markers, using full response as transcript"
            )
            corrected_transcript = full_response

        # Save corrected transcript
        try:
            corrected_path.write_text(corrected_transcript, encoding="utf-8")
            logger.debug(f"Saved corrected transcript to {corrected_path}")
        except Exception as e:
            logger.debug(f"Failed to save corrected transcript: {str(e)}")
            raise

        # Save key corrections if available
        if key_corrections:
            try:
                corrections_path = base_dir / "subtitles_corrections.txt"
                corrections_path.write_text(key_corrections, encoding="utf-8")
                logger.debug(f"Saved key corrections to {corrections_path}")
            except Exception as e:
                logger.debug(f"Failed to save key corrections: {str(e)}")
                # Continue anyway since this is not critical

        console.print(
            "[green]LLM post-processing complete. Corrected transcript saved.[/green]"
        )

        return corrected_transcript

    async def _get_user_profile(
        self, uid: int, credential_browser: Optional[str] = None
    ) -> dict:
        """Get detailed user profile information.

        Args:
            uid: User ID
            credential_browser: Browser to use for credential extraction

        Returns:
            Dictionary with user information including name, bio, followers, etc.
        """
        logger.debug(f"Fetching user profile for UID: {uid}")

        # If browser is provided but credential is not set, try to extract credentials
        temp_credential = None
        if credential_browser and not self.credential:
            try:
                logger.debug(
                    f"Trying to extract credentials from {credential_browser} for user profile"
                )

                cookie_file = get_browser_cookies(credential_browser)

                if cookie_file:
                    # Parse the cookies to extract Bilibili specific ones
                    cookie_data = {}
                    with open(cookie_file, "r") as f:
                        for line in f:
                            if line.startswith("#") or not line.strip():
                                continue
                            fields = line.strip().split("\t")
                            if len(fields) >= 7:
                                name, value = fields[5], fields[6]
                                cookie_data[name] = value

                    # Create a temporary credential for this request
                    if any(
                        k in cookie_data for k in ["SESSDATA", "bili_jct", "buvid3"]
                    ):
                        temp_credential = Credential(
                            sessdata=cookie_data.get("SESSDATA"),
                            bili_jct=cookie_data.get("bili_jct"),
                            buvid3=cookie_data.get("buvid3"),
                        )
                        logger.debug(
                            "Created temporary credential from browser cookies"
                        )
            except Exception as e:
                logger.debug(f"Failed to extract credentials from browser: {str(e)}")

        try:
            # Create user object with credentials if available
            u = user.User(uid, credential=temp_credential or self.credential)

            # Get basic user info
            user_info = await u.get_user_info()

            # Get relation info (followers)
            relation_info = await u.get_relation_info()

            # Combine the information
            profile = {
                "uid": uid,
                "name": user_info.get("name", "Unknown"),
                "sign": user_info.get("sign", ""),
                "level": user_info.get("level", 0),
                "follower_count": relation_info.get("follower", 0),
            }

            # Try to get user's video count (may fail silently)
            try:
                space_info = await u.get_videos(pn=1, ps=1)
                if space_info and "page" in space_info:
                    profile["video_count"] = space_info["page"].get("count", 0)
            except Exception as e:
                logger.debug(f"Error getting video count: {str(e)}")
                # Don't raise error for this optional info

            return profile
        except Exception as e:
            logger.debug(f"Error fetching user profile: {str(e)}")
            raise

    async def get_all_user_subtitles(
        self,
        uid: int,
        browser: Optional[str] = None,
        limit: Optional[int] = None,
        include_description: bool = True,
        include_meta_info: bool = True,
    ) -> tuple[str, dict]:
        """Get subtitles from all videos of a user and combine them into a single text file.

        Args:
            uid: User ID
            browser: Browser to extract cookies from for authentication
            limit: Maximum number of videos to process (None for all)
            include_description: Whether to include video descriptions in the output
            include_meta_info: Whether to include meta info (title, views, coins, etc.)

        Returns:
            Tuple of (combined subtitles text, stats dictionary)
        """
        console = Console()

        # Confirm all input parameters before starting visual progress indicators
        console.print(
            f"[cyan]Initializing subtitle extraction for user {uid}...[/cyan]"
        )

        # Warn if no browser provided
        if not browser:
            console.print(
                "[yellow]Warning: No browser authentication provided. Some videos may require authentication.[/yellow]"
            )
            console.print(
                "[yellow]If export fails, retry with --browser chrome or --browser firefox[/yellow]"
            )

        # Get list of user's videos (this must be done before showing any progress bars)
        console.print(f"[cyan]Fetching video list for user {uid}...[/cyan]")
        videos = await self.get_user_videos(uid)

        if not videos:
            console.print("[yellow]No videos found for this user.[/yellow]")
            return "", {
                "total_videos": 0,
                "processed_videos": 0,
                "videos_with_subtitles": 0,
            }

        # Limit number of videos if specified
        if limit and limit > 0 and limit < len(videos):
            console.print(
                f"[cyan]Limiting to {limit} videos out of {len(videos)} total videos[/cyan]"
            )
            videos = videos[:limit]
        elif limit == 0:
            console.print(
                f"[yellow]Limit of 0 videos specified. No videos will be processed.[/yellow]"
            )
            return "", {
                "total_videos": len(videos),
                "processed_videos": 0,
                "videos_with_subtitles": 0,
            }
        else:
            console.print(f"[cyan]Found {len(videos)} videos to process[/cyan]")

        # Last confirmation message before starting intensive processing
        console.print(
            "[bold cyan]Beginning subtitle extraction for all videos...[/bold cyan]"
        )

        # Statistics tracking
        stats = {
            "total_videos": len(videos),
            "processed_videos": 0,
            "videos_with_subtitles": 0,
            "subtitle_sources": {"api": 0, "yt-dlp": 0, "whisper": 0, "failed": 0},
        }

        # Add flag to identify this is from export_user_subtitles
        # This will be used in exception handling to suggest the right command
        os.environ["export_user_subtitles"] = str(uid)

        try:
            # Create text content config that only includes subtitles
            config = VideoTextConfig(
                include_subtitles=True,
                include_comments=False,
                include_uploader_info=False,
                include_meta_info=include_meta_info,
            )

            all_subtitles = []

            # Process videos with progress bar
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
                console=console,
                expand=True,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Processing videos...", total=len(videos)
                )

                for video in videos:
                    # Update progress
                    progress.update(
                        task,
                        description=f"[cyan]Processing {video.bvid}: {video.title[:30]}...",
                    )

                    try:
                        # Get video content with subtitles
                        content = await self.get_video_text_content(
                            video.bvid, config=config, browser=browser
                        )

                        # Update processed count
                        stats["processed_videos"] += 1

                        # Check if subtitles were found
                        if content.subtitles:
                            # Determine subtitle source from content
                            subtitle_source = "api"
                            if "Whisper Transcript" in content.subtitles:
                                subtitle_source = "whisper"
                            elif "yt-dlp" in content.subtitles:
                                subtitle_source = "yt-dlp"

                            # Update stats
                            stats["videos_with_subtitles"] += 1
                            stats["subtitle_sources"][subtitle_source] += 1

                            # Format subtitle text
                            header = format_subtitle_header(
                                video, include_description, config.include_meta_info
                            )
                            subtitle_text = content.subtitles

                            # Remove section headers that might be in markdown
                            subtitle_text = re.sub(
                                r"^#+\s*Video Subtitles.*$",
                                "",
                                subtitle_text,
                                flags=re.MULTILINE,
                            )
                            subtitle_text = re.sub(
                                r"^#+\s*Whisper Transcript.*$",
                                "",
                                subtitle_text,
                                flags=re.MULTILINE,
                            )

                            # Remove timestamps
                            clean_subtitles = remove_timestamps(subtitle_text)

                            # Add to results
                            all_subtitles.append(f"{header}\n\n{clean_subtitles}")
                        else:
                            # No subtitles found
                            header = format_subtitle_header(
                                video, include_description, config.include_meta_info
                            )
                            all_subtitles.append(f"{header}\n\n[无字幕]")
                            stats["subtitle_sources"]["failed"] += 1

                    except Exception as e:
                        error_message = str(e)
                        logger.debug(
                            f"Error processing video {video.bvid}: {error_message}"
                        )

                        # Check if it's an authentication error
                        if "Authentication required" in error_message:
                            # Re-raise to exit the entire process
                            raise

                        # Special handling for yt-dlp format errors
                        if "Requested format is not available" in error_message:
                            console.print(
                                f"[yellow]Video {video.bvid} format not available for download, skipping...[/yellow]"
                            )
                        # Special handling for deleted or restricted videos
                        elif (
                            "This video is unavailable" in error_message
                            or "has been deleted" in error_message
                        ):
                            console.print(
                                f"[yellow]Video {video.bvid} is unavailable or deleted, skipping...[/yellow]"
                            )
                        # General error message for other cases
                        else:
                            console.print(
                                f"[yellow]Error processing video {video.bvid}: {error_message}[/yellow]"
                            )

                        # Add error message for all errors
                        header = format_subtitle_header(
                            video, include_description, config.include_meta_info
                        )
                        all_subtitles.append(
                            f"{header}\n\n[字幕获取失败: {error_message}]"
                        )
                        stats["subtitle_sources"]["failed"] += 1

                    # Update progress
                    progress.advance(task)

            # Combine all subtitles with double newline between videos
            combined_text = "\n\n\n".join(all_subtitles)

            # Calculate total token count (rough estimate)
            stats["total_tokens"] = len(combined_text.split()) * 1.5

            # Display summary
            console.print(f"[green]Processing complete![/green]")
            console.print(
                f"[green]Processed {stats['processed_videos']} videos, found subtitles for {stats['videos_with_subtitles']} videos[/green]"
            )

            return combined_text, stats

        finally:
            # Clean up the environment variable
            if "export_user_subtitles" in os.environ:
                del os.environ["export_user_subtitles"]
