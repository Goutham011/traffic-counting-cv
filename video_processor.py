"""
Main video processing pipeline.
Reads video, runs detection + tracking, line-crossing counting, and optionally
writes annotated video and collects statistics for analytics.
"""

from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
import cv2
import numpy as np

from config import TrafficCountingConfig
from detector import VehicleDetector, DetectedObject
from tracker import LineCrossingCounter, CrossEvent


@dataclass
class FrameResult:
    """Result for one processed frame."""
    frame_index: int
    timestamp_sec: float
    frame: np.ndarray
    detections: List[DetectedObject]
    new_crossings: List[CrossEvent]
    total_count_so_far: int


class VideoProcessor:
    """
    Processes a video file (or in future: stream) through detection, tracking,
    and counting. Can write annotated video and collect time-series data.
    """

    def __init__(self, config: TrafficCountingConfig):
        self.config = config
        self.detector = VehicleDetector(
            detection_config=config.detection,
            tracking_config=config.tracking,
        )
        self.counter: Optional[LineCrossingCounter] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._writer: Optional[cv2.VideoWriter] = None
        self._fps: float = 25.0
        self._width: int = 0
        self._height: int = 0
        self._total_frames: int = 0
        self._all_cross_events: List[CrossEvent] = []

    def open(self, video_path: str) -> bool:
        """Open video file or stream. Returns True on success."""
        path = Path(video_path) if video_path else None
        if not video_path:
            return False
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            return False
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.counter = LineCrossingCounter(
            self.config.counting_line,
            self._width,
            self._height,
        )
        return True

    def close(self):
        if self._cap:
            self._cap.release()
            self._cap = None
        if self._writer:
            self._writer.release()
            self._writer = None

    def start_annotated_writer(
        self,
        output_path: str,
        fps: Optional[float] = None,
        fourcc: Optional[str] = None,
    ) -> bool:
        """Start writing annotated frames to output_path."""
        fps = fps or self.config.video.output_fps or self._fps
        fourcc_str = fourcc or self.config.video.output_fourcc
        fourcc_code = cv2.VideoWriter_fourcc(*fourcc_str)
        self._writer = cv2.VideoWriter(
            output_path,
            fourcc_code,
            fps,
            (self._width, self._height),
        )
        return self._writer.isOpened()

    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp_sec: float,
        draw_callback: Optional[Callable[[np.ndarray, FrameResult], None]] = None,
    ) -> FrameResult:
        """
        Process one frame: detect, track, count crossings, optionally draw.
        draw_callback(frame, result) can be used to add annotations.
        """
        detections = self.detector.detect(frame, track=True)
        new_crossings = self.counter.update(frame_index, timestamp_sec, detections)
        self._all_cross_events.extend(new_crossings)
        total = self.counter.total_count()

        result = FrameResult(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            frame=frame.copy(),
            detections=detections,
            new_crossings=new_crossings,
            total_count_so_far=total,
        )

        if draw_callback:
            draw_callback(result.frame, result)
        if self._writer and self._writer.isOpened():
            self._writer.write(result.frame)

        return result

    def run(
        self,
        progress_callback: Optional[Callable[[int, int, FrameResult], None]] = None,
        draw_callback: Optional[Callable[[np.ndarray, FrameResult], None]] = None,
        max_frames: Optional[int] = None,
    ) -> List[CrossEvent]:
        """
        Run full video processing. Optionally report progress and draw.
        Returns list of all crossing events.
        """
        if not self._cap or not self._cap.isOpened() or not self.counter:
            return []

        frame_index = 0
        self._all_cross_events.clear()
        total = max_frames or self._total_frames
        if total <= 0:
            total = 0  # unknown length

        while True:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                break
            ts = frame_index / self._fps if self._fps > 0 else 0
            result = self.process_frame(frame, frame_index, ts, draw_callback=draw_callback)
            if progress_callback:
                stop = progress_callback(frame_index, total, result)
                if stop is True:
                    break
            frame_index += 1
            if max_frames is not None and frame_index >= max_frames:
                break

        return list(self._all_cross_events)

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def total_frames(self) -> int:
        return self._total_frames
