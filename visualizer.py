"""
Visualization: draw bounding boxes, IDs, counting line, and on-screen stats;
generate graphs and dashboard figures.
"""

from pathlib import Path
from typing import List, Optional, Dict
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from config import CountingLineConfig, OUTPUT_DIR, ANALYTICS_DIR
from detector import DetectedObject
from video_processor import FrameResult
from tracker import LineCrossingCounter, CrossEvent
from analytics import TrafficStats


# Colors (BGR) and labels
COLORS = {
    "bicycle": (0, 255, 255),   # yellow
    "car": (0, 255, 0),         # green
    "motorcycle": (255, 165, 0),  # orange (motorbike same)
    "motorbike": (255, 165, 0),
    "bus": (255, 0, 0),         # blue
    "truck": (128, 0, 255),     # purple
}
DEFAULT_COLOR = (200, 200, 200)


def get_color(category: str) -> tuple:
    return COLORS.get(category.lower(), DEFAULT_COLOR)


def draw_detections(frame: np.ndarray, detections: List[DetectedObject], line: Optional[LineCrossingCounter] = None):
    """Draw bounding boxes and track IDs on frame."""
    for obj in detections:
        x1, y1, x2, y2 = map(int, obj.xyxy)
        color = get_color(obj.category_name)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"#{obj.track_id}" if obj.track_id is not None else obj.category_name
        cv2.putText(
            frame, label, (x1, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )


def draw_counting_line(frame: np.ndarray, line: LineCrossingCounter):
    """Draw the virtual counting line."""
    L = line.line
    cv2.line(frame, (int(L.x1), int(L.y1)), (int(L.x2), int(L.y2)), (0, 255, 255), 2)
    cv2.putText(
        frame, "Counting line", (int(L.x1), int(L.y1) - 6),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA,
    )


def draw_on_frame(frame: np.ndarray, result: FrameResult, counter: Optional[LineCrossingCounter] = None):
    """Full overlay: boxes, IDs, counting line, and total count."""
    draw_detections(frame, result.detections, counter)
    if counter:
        draw_counting_line(frame, counter)
    # On-screen stats
    cv2.putText(
        frame, f"Total: {result.total_count_so_far}", (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"Time: {result.timestamp_sec:.1f}s", (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA,
    )


def plot_category_distribution(
    stats: TrafficStats,
    save_path: Optional[Path] = None,
    category_counts_override: Optional[Dict[str, int]] = None,
) -> Path:
    """Bar chart of category-wise vehicle count. Use category_counts_override for all detected (green boxes)."""
    counts_dict = category_counts_override if category_counts_override else stats.category_counts
    if not counts_dict:
        return save_path or ANALYTICS_DIR / "category_distribution.png"
    path = save_path or ANALYTICS_DIR / "category_distribution.png"
    fig, ax = plt.subplots(figsize=(8, 5), facecolor="white")
    ax.set_facecolor("white")
    cats = list(counts_dict.keys())
    counts = list(counts_dict.values())
    colors = [get_color(c) for c in cats]
    colors_rgb = [(c[2] / 255, c[1] / 255, c[0] / 255) for c in colors]
    bars = ax.bar(cats, counts, color=colors_rgb, edgecolor="gray", linewidth=0.8)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_xlabel("Category", fontsize=12)
    title = "Vehicle Count by Category (all detected)" if category_counts_override else "Vehicle Count by Category (counted)"
    ax.set_title(title, fontsize=14, weight="bold")
    # Value labels on top of each bar
    for bar, val in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(int(val)),
                ha="center", va="bottom", fontsize=11, weight="bold")
    ax.tick_params(axis="both", labelsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def plot_density_over_time(stats: TrafficStats, save_path: Optional[Path] = None) -> Optional[Path]:
    """Bar plot of vehicle count per time window."""
    if stats.counts_per_window.empty:
        return None
    path = save_path or ANALYTICS_DIR / "density_over_time.png"
    df = stats.counts_per_window
    # Ensure expected columns exist
    if "time_window_start_sec" not in df.columns or "vehicle_count" not in df.columns:
        return None
    fig, ax = plt.subplots(figsize=(12, 6), facecolor="white")
    ax.set_facecolor("white")
    x = df["time_window_start_sec"].values
    y = df["vehicle_count"].values
    if len(x) > 1:
        spacing = np.diff(x)
        w = float(spacing.min()) * 0.85 if len(spacing) > 0 and spacing.min() > 0 else 30
    else:
        w = 30
    w = max(w, 1)
    bars = ax.bar(x, y, width=w, color="#3b82f6", alpha=0.8, edgecolor="#1e40af", linewidth=1)
    ax.set_xlabel("Time (seconds)", fontsize=12)
    ax.set_ylabel("Vehicle count", fontsize=12)
    ax.set_title("Traffic density over time", fontsize=14, weight="bold")
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")
    ax.set_axisbelow(True)
    # Integer x-axis for time
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for bar, val in zip(bars, y):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(int(val)),
                    ha="center", va="bottom", fontsize=9, weight="bold")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def plot_category_over_time(stats: TrafficStats, save_path: Optional[Path] = None) -> Optional[Path]:
    """Stacked bar chart: count per time window per category."""
    if stats.density_over_time.empty:
        return None
    path = save_path or ANALYTICS_DIR / "category_over_time.png"
    df = stats.density_over_time
    time_col = "window_start" if "window_start" in df.columns else "time_window_start_sec"
    if time_col not in df.columns or "category" not in df.columns or "count" not in df.columns:
        return None
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")
    ax.set_facecolor("white")
    pivot = df.pivot(index=time_col, columns="category", values="count").fillna(0)
    pivot.plot(kind="bar", stacked=True, ax=ax, width=0.8, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Time window (sec)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("Category-wise traffic over time (counted)", fontsize=14, weight="bold")
    ax.legend(title="Category", fontsize=9)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def generate_dashboard(
    stats: TrafficStats,
    output_dir: Optional[Path] = None,
    detected_category_counts: Optional[Dict[str, int]] = None,
) -> List[Path]:
    """Generate all analytics plots. Use detected_category_counts so chart matches all green boxes."""
    output_dir = output_dir or ANALYTICS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    p1 = plot_category_distribution(
        stats,
        output_dir / "category_distribution.png",
        category_counts_override=detected_category_counts,
    )
    paths.append(p1)
    p2 = plot_density_over_time(stats, output_dir / "density_over_time.png")
    if p2:
        paths.append(p2)
    p3 = plot_category_over_time(stats, output_dir / "category_over_time.png")
    if p3:
        paths.append(p3)
    return paths
