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
    ANPRResult,
    ReIDEmbedding,
)
from providers.confidence_fusion import WeightedConfidenceFusion, compute_cosine_similarity
from providers.simulator_provider import SimulatorVisionProvider

__all__ = [
    "IVisionProvider",
    "IVehicleDetector",
    "IANPRProvider",
    "IReIDProvider",
    "IConfidenceFusion",
    "UnifiedDetectionPayload",
    "VehicleDetection",
    "VehicleType",
    "BoundingBox",
    "ANPRResult",
    "ReIDEmbedding",
    "WeightedConfidenceFusion",
    "compute_cosine_similarity",
    "SimulatorVisionProvider",
]
