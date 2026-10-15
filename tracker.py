"""
Line-crossing logic and counting.
Assigns unique IDs via the detector's tracker; counts each vehicle only once
when its centroid crosses the virtual counting line in the configured direction.
"""

from typing import List, Set, Tuple, Optional, Dict
from dataclasses import dataclass

from config import CountingLineConfig
from detector import DetectedObject


def _normalize_category(name: Optional[str]) -> str:
    """Normalize category for consistent aggregation (e.g. 'bus', 'Bus', 'BUS' -> 'Bus')."""
    if not name or not str(name).strip():
        return "unknown"
    return str(name).strip().title()


@dataclass
class CountingLine:
    """Screen-space counting line from (x1,y1) to (x2,y2)."""
    x1: float
    y1: float
    x2: float
    y2: float

    @classmethod
    def from_config(cls, cfg: CountingLineConfig, frame_width: int, frame_height: int) -> "CountingLine":
        sx, sy = cfg.line_start_rel
        ex, ey = cfg.line_end_rel
        return cls(
            x1=sx * frame_width,
            y1=sy * frame_height,
            x2=ex * frame_width,
            y2=ey * frame_height,
        )

    def side_of_line(self, px: float, py: float) -> float:
        """
        Signed value: positive = one side, negative = other, ~0 = on line.
        Uses cross product (line vector x point vector).
        """
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        return (self.x2 - self.x1) * (py - self.y1) - (self.y2 - self.y1) * (px - self.x1)


@dataclass
class CrossEvent:
    """Record of a vehicle crossing the counting line."""
    track_id: int
    category: str
    frame_index: int
    timestamp_sec: float


class LineCrossingCounter:
    """
    Tracks which vehicle IDs have already been counted and detects new crossings.
    Uses centroid position relative to the counting line and direction.
    """

    def __init__(self, config: CountingLineConfig, frame_width: int, frame_height: int):
        self.config = config
        self.line = CountingLine.from_config(config, frame_width, frame_height)
        self.counted_ids: Set[int] = set()
        self.all_track_ids_seen: Set[int] = set()  # every track ID that appeared (for report)
        self.track_id_to_category: Dict[int, str] = {}  # track_id -> category (last seen) for all detected
        self.track_id_to_category_counts: Dict[int, Dict[str, int]] = {}  # track_id -> {category: frame_count} for majority vote
        self.track_previous_side: dict[int, float] = {}  # track_id -> last side value
        self.track_frame_count: dict[int, int] = {}  # track_id -> frames seen
        self.cross_events: List[CrossEvent] = []

    def update(
        self,
        frame_index: int,
        timestamp_sec: float,
        detected_objects: List[DetectedObject],
    ) -> List[CrossEvent]:
        """
        Update state with new detections; return list of new crossing events this frame.
        """
        new_events: List[CrossEvent] = []

        for obj in detected_objects:
            if obj.track_id is None:
                continue
            tid = obj.track_id
            self.all_track_ids_seen.add(tid)
            self.track_id_to_category[tid] = obj.category_name  # keep category for every detected vehicle
            # Accumulate category counts per track for majority vote (normalized key so bus/Bus merge)
            if tid not in self.track_id_to_category_counts:
                self.track_id_to_category_counts[tid] = {}
            key = _normalize_category(obj.category_name)
            self.track_id_to_category_counts[tid][key] = (
                self.track_id_to_category_counts[tid].get(key, 0) + 1
            )
            cx, cy = obj.centroid
            side = self.line.side_of_line(cx, cy)

            self.track_frame_count[tid] = self.track_frame_count.get(tid, 0) + 1
            if self.track_frame_count[tid] < self.config.min_track_frames:
                self.track_previous_side[tid] = side
                continue

            prev_side = self.track_previous_side.get(tid)
            self.track_previous_side[tid] = side

            if prev_side is None:
                continue
            if tid in self.counted_ids:
                continue

            # Crossing: sign change. side > 0 = below line, side < 0 = above line (for horizontal line left-to-right).
            direction = self.config.count_direction
            crossed = False
            if direction == "both":
                # Count crossing in either direction
                crossed = (prev_side < 0 and side >= 0) or (prev_side > 0 and side <= 0)
            elif direction == "down":
                # Down = moving downward in image (increasing y) = from above line to below line
                crossed = prev_side < 0 and side >= 0
            elif direction == "up":
                # Up = moving upward in image (decreasing y) = from below line to above line
                crossed = prev_side > 0 and side <= 0

            if crossed:
                self.counted_ids.add(tid)
                # Use majority-vote category (most seen over track lifetime) for stable per-category counts
                cat_counts = self.track_id_to_category_counts.get(tid, {})
                category = (
                    max(cat_counts, key=cat_counts.get) if cat_counts else _normalize_category(obj.category_name)
                )
                evt = CrossEvent(
                    track_id=tid,
                    category=category,
                    frame_index=frame_index,
                    timestamp_sec=timestamp_sec,
                )
                self.cross_events.append(evt)
                new_events.append(evt)

        return new_events

    def total_count(self) -> int:
        return len(self.counted_ids)

    def get_events(self) -> List[CrossEvent]:
        return list(self.cross_events)

    def get_detected_category_counts(self) -> Dict[str, int]:
        """Category breakdown for ALL detected vehicles (every green box)."""
        counts: Dict[str, int] = {}
        for tid in self.all_track_ids_seen:
            cat = _normalize_category(self.track_id_to_category.get(tid, "unknown"))
            counts[cat] = counts.get(cat, 0) + 1
        return counts
