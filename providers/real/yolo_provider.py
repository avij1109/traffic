import os
from typing import List, Optional
from providers.base import IVehicleDetector, VehicleDetection, VehicleType, BoundingBox


class YOLOv8VehicleDetector(IVehicleDetector):
    """Production drop-in stub for YOLOv8/v11 vehicle detection.
    The ML teammate loads weights here (e.g. from ultralytics import YOLO).
    Avoids hard imports of torch/ultralytics to prevent framework leakage.
    """

    CLASS_MAPPING = {
        0: VehicleType.CAR,
        1: VehicleType.SUV,
        2: VehicleType.BUS,
        3: VehicleType.TRUCK,
        4: VehicleType.MOTORCYCLE,
        5: VehicleType.AUTO,
    }

    def __init__(self, weights_path: str = "providers/weights/yolov8n.pt", device: str = "cpu"):
        self.weights_path = weights_path
        self.device = device
        self.model = None  # Lazily loaded when weights are present
        self._is_loaded = False

    def is_model_loaded(self) -> bool:
        return self._is_loaded and self.model is not None

    def load_model(self) -> bool:
        """Loads weights lazily if ultralytics is installed and weights file exists."""
        if self._is_loaded:
            return True
        if os.path.exists(self.weights_path):
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.weights_path)
                self._is_loaded = True
                return True
            except (ImportError, Exception):
                self.model = None
                return False
        return False

    async def detect(self, frame_bytes: bytes) -> List[VehicleDetection]:
        """Runs object detection inference on raw frame bytes.
        Returns detected vehicles with normalized bounding boxes and confidences.
        """
        if not self._is_loaded:
            self.load_model()

        if self.model is None or not frame_bytes:
            # Fallback stub for unit testing and offline development
            return []

        # Production execution path (when teammate provides weights and ultralytics):
        # import numpy as np
        # import cv2
        # nparr = np.frombuffer(frame_bytes, np.uint8)
        # img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # results = self.model(img, device=self.device)
        # Parse detections...
        return []
