import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Help & About - Bilibili Analyzer",
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
    .help-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">Help & About</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="info-text">Learn how to use the Bilibili Analyzer</div>',
    unsafe_allow_html=True,
)

# Application overview
st.markdown(
    '<div class="sub-header">About Bilibili Analyzer</div>', unsafe_allow_html=True
)
st.markdown('<div class="help-container">', unsafe_allow_html=True)
st.markdown(
    """
Bilibili Analyzer is a powerful tool that helps you analyze videos and users on Bilibili. 
It provides features to:

- Fetch detailed information about a single video
- Get video text content including subtitles, comments, and more
- Export all subtitles from a user's videos to a single text file

The application is built on top of a Python tool that can fetch video information from 
Bilibili using either a video URL/BVID or user UID.
"""
)
st.markdown("</div>", unsafe_allow_html=True)

# Video Analysis Help
st.markdown('<div class="sub-header">Video Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="help-container">', unsafe_allow_html=True)
st.markdown(
    """
The **Video Analysis** tab allows you to analyze a single Bilibili video.

### How to use:

1. Enter a Bilibili video URL or BVID in the text input field
   - Example URL: `https://www.bilibili.com/video/BV1xx411c7mD`
   - Example BVID: `BV1xx411c7mD`

2. Select a browser for authentication (optional)
   - This is needed for videos that require authentication
   - Supported browsers: Chrome, Firefox
   - Leave as "None" if authentication is not required

3. Select the content types to include
   - Subtitles: Video subtitles/captions
   - Comments: User comments on the video
   - Uploader: Information about the video uploader

4. Use the action buttons:
   - **Get Video Info**: Fetches basic information about the video
   - **Get Video Text**: Fetches the video text content based on selected options

### Note:

For videos that require authentication (premium content), you need to select a browser 
to extract cookies from your logged-in session.
"""
)
st.markdown("</div>", unsafe_allow_html=True)

# User Analysis Help
st.markdown('<div class="sub-header">User Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="help-container">', unsafe_allow_html=True)
st.markdown(
    """
The **User Analysis** tab allows you to analyze a Bilibili user and export their video subtitles.

### How to use:

1. Enter a Bilibili user UID in the text input field
   - Example: `12345678`

2. Select a browser for authentication (optional)
   - This is needed for users with private or premium videos
   - Supported browsers: Chrome, Firefox
   - Leave as "None" if authentication is not required

3. Configure options:
   - **Subtitle Limit**: Limit the number of videos to process (0 = no limit)
   - **No Description**: Don't include video descriptions in exported subtitles
   - **No Meta Info**: Don't include meta information in the header of each video

4. Click the **Export User Subtitles** button to start the process
   - This will fetch all videos from the user
   - Extract subtitles from each video
   - Combine all subtitles into a single text file
   - Save the file and provide statistics about the process

### Note:

Exporting subtitles for users with many videos can take a significant amount of time. 
Consider using the subtitle limit option if you only need a sample of videos.
"""
)
st.markdown("</div>", unsafe_allow_html=True)

# Requirements and credits
st.markdown(
    '<div class="sub-header">Requirements & Credits</div>', unsafe_allow_html=True
)
st.markdown('<div class="help-container">', unsafe_allow_html=True)
st.markdown(
    """
### Requirements:

- Python >= 3.12, < 4.0
- Streamlit
- ffmpeg (for audio extraction)
- A browser (Chrome or Firefox) for authenticated access

### Credits:

Bilibili Analyzer is an open-source project developed to help users analyze Bilibili content.
This web interface is built with Streamlit to provide an easy-to-use front-end for the underlying 
Python tool.

For more information and updates, please refer to the project documentation.
"""
)
st.markdown("</div>", unsafe_allow_html=True)
