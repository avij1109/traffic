from providers.real.yolo_provider import YOLOv8VehicleDetector
from providers.real.paddle_provider import PaddleOCRProvider
from providers.real.reid_provider import TorchReIDProvider
from providers.real.yolo_paddle_provider import YoloPaddleVisionProvider

__all__ = [
    "YOLOv8VehicleDetector",
    "PaddleOCRProvider",
    "TorchReIDProvider",
    "YoloPaddleVisionProvider",
]
