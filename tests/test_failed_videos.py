import asyncio
import pytest

from bilibili_client import BilibiliClient, VideoInfo, VideoTextContent


class TestFailedVideosTracking:
    """Test failed video tracking functionality"""

    def setup_method(self):
        # Create mock VideoInfo objects
        self.mock_videos = [
            VideoInfo(
                bvid=f"bvid{i}",
                title=f"Test Video {i}",
                description="Test Description",
                duration=100,
                view_count=1000,
                like_count=100,
                coin_count=50,
                favorite_count=30,
                share_count=20,
                upload_time="2023-01-01",
                owner_name="Test User",
                owner_mid=12345,
                comment_count=10,
                is_charging_exclusive=False,
                charging_level="",
            )
            for i in range(1, 4)  # Create 3 videos
        ]

    @pytest.mark.asyncio
    async def test_failed_videos_tracking(self, mocker):
        """Test if videos are correctly tracked when processing fails"""
        # Configure mock return values
        mock_get_videos = mocker.patch("bilibili_client.BilibiliClient.get_user_videos")
        mock_get_videos.return_value = self.mock_videos

        # Mock video processing failure for the second video
        mock_get_content = mocker.patch(
            "bilibili_client.BilibiliClient.get_video_text_content"
        )

        async def mock_get_content_side_effect(bvid, **kwargs):
            if bvid == "bvid2":
                raise Exception("Simulated download failure")

            # Other videos succeed
            return VideoTextContent(
                basic_info="Test basic info",
                uploader_info="Test uploader info",
                tags_and_categories="Test tags",
                subtitles="Test subtitles",
            )

        mock_get_content.side_effect = mock_get_content_side_effect

        # Create client and call method
        client = BilibiliClient()
        combined_text, stats = await client.get_all_user_subtitles(
            uid=12345,
            browser=None,
            limit=None,
            include_description=True,
            include_meta_info=True,
            force_charging=False,
            skip_charging=False,
        )

        # Assertions
        assert len(stats["failed_videos"]) == 1, "Should have 1 failed video"
        assert (
            stats["failed_videos"][0]["bvid"] == "bvid2"
        ), "Failed video BV ID should be bvid2"
        assert (
            stats["failed_videos"][0]["title"] == "Test Video 2"
        ), "Failed video title should be Test Video 2"
        assert (
            "Simulated download failure" in stats["failed_videos"][0]["error"]
        ), "Error message should contain 'Simulated download failure'"


# Run test
if __name__ == "__main__":
    # Run async test
    loop = asyncio.get_event_loop()
    loop.run_until_complete(TestFailedVideosTracking().test_failed_videos_tracking())
    print("Test completed")
