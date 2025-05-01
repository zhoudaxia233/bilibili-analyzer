from typing import List
from datetime import datetime
from urllib.parse import urlparse
from bilibili_api import video, user
from pydantic import BaseModel, Field


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


class BilibiliClient:
    """Client for interacting with Bilibili API"""

    def __init__(self):
        pass

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
