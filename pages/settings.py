import streamlit as st
import os
import json
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="Settings - Bilibili Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants
CONFIG_DIR = Path(".streamlit")
CONFIG_FILE = CONFIG_DIR / "bilibili_analyzer_config.json"

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
    .settings-container {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .stButton button {
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Functions to load and save settings
def load_settings():
    """Load settings from the config file"""
    default_settings = {
        "default_browser": "None",
        "default_content_types": ["subtitles", "uploader"],
        "output_directory": "bilibili_outputs",
        "whisper_model": "tiny",
        "subtitle_limit": 20,
        "debug_mode": False,
    }

    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(exist_ok=True)

    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=4)
        return default_settings

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        st.error(f"Error loading settings: {str(e)}")
        return default_settings


def save_settings(settings):
    """Save settings to the config file"""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(exist_ok=True)

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving settings: {str(e)}")
        return False


# Main settings UI
st.markdown('<div class="main-header">Settings</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="info-text">Configure Bilibili Analyzer preferences</div>',
    unsafe_allow_html=True,
)

# Load current settings
settings = load_settings()

# General Settings
st.markdown('<div class="sub-header">General Settings</div>', unsafe_allow_html=True)
st.markdown('<div class="settings-container">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    default_browser = st.selectbox(
        "Default Browser for Authentication",
        options=["None", "Chrome", "Firefox"],
        index=["None", "Chrome", "Firefox"].index(
            settings.get("default_browser", "None")
        ),
    )

with col2:
    output_directory = st.text_input(
        "Output Directory", value=settings.get("output_directory", "bilibili_outputs")
    )

default_content_types = st.multiselect(
    "Default Content Types",
    options=["subtitles", "comments", "uploader"],
    default=settings.get("default_content_types", ["subtitles", "uploader"]),
)

debug_mode = st.checkbox(
    "Debug Mode",
    value=settings.get("debug_mode", False),
    help="Enable debug logging output",
)

st.markdown("</div>", unsafe_allow_html=True)

# Advanced Settings
st.markdown('<div class="sub-header">Advanced Settings</div>', unsafe_allow_html=True)
st.markdown('<div class="settings-container">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    whisper_model = st.selectbox(
        "Whisper Model",
        options=["tiny", "base", "small", "medium", "large"],
        index=["tiny", "base", "small", "medium", "large"].index(
            settings.get("whisper_model", "tiny")
        ),
        help="Model size for Whisper AI transcription (larger models are more accurate but slower)",
    )

with col2:
    subtitle_limit = st.number_input(
        "Default Subtitle Limit",
        min_value=0,
        value=settings.get("subtitle_limit", 20),
        help="Default limit for the number of videos to process (0 = no limit)",
    )

st.markdown("</div>", unsafe_allow_html=True)

# Environment Variables
st.markdown(
    '<div class="sub-header">Environment Variables</div>', unsafe_allow_html=True
)
st.markdown('<div class="settings-container">', unsafe_allow_html=True)

st.markdown(
    """
You can set environment variables by creating a `.env` file in the application directory.
The following variables are supported:

```
# Bilibili credentials (optional)
BILIBILI_SESSDATA=your_sessdata
BILIBILI_BILI_JCT=your_bili_jct
BILIBILI_BUVID3=your_buvid3
```

Note: These credentials are sensitive information. Do not share them with others.
"""
)

st.markdown("</div>", unsafe_allow_html=True)

# Save Settings
st.markdown('<div class="settings-container">', unsafe_allow_html=True)
save_button = st.button("Save Settings", type="primary")

if save_button:
    # Update settings
    new_settings = {
        "default_browser": default_browser,
        "default_content_types": default_content_types,
        "output_directory": output_directory,
        "whisper_model": whisper_model,
        "subtitle_limit": subtitle_limit,
        "debug_mode": debug_mode,
    }

    # Save to file
    if save_settings(new_settings):
        st.success("Settings saved successfully!")
    else:
        st.error("Failed to save settings.")

st.markdown("</div>", unsafe_allow_html=True)

# Reset Settings
st.markdown('<div class="settings-container">', unsafe_allow_html=True)
reset_button = st.button("Reset to Default Settings")

if reset_button:
    default_settings = {
        "default_browser": "None",
        "default_content_types": ["subtitles", "uploader"],
        "output_directory": "bilibili_outputs",
        "whisper_model": "tiny",
        "subtitle_limit": 20,
        "debug_mode": False,
    }

    if save_settings(default_settings):
        st.success("Settings reset to defaults successfully!")
        st.rerun()
    else:
        st.error("Failed to reset settings.")

st.markdown("</div>", unsafe_allow_html=True)
