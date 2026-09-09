import uuid
from datetime import datetime, timezone
from typing import List, Optional

from providers.base import (
    IVisionProvider,
    IVehicleDetector,
    IANPRProvider,
    IReIDProvider,
    IConfidenceFusion,
    UnifiedDetectionPayload,
    VehicleDetection,
    VehicleType,
    BoundingBox,
)
from providers.confidence_fusion import WeightedConfidenceFusion
from providers.real.yolo_provider import YOLOv8VehicleDetector
from providers.real.paddle_provider import PaddleOCRProvider
from providers.real.reid_provider import TorchReIDProvider


class YoloPaddleVisionProvider(IVisionProvider):
    """Production composite vision provider combining YOLO vehicle detection,
    PaddleOCR plate recognition, and TorchReID feature extraction.
    Adheres strictly to the IVisionProvider abstraction boundary.
    """

    def __init__(
        self,
        detector: Optional[IVehicleDetector] = None,
        anpr: Optional[IANPRProvider] = None,
        reid: Optional[IReIDProvider] = None,
        fusion: Optional[IConfidenceFusion] = None,
    ):
        self.detector = detector or YOLOv8VehicleDetector()
        self.anpr = anpr or PaddleOCRProvider()
        self.reid = reid or TorchReIDProvider()
        self.fusion = fusion or WeightedConfidenceFusion()

    async def process_frame(self, camera_id: str, frame_bytes: bytes) -> List[UnifiedDetectionPayload]:
        """Runs the full perception pipeline on a camera frame:
        Detection -> ANPR -> Re-ID -> Confidence Fusion.
        """
        now = datetime.now(timezone.utc)
        detections = await self.detector.detect(frame_bytes)
        payloads: List[UnifiedDetectionPayload] = []

        for det in detections:
            det_id = f"det_{uuid.uuid4().hex[:12]}"
            anpr_result = await self.anpr.recognize(frame_bytes)
            reid_result = await self.reid.extract_features(frame_bytes)
            fused_conf = self.fusion.fuse(det, anpr_result, reid_result)

            payloads.append(
                UnifiedDetectionPayload(
                    id=det_id,
                    camera_id=camera_id,
                    timestamp=now,
                    detection=det,
                    anpr=anpr_result,
                    reid=reid_result,
                    fused_confidence=fused_conf,
                    metadata={"source": "YOLO_PADDLE_REAL_PIPELINE"}
                )
            )

        return payloads

    async def generate_simulated_detection(
        self,
        camera_id: str,
        plate_number: str,
        vehicle_type: VehicleType,
        color: str,
        make_model: str,
        speed_kmh: float,
        ocr_noise: bool = False
    ) -> UnifiedDetectionPayload:
        """Simulated detection bridge for fallback or hybrid validation."""
        now = datetime.now(timezone.utc)
        det_id = f"det_{uuid.uuid4().hex[:12]}"

        if isinstance(vehicle_type, str):
            try:
                v_type = VehicleType(vehicle_type.upper())
            except ValueError:
                v_type = VehicleType.CAR
        else:
            v_type = vehicle_type

        bbox = BoundingBox(x_min=0.20, y_min=0.25, x_max=0.75, y_max=0.80)
        det = VehicleDetection(
            bbox=bbox,
            vehicle_type=v_type,
            confidence=0.95,
            color=color,
            make_model=make_model
        )

        anpr_result = await self.anpr.recognize(b"")
        anpr_result.plate_text = plate_number
        anpr_result.raw_text = plate_number

        reid_result = await self.reid.extract_features(plate_number.encode("utf-8"))
        fused = self.fusion.fuse(det, anpr_result, reid_result)

        return UnifiedDetectionPayload(
            id=det_id,
            camera_id=camera_id,
            timestamp=now,
            detection=det,
            anpr=anpr_result,
            reid=reid_result,
            fused_confidence=fused,
            estimated_speed_kmh=round(speed_kmh, 1),
            metadata={"source": "YOLO_PADDLE_SIM_FALLBACK"}
        )
