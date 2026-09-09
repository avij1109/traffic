from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VehicleType(str, Enum):
    CAR = "CAR"
    SUV = "SUV"
    MOTORCYCLE = "MOTORCYCLE"
    AUTO = "AUTO"
    BUS = "BUS"
    TRUCK = "TRUCK"


class BoundingBox(BaseModel):
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)


class VehicleDetection(BaseModel):
    bbox: BoundingBox
    vehicle_type: VehicleType
    confidence: float = Field(..., ge=0.0, le=1.0)
    color: str
    make_model: Optional[str] = None


class ANPRResult(BaseModel):
    plate_text: str
    raw_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    plate_bbox: Optional[BoundingBox] = None
    character_confidences: List[float] = Field(default_factory=list)


class ReIDEmbedding(BaseModel):
    vector: List[float] = Field(default_factory=list)
    signature_hash: str
    similarity_threshold: float = 0.85


class UnifiedDetectionPayload(BaseModel):
    id: str
    camera_id: str
    timestamp: datetime
    detection: VehicleDetection
    anpr: ANPRResult
    reid: ReIDEmbedding
    fused_confidence: float
    estimated_speed_kmh: Optional[float] = None
    crop_svg: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Abstract Contracts for AI Models
class IVehicleDetector(ABC):
    """Abstract interface for vehicle detection models (e.g. YOLOv8, YOLOv11)."""
    @abstractmethod
    async def detect(self, frame_bytes: bytes) -> List[VehicleDetection]:
        pass


class IANPRProvider(ABC):
    """Abstract interface for license plate recognition (e.g. PaddleOCR, EasyOCR)."""
    @abstractmethod
    async def recognize(self, frame_bytes: bytes, plate_crop: Optional[bytes] = None) -> ANPRResult:
        pass


class IReIDProvider(ABC):
    """Abstract interface for vehicle re-identification (e.g. TorchReID, OSNet)."""
    @abstractmethod
    async def extract_features(self, vehicle_crop: bytes) -> ReIDEmbedding:
        pass


class IConfidenceFusion(ABC):
    """Abstract interface for multi-modal confidence fusion."""
    @abstractmethod
    def fuse(self, detection: VehicleDetection, anpr: ANPRResult, reid: Optional[ReIDEmbedding] = None) -> float:
        pass


class IVisionProvider(ABC):
    """Unified vision pipeline interface coordinating detector, OCR, and Re-ID."""
    @abstractmethod
    async def process_frame(self, camera_id: str, frame_bytes: bytes) -> List[UnifiedDetectionPayload]:
        pass

    @abstractmethod
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
        pass
