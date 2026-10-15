"""
Traffic analytics: aggregate counts by category, time windows, and density over time.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from tracker import CrossEvent
from config import AnalyticsConfig


@dataclass
class TrafficStats:
    """Aggregated traffic statistics."""
    total_count: int = 0
    category_counts: Dict[str, int] = field(default_factory=dict)
    events: List[CrossEvent] = field(default_factory=list)
    density_over_time: pd.DataFrame = field(default_factory=pd.DataFrame)
    counts_per_window: pd.DataFrame = field(default_factory=pd.DataFrame)


def compute_stats(
    cross_events: List[CrossEvent],
    config: Optional[AnalyticsConfig] = None,
    video_duration_sec: float = 0,
) -> TrafficStats:
    """
    Compute total count, category distribution, and optional time-based aggregates.
    """
    config = config or AnalyticsConfig()
    stats = TrafficStats()
    stats.events = list(cross_events)
    stats.total_count = len(cross_events)

    # Category-wise counts (normalize key so "bus"/"Bus" merge into one count)
    for evt in cross_events:
        key = (evt.category or "unknown").strip().title()
        stats.category_counts[key] = stats.category_counts.get(key, 0) + 1

    if not cross_events:
        return stats

    df = pd.DataFrame([
        {"timestamp_sec": e.timestamp_sec, "category": e.category, "track_id": e.track_id}
        for e in cross_events
    ])

    # Density over time: count per time window
    if config.use_time_windows and not df.empty:
        window_sec = config.density_window_seconds
        t_max = df["timestamp_sec"].max()
        if video_duration_sec > 0:
            t_max = max(t_max, video_duration_sec)
        bins = np.arange(0, t_max + window_sec, window_sec)
        win_idx = np.searchsorted(bins, df["timestamp_sec"], side="right") - 1
        df["window"] = np.clip(win_idx, 0, len(bins) - 1)
        df["window_start"] = bins[df["window"].values] if len(bins) > 0 else 0

        counts_per_window = df.groupby("window_start").size().reset_index(name="count")
        counts_per_window.columns = ["time_window_start_sec", "vehicle_count"]
        stats.counts_per_window = counts_per_window

        # Per-window per-category
        by_window_cat = df.groupby(["window_start", "category"]).size().reset_index(name="count")
        stats.density_over_time = by_window_cat

    return stats
