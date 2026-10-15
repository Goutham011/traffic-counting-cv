"""
Vehicle detection module using YOLO (Ultralytics).
Detects and optionally tracks vehicles (car, motorcycle, bus, truck) in video frames.
"""

from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from config import DetectionConfig, TrackingConfig


@dataclass
class DetectedObject:
    """Single detected/tracked object."""
    xyxy: Tuple[float, float, float, float]  # bbox: x1, y1, x2, y2
    confidence: float
    class_id: int
    track_id: Optional[int] = None  # Set when tracking is enabled
    category_name: str = ""

    @property
    def centroid(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2, (y1 + y2) / 2)


class VehicleDetector:
    """
    Wraps Ultralytics YOLO for vehicle detection and tracking.
    Filters detections to vehicle classes only.
    """

    def __init__(
        self,
        detection_config: Optional[DetectionConfig] = None,
        tracking_config: Optional[TrackingConfig] = None,
    ):
        self.det_cfg = detection_config or DetectionConfig()
        self.track_cfg = tracking_config or TrackingConfig()
        self._model = None
        self._category_map = self.det_cfg.class_id_to_category

    def _get_model(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.det_cfg.model_name)
        return self._model

    def _get_vehicle_class_ids(self):
        """Vehicle class IDs from config, plus any from model.names matching vehicle keywords."""
        model = self._get_model()
        ids = set(self.det_cfg.vehicle_class_ids)
        # Include any class whose name looks like a vehicle (covers motorcycle/motorbike etc.)
        vehicle_keywords = ("car", "motorcycle", "motorbike", "bicycle", "bike", "bus", "truck")
        if hasattr(model, "names") and model.names is not None:
            names = model.names
            items = names.items() if isinstance(names, dict) else enumerate(names)
            for cls_id, name in items:
                if name and any(kw in str(name).lower() for kw in vehicle_keywords):
                    ids.add(int(cls_id))
        return ids

    def detect(
        self,
        frame: np.ndarray,
        track: bool = True,
    ) -> List[DetectedObject]:
        """
        Run detection (and optionally tracking) on one frame.
        Returns list of DetectedObject filtered to vehicle classes.
        """
        model = self._get_model()
        conf = self.det_cfg.confidence_threshold
        iou = self.det_cfg.iou_threshold
        vehicle_ids = self._get_vehicle_class_ids()

        # max_det: allow many detections per frame (default can be low in some setups)
        max_det = 500
        if track:
            results = model.track(
                frame,
                conf=conf,
                iou=iou,
                persist=self.track_cfg.persist,
                tracker=self.track_cfg.tracker_type,
                verbose=False,
                max_det=max_det,
            )
        else:
            results = model.predict(
                frame,
                conf=conf,
                iou=iou,
                verbose=False,
                max_det=max_det,
            )

        objects: List[DetectedObject] = []
        if not results:
            return objects

        r = results[0]
        boxes = r.boxes
        if boxes is None:
            return objects

        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        n = len(class_ids)
        # Track IDs: same length as boxes when tracking; safe index
        if boxes.id is not None:
            id_arr = boxes.id.cpu().numpy()
            track_ids = id_arr if len(id_arr) >= n else list(id_arr) + [None] * (n - len(id_arr))
        else:
            track_ids = [None] * n

        for i in range(n):
            cls_id = int(class_ids[i])
            if cls_id not in vehicle_ids:
                continue
            cat_name = self._category_map.get(cls_id, f"class_{cls_id}")
            tid = int(track_ids[i]) if track_ids[i] is not None else None
            obj = DetectedObject(
                xyxy=tuple(map(float, xyxy[i])),
                confidence=float(confidences[i]),
                class_id=cls_id,
                track_id=tid,
                category_name=cat_name,
            )
            objects.append(obj)

        return objects
