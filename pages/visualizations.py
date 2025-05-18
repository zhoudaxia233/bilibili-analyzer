import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import os
import subprocess
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Visualizations - Bilibili Analyzer",
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
    .viz-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def run_command(cmd):
    """Run a command and return the output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        st.error(f"Command failed with error: {e.stderr}")
        return None


def get_user_videos(uid, browser=None):
    """Get videos from a user using the Bilibili client"""
    cmd = ["python", "main.py", uid, "--user"]

    if browser:
        cmd.extend(["--browser", browser])

    return run_command(cmd)


def parse_user_videos(output):
    """Parse the user videos from the command output"""
    if not output:
        return None

    # Prepare data structure
    videos = []

    # Extract table rows using regex
    pattern = (
        r"│\s+(\S+)\s+│\s+(.+?)\s+│\s+(\d\d:\d\d:\d\d)\s+│\s+(\d+)\s+│\s+(.+?)\s+│"
    )
    matches = re.findall(pattern, output)

    for match in matches:
        if len(match) == 5:
            bvid, title, duration, views, upload_time = match

            # Convert duration to seconds for chart purposes
            duration_parts = duration.split(":")
            duration_seconds = (
                int(duration_parts[0]) * 3600
                + int(duration_parts[1]) * 60
                + int(duration_parts[2])
            )

            videos.append(
                {
                    "BVID": bvid,
                    "Title": title.strip(),
                    "Duration": duration,
                    "Duration (seconds)": duration_seconds,
                    "Views": int(views),
                    "Upload Time": upload_time.strip(),
                }
            )

    return pd.DataFrame(videos)


def generate_visualizations(df):
    """Generate visualizations based on the data"""
    if df is None or df.empty:
        st.warning("No data available for visualization.")
        return

    # View count distribution
    st.markdown(
        '<div class="sub-header">View Count Distribution</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="viz-container">', unsafe_allow_html=True)

    fig = px.histogram(
        df,
        x="Views",
        nbins=20,
        title="Distribution of Video Views",
        color_discrete_sequence=["#73C2FB"],
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # View count vs. Duration
    st.markdown(
        '<div class="sub-header">Views vs. Duration</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="viz-container">', unsafe_allow_html=True)

    fig = px.scatter(
        df,
        x="Duration (seconds)",
        y="Views",
        hover_name="Title",
        size="Views",
        size_max=50,
        color="Views",
        color_continuous_scale="Turbo",
        title="Video Views vs. Duration",
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Top Videos by Views
    st.markdown(
        '<div class="sub-header">Top Videos by Views</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="viz-container">', unsafe_allow_html=True)

    top_videos = df.sort_values(by="Views", ascending=False).head(10)

    fig = px.bar(
        top_videos,
        x="Views",
        y="Title",
        orientation="h",
        color="Views",
        color_continuous_scale="Turbo",
        title="Top 10 Videos by View Count",
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        margin=dict(l=40, r=40, t=50, b=40),
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Duration Distribution
    st.markdown(
        '<div class="sub-header">Duration Distribution</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="viz-container">', unsafe_allow_html=True)

    fig = px.histogram(
        df,
        x="Duration (seconds)",
        nbins=20,
        title="Distribution of Video Durations",
        color_discrete_sequence=["#FC8EAC"],
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Upload Timeline
    if "Upload Time" in df.columns:
        try:
            st.markdown(
                '<div class="sub-header">Upload Timeline</div>', unsafe_allow_html=True
            )
            st.markdown('<div class="viz-container">', unsafe_allow_html=True)

            # Convert upload time to datetime if possible
            df["Upload Datetime"] = pd.to_datetime(df["Upload Time"], errors="coerce")
            df = df.sort_values(by="Upload Datetime")

            # Create a timeline plot
            fig = px.scatter(
                df,
                x="Upload Datetime",
                y="Views",
                size="Views",
                hover_name="Title",
                color="Views",
                color_continuous_scale="Turbo",
                title="Video Upload Timeline",
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#1E1E1E",
                paper_bgcolor="#1E1E1E",
                margin=dict(l=40, r=40, t=50, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Could not generate upload timeline: {str(e)}")


def main():
    # Main header
    st.markdown('<div class="main-header">Visualizations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-text">Visual analytics for Bilibili content</div>',
        unsafe_allow_html=True,
    )

    # Input section
    st.markdown(
        '<div class="sub-header">Generate Visualizations</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="viz-container">', unsafe_allow_html=True)

    user_uid = st.text_input("Enter Bilibili User UID", placeholder="12345678")

    col1, col2 = st.columns(2)

    with col1:
        browser = st.selectbox(
            "Browser for authentication (optional)", ["None", "Chrome", "Firefox"]
        )

    with col2:
        refresh = st.checkbox("Refresh data", value=False)

    analyze_button = st.button("Generate Visualizations", type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # Process and visualize
    if user_uid and analyze_button:
        with st.spinner("Fetching and analyzing data... This may take a while."):
            # Check if we already have cached data
            cache_file = f"viz_cache_{user_uid}.csv"

            if os.path.exists(cache_file) and not refresh:
                # Load cached data
                df = pd.read_csv(cache_file)
                st.success(f"Loaded cached data for user {user_uid}")
            else:
                # Fetch new data
                browser_arg = None if browser == "None" else browser.lower()
                output = get_user_videos(user_uid, browser_arg)

                if output:
                    df = parse_user_videos(output)

                    # Cache the data
                    if df is not None and not df.empty:
                        df.to_csv(cache_file, index=False)

                    st.success(f"Successfully fetched data for user {user_uid}")
                else:
                    st.error("Failed to fetch user data.")
                    return

            # Generate visualizations
            generate_visualizations(df)

            # Show data table
            with st.expander("View Data Table"):
                st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
