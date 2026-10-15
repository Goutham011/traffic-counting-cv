"""
Configuration for the traffic counting system.
Centralizes settings for detection, tracking, counting line, and output paths.
Easy to extend for real-time feeds (e.g., swap video_path for stream URL).
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Tuple, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Subdirectories for organized output
ANNOTATED_VIDEO_DIR = OUTPUT_DIR / "annotated_videos"
ANALYTICS_DIR = OUTPUT_DIR / "analytics"
REPORT_DIR = OUTPUT_DIR / "reports"
DATA_DIR = OUTPUT_DIR / "data"

for d in (ANNOTATED_VIDEO_DIR, ANALYTICS_DIR, REPORT_DIR, DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# YOLO and detection
# ---------------------------------------------------------------------------
@dataclass
class DetectionConfig:
    """YOLO model and detection parameters."""
    model_name: str = "yolov8n.pt"  # n=nano, s=small, m=medium, l=large
    # Lower threshold (e.g. 0.35) helps detect smaller/distant vehicles like motorcycles
    confidence_threshold: float = 0.35
    # Lower NMS IOU (e.g. 0.4) keeps more overlapping boxes as separate detections
    iou_threshold: float = 0.4
    # COCO class IDs: 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
    vehicle_class_ids: List[int] = field(
        default_factory=lambda: [1, 2, 3, 5, 7]  # bicycle, car, motorcycle, bus, truck
    )
    # Map class ID to category name for reporting
    class_id_to_category: dict = field(default_factory=lambda: {
        1: "bicycle",
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck",
    })


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
# Custom tracker config that keeps overlapping vehicles as separate tracks (higher match_thresh)
TRACKER_OVERLAP_YAML = (PROJECT_ROOT / "trackers" / "bytetrack_overlap.yaml").resolve()


@dataclass
class TrackingConfig:
    """Object tracking parameters (used by YOLO tracker)."""
    # Use custom bytetrack_overlap.yaml so overlapping vehicles get separate IDs
    tracker_type: str = field(default_factory=lambda: str(TRACKER_OVERLAP_YAML))
    persist: bool = True  # persist tracks across frames


# ---------------------------------------------------------------------------
# Counting line
# ---------------------------------------------------------------------------
@dataclass
class CountingLineConfig:
    """
    Virtual counting line: vehicles are counted when they cross this line.
    Line is defined by two points (x1, y1) -> (x2, y2).
    Use relative coords (0-1) for portability, or absolute pixels.
    """
    # Relative coordinates (0-1) of line start and end; applied to frame size
    line_start_rel: Tuple[float, float] = (0.0, 0.72)   # left, 72% down (lower in frame)
    line_end_rel: Tuple[float, float] = (1.0, 0.72)     # right, 72% down
    # Direction: "up" = count when centroid crosses upward, "down" = downward, "both" = either way
    count_direction: str = "both"  # "up", "down", or "both" (both = count every crossing)
    # Minimum frames the track must exist before counting (reduces noise)
    min_track_frames: int = 2


# ---------------------------------------------------------------------------
# Video I/O
# ---------------------------------------------------------------------------
@dataclass
class VideoConfig:
    """Input/output video settings."""
    # Input: path to video file or URL (for future real-time: rtsp://...)
    video_path: str = ""
    # Output annotated video
    output_video_name: str = "annotated_traffic"
    output_fps: float = 0  # 0 = same as input
    # Use MJPG (Motion JPEG) codec - universally supported, works with all OpenCV builds
    # Produces larger files but guaranteed compatibility with all media players
    # Alternative: "XVID" for smaller files if MJPG produces too large videos
    output_fourcc: str = "MJPG"


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@dataclass
class AnalyticsConfig:
    """Time windows and aggregation for statistics."""
    # Time window (seconds) for density-over-time aggregation
    density_window_seconds: float = 60.0
    # Generate time-series of counts per window
    use_time_windows: bool = True


# ---------------------------------------------------------------------------
# Single config container (optional, for passing one object)
# ---------------------------------------------------------------------------
@dataclass
class TrafficCountingConfig:
    """Full configuration for the pipeline."""
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    counting_line: CountingLineConfig = field(default_factory=CountingLineConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    analytics: AnalyticsConfig = field(default_factory=AnalyticsConfig)

    @classmethod
    def from_video_path(cls, video_path: str, **overrides) -> "TrafficCountingConfig":
        c = cls()
        c.video.video_path = video_path
        for key, value in overrides.items():
            if hasattr(c, key):
                setattr(c, key, value)
        return c
