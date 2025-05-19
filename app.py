import streamlit as st
import subprocess
import re
import pandas as pd
from pathlib import Path
import os
import json
from datetime import datetime
from pages.visualizations import (
    get_user_videos as fetch_user_videos,
    parse_user_videos as parse_user_videos_table,
)

# Set page configuration
st.set_page_config(
    page_title="Bilibili Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS to make the UI more beautiful
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FC8EAC;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #73C2FB;
        margin-bottom: 1rem;
    }
    .info-text {
        font-size: 1rem;
        color: #888888;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        white-space: pre-wrap;
        background-color: #1E1E1E;
        border-radius: 5px;
        color: white;
        padding: 1rem 2rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #73C2FB !important;
        color: white !important;
    }
    .stTextInput > div > div > input {
        height: 3rem;
    }
    .stRadio > div > div > label {
        background-color: #1E1E1E;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        margin-right: 0.5rem;
    }
    .stRadio > div {
        display: flex;
        flex-direction: row;
    }
    .result-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .viz-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def run_command(cmd):
    """Run a command and return the output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        st.error(f"Command failed with error: {e.stderr}")
        return None


def get_video_info(identifier, browser=None):
    """Get video information using the Bilibili client, always as JSON"""
    cmd = ["python", "main.py", identifier, "--json"]

    if browser:
        cmd.extend(["--browser", browser])

    return run_command(cmd)


def get_video_text(identifier, content_types=None, browser=None, output=None):
    """Get video text content"""
    cmd = ["python", "main.py", identifier, "--text"]

    if content_types:
        cmd.extend(["--content", content_types])

    if browser:
        cmd.extend(["--browser", browser])

    if output:
        cmd.extend(["--output", output])

    return run_command(cmd)


def export_user_subtitles(
    identifier,
    browser=None,
    subtitle_limit=None,
    no_description=False,
    no_meta_info=False,
    output=None,
):
    """Export user subtitles"""
    cmd = ["python", "main.py", identifier, "--export-user-subtitles"]

    if browser:
        cmd.extend(["--browser", browser])

    if subtitle_limit:
        cmd.extend(["--subtitle-limit", str(subtitle_limit)])

    if no_description:
        cmd.append("--no-description")

    if no_meta_info:
        cmd.append("--no-meta-info")

    if output:
        cmd.extend(["--output", output])

    return run_command(cmd)


def show_video_info_streamlit(video_info: dict):
    """Display video info in a beautiful card layout using Streamlit."""
    if not video_info:
        st.warning("No video information available.")
        return

    def format_duration(seconds):
        try:
            seconds = int(seconds)
        except Exception:
            return str(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    st.markdown('<div class="viz-container">', unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='color:#FC8EAC;margin-bottom:0.5rem;'>🎬 {video_info.get('title', '')}</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='color:#888;'>BVID: {video_info.get('bvid', '')}</span>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"<b>⏱ Duration:</b> <span style='color:#73C2FB'>{format_duration(video_info.get('duration', 0))}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>📅 Upload Time:</b> <span style='color:#73C2FB'>{video_info.get('upload_time', '')}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>👁️ Views:</b> <span style='color:#73C2FB'>{video_info.get('view_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>👍 Likes:</b> <span style='color:#73C2FB'>{video_info.get('like_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>🪙 Coins:</b> <span style='color:#73C2FB'>{video_info.get('coin_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>⭐ Favorites:</b> <span style='color:#73C2FB'>{video_info.get('favorite_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<b>🔁 Shares:</b> <span style='color:#73C2FB'>{video_info.get('share_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>💬 Comments:</b> <span style='color:#73C2FB'>{video_info.get('comment_count', 0):,}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<b>👤 Uploader:</b> <span style='color:#73C2FB'>{video_info.get('owner_name', '')} (UID: {video_info.get('owner_mid', '')})</span>",
            unsafe_allow_html=True,
        )
        if video_info.get("is_charging_exclusive"):
            st.markdown(
                f"<span style='color:#FF4B4B;font-weight:bold;'>⚡ Charging Exclusive Content</span>",
                unsafe_allow_html=True,
            )
            if video_info.get("charging_level"):
                st.markdown(
                    f"<span style='color:#FFB347;'>Charging Level: {video_info.get('charging_level')}</span>",
                    unsafe_allow_html=True,
                )

    desc = video_info.get("description", "")
    if desc:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<b>Description:</b>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='white-space: pre-wrap; color:#ccc'>{desc}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def show_video_section():
    st.markdown('<div class="sub-header">Video Analysis</div>', unsafe_allow_html=True)

    # Input for video identifier
    video_identifier = st.text_input(
        "Enter Bilibili Video URL or BVID",
        placeholder="https://www.bilibili.com/video/BV... or BV...",
    )

    col1, col2 = st.columns(2)

    with col1:
        browser = st.selectbox(
            "Browser for authentication (optional)", ["None", "Chrome", "Firefox"]
        )

    with col2:
        content_types = st.multiselect(
            "Content to include",
            ["subtitles", "comments", "uploader"],
            default=["subtitles", "uploader"],
        )

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        info_button = st.button("Get Video Info", type="primary")

    with col2:
        text_button = st.button("Get Video Text", type="primary")

    # Show results
    if video_identifier:
        if info_button:
            with st.spinner("Fetching video information..."):
                browser_arg = None if browser == "None" else browser.lower()
                output = get_video_info(video_identifier, browser_arg)

                if output:
                    st.markdown(
                        '<div class="result-container">', unsafe_allow_html=True
                    )
                    st.subheader("Video Information")
                    try:
                        video_info = json.loads(output)
                        show_video_info_streamlit(video_info)
                    except Exception as e:
                        st.error(f"Failed to parse video info as JSON: {e}")
                        st.text(output)

                    # Show raw output in expander
                    with st.expander("View Raw Output"):
                        st.text(output)
                    st.markdown("</div>", unsafe_allow_html=True)

        if text_button:
            with st.spinner("Fetching video text content..."):
                browser_arg = None if browser == "None" else browser.lower()
                content_arg = (
                    ",".join(content_types) if content_types else "subtitles,uploader"
                )

                # Create a temporary file to save the output
                temp_output = (
                    f"temp_output_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                )
                output = get_video_text(
                    video_identifier, content_arg, browser_arg, temp_output
                )

                st.markdown('<div class="result-container">', unsafe_allow_html=True)
                st.subheader("Video Text Content")

                # Read the content of the saved file
                try:
                    if os.path.exists(temp_output):
                        with open(temp_output, "r", encoding="utf-8") as f:
                            content = f.read()
                        st.text_area("Text Content", content, height=400)

                        # Provide download button
                        st.download_button(
                            label="Download Text Content",
                            data=content,
                            file_name=f"bilibili_content_{video_identifier}.txt",
                            mime="text/plain",
                        )

                        # Clean up
                        os.remove(temp_output)
                    else:
                        st.warning("No text content was saved.")
                except Exception as e:
                    st.error(f"Error reading content: {str(e)}")

                st.markdown("</div>", unsafe_allow_html=True)


def show_user_section():
    st.markdown('<div class="sub-header">User Analysis</div>', unsafe_allow_html=True)

    # Input for user identifier
    user_identifier = st.text_input("Enter Bilibili User UID", placeholder="12345678")

    col1, col2, col3 = st.columns(3)

    with col1:
        browser = st.selectbox(
            "Browser for authentication (optional)",
            ["None", "Chrome", "Firefox"],
            key="user_browser",
        )

    with col2:
        subtitle_limit = st.number_input(
            "Subtitle Limit (optional)",
            min_value=0,
            value=0,
            help="Limit the number of videos to process (0 = no limit)",
        )

    with col3:
        st.write("Options")
        no_description = st.checkbox("No Description")
        no_meta_info = st.checkbox("No Meta Info")

    # New: Button to fetch user video list
    fetch_list_button = st.button("Fetch User Video List", type="primary")
    export_button = None
    video_df = None
    if user_identifier and fetch_list_button:
        with st.spinner("Fetching user video list..."):
            browser_arg = None if browser == "None" else browser.lower()
            output = fetch_user_videos(user_identifier, browser_arg)
            if output:
                video_df = parse_user_videos_table(output)
                if video_df is not None and not video_df.empty:
                    st.markdown(
                        '<div class="result-container">', unsafe_allow_html=True
                    )
                    st.subheader(f"Video List for User {user_identifier}")
                    st.dataframe(video_df, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    export_button = st.button("Export User Subtitles", type="primary")
                else:
                    st.warning("No videos found for this user.")
            else:
                st.error("Failed to fetch user video list.")

    # Show export button only after list is fetched
    if user_identifier and export_button:
        with st.spinner("Exporting user subtitles... This may take a while."):
            browser_arg = None if browser == "None" else browser.lower()
            subtitle_limit_arg = None if subtitle_limit == 0 else subtitle_limit

            # Create output directory if it doesn't exist
            output_dir = Path(f"user_{user_identifier}")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "all_subtitles.txt"

            output = export_user_subtitles(
                user_identifier,
                browser_arg,
                subtitle_limit_arg,
                no_description,
                no_meta_info,
                str(output_file),
            )

            if output:
                st.markdown('<div class="result-container">', unsafe_allow_html=True)
                st.success(
                    f"Successfully exported subtitles for user {user_identifier}"
                )

                # Check if the file exists
                if output_file.exists():
                    # Show a preview of the file
                    with open(output_file, "r", encoding="utf-8") as f:
                        content = f.read(10000)  # First 10000 characters

                    st.text_area("Preview of Subtitles", content, height=300)

                    # Provide download button
                    with open(output_file, "r", encoding="utf-8") as f:
                        full_content = f.read()

                    st.download_button(
                        label="Download Full Subtitles",
                        data=full_content,
                        file_name=f"user_{user_identifier}_subtitles.txt",
                        mime="text/plain",
                    )

                    # Show stats if available
                    stats_file = output_dir / "stats.txt"
                    if stats_file.exists():
                        with open(stats_file, "r", encoding="utf-8") as f:
                            stats_content = f.read()

                        with st.expander("View Processing Statistics"):
                            st.text(stats_content)

                st.markdown("</div>", unsafe_allow_html=True)


def main():
    # Main header
    st.markdown(
        '<div class="main-header">Bilibili Analyzer</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="info-text">A powerful tool to analyze Bilibili videos and users</div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    st.sidebar.title("Bilibili Analyzer")
    st.sidebar.markdown("---")
    st.sidebar.info(
        """
        This app provides a user-friendly interface for the Bilibili Analyzer tool.
        
        [View on GitHub](https://github.com/your-username/bilibili-analyzer)
        """
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Bilibili Analyzer")

    # Create tabs
    tab1, tab2 = st.tabs(["Video Analysis", "User Analysis"])

    with tab1:
        show_video_section()

    with tab2:
        show_user_section()


if __name__ == "__main__":
    main()
