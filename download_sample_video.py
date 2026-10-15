"""
Optional: Download a short sample traffic video for testing.
Uses a direct link to a small clip (e.g. from a public domain / free use source).
If the URL is unavailable, use any local traffic video with --video path.
"""

import sys
from pathlib import Path

# Sample: Pexels free stock video (traffic). Replace with any direct .mp4 URL.
# This is an example; Pexels/Pixabay URLs may require handling redirects.
SAMPLE_VIDEO_URL = (
    "https://www.pexels.com/download/video/3054155/"
    # Alternative: use a direct .mp4 link from a CDN if you have one
)
# Fallback: user provides their own file
SAMPLE_LOCAL = Path(__file__).parent / "sample_traffic.mp4"


def download_sample():
    try:
        import urllib.request
        # Example: use a known small sample (replace URL with a direct .mp4)
        # Many free video sites don't offer direct .mp4; user may need to download manually
        out = Path(__file__).parent / "sample_traffic.mp4"
        print("To use a sample video:")
        print("  1. Download a short traffic clip from Pexels or Pixabay (search 'traffic').")
        print("  2. Save it as 'sample_traffic.mp4' in this folder, or")
        print("  3. Run: python main.py --video /path/to/your/video.mp4")
        print(f"  Expected path for script: {out}")
        return None
    except Exception as e:
        print("Download failed:", e)
        return None


if __name__ == "__main__":
    download_sample()
