# AI Model Integration Guide (For ML / Vision Teammate)

This guide documents how the ML teammate can plug in trained models (**YOLOv8/v11**, **PaddleOCR**, and **TorchReID**) into the surveillance platform once ready.

---

## 1. Provider Contract Architecture

The entire surveillance engine interacts with computer vision exclusively through abstract interfaces located in `providers/base.py`:
- `IVisionProvider`
- `IANPRProvider`
- `IReIDProvider`

The backend does **not** make direct calls to PyTorch, ONNX, or OpenCV. It only consumes standard `UnifiedDetectionPayload` data structures.

---

## 2. Interface Contract (`providers/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

class VehicleClass(BaseModel):
    label: str               # "CAR", "SUV", "TRUCK", "BUS", "MOTORCYCLE"
    confidence: float

class RawDetection(BaseModel):
    bbox: BoundingBox
    vehicle: VehicleClass
    crop_base64: Optional[str] = None

class ANPRResult(BaseModel):
    plate_text: str          # Normalized plate, e.g. "DL01AB1234"
    raw_text: str            # Raw OCR text before regex normalization
    confidence: float        # 0.0 to 1.0
    plate_bbox: Optional[BoundingBox] = None

class ReIDEmbedding(BaseModel):
    vector: List[float]      # L2-normalized 512-dim feature embedding
    fingerprint: str         # Hex representation or hash for rapid lookup

class UnifiedDetectionPayload(BaseModel):
    camera_id: str
    timestamp: datetime
    detection: RawDetection
    anpr: ANPRResult
    reid: ReIDEmbedding
    speed_estimate_kmh: Optional[float] = None

class IVisionProvider(ABC):
    @abstractmethod
    async def process_frame(
        self, 
        camera_id: str, 
        timestamp: datetime, 
        frame_bytes: bytes
    ) -> List[UnifiedDetectionPayload]:
        """Ingest raw camera frame and output detections with OCR and ReID embeddings."""
        pass
```

---

## 3. How to Plug In Real Models

When your models are trained and ready:
1. Place model weights in `providers/weights/` (e.g. `yolov8n.pt`, `reid_osnet.pth`).
2. Implement your provider in `providers/real/yolo_paddle_provider.py` inheriting from `IVisionProvider`.
3. In `backend/app/core/config.py`, change:
   ```python
   VISION_PROVIDER = "providers.real.yolo_paddle_provider.YoloPaddleVisionProvider"
   ```
4. No changes needed to:
   - Database schemas
   - WebSocket streaming
   - Anomaly detection algorithms
   - Multi-camera tracking
   - Frontend command center
