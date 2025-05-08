from typing import List, Optional
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import subprocess
import logging
import aiohttp
from bilibili_api import video, user, Credential
from pydantic import BaseModel, Field

logger = logging.getLogger("bilibili_client")


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
    subtitle_markdown: bool = Field(
        default=False, description="Whether to format subtitles in markdown"
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
        )

    async def get_user_videos(
        self, uid: int, page: int = 1, page_size: int = 30
    ) -> List[VideoInfo]:
        """Get all videos from a user"""
        u = user.User(uid)
        videos = await u.get_videos(pn=page, ps=page_size)

        return [
            VideoInfo(
                bvid=item["bvid"],
                title=item["title"],
                description=item["description"],
                duration=self._parse_duration(item["length"]),
                view_count=item["play"],
                like_count=item.get("like", 0),
                coin_count=item.get("coin", 0),
                favorite_count=item.get("favorite", 0),
                share_count=item.get("share", 0),
                upload_time=self._format_timestamp(item["created"]),
                owner_name=item["author"],
                owner_mid=uid,
            )
            for item in videos["list"]["vlist"]
        ]

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

    async def _format_subtitles(
        self, v: video.Video, cid: int, markdown: bool = False
    ) -> Optional[str]:
        """Format video subtitles as markdown or plain text

        Args:
            v: Video object
            cid: Video CID
            markdown: Whether to format output as markdown
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
                if markdown:
                    all_subtitles.append(f"\n### Subtitles ({lang})\n")
                else:
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

            if markdown:
                return "## Video Subtitles\n" + "\n".join(all_subtitles)
            else:
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
        self, identifier: str, config: Optional[VideoTextConfig] = None
    ) -> VideoTextContent:
        """Get video text content in markdown format

        Args:
            identifier: A Bilibili video URL or BVID
            config: Configuration for text content extraction

        Returns:
            VideoTextContent object containing markdown formatted text
        """
        config = config or VideoTextConfig()
        bvid = self._extract_bvid(identifier)

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
            try:
                subtitles = await self._format_subtitles(
                    v, info["cid"], config.subtitle_markdown
                )
            except Exception as e:
                logger.debug(f"Error getting subtitles: {str(e)}")

        # Whisper fallback if no subtitles
        if config.include_subtitles and not subtitles:
            confirm = (
                input(
                    "No subtitles found. Download audio and generate subtitles with Whisper? This may take a long time. [y/N]: "
                )
                .strip()
                .lower()
            )
            if confirm == "y":
                # Prepare paths
                base_dir = Path("video_texts") / bvid
                base_dir.mkdir(parents=True, exist_ok=True)
                audio_path = base_dir / "temp_audio.m4a"
                transcript_path = base_dir / "whisper_transcript.txt"
                # Download audio
                from main import ensure_bilibili_url, download_audio

                url = ensure_bilibili_url(identifier)
                download_audio(url, output_path=str(audio_path))
                # Run Whisper
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
                subprocess.run(cmd, check=True)
                # Move/rename output if needed
                generated_txt = base_dir / (audio_path.stem + ".txt")
                if generated_txt != transcript_path:
                    generated_txt.rename(transcript_path)
                transcript = transcript_path.read_text(encoding="utf-8")
                subtitles = "## Whisper Transcript\n" + transcript
                # Clean up temp audio
                audio_path.unlink(missing_ok=True)
            else:
                subtitles = "No subtitles available and user declined Whisper fallback."

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
