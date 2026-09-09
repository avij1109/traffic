import base64
import hashlib
import random
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from providers.base import (
    IVisionProvider,
    UnifiedDetectionPayload,
    VehicleDetection,
    VehicleType,
    BoundingBox,
    ANPRResult,
    ReIDEmbedding,
)
from providers.confidence_fusion import WeightedConfidenceFusion


class SimulatorVisionProvider(IVisionProvider):
    """Realistic mock implementation of the Vision Provider interface.
    Generates realistic detection bounding boxes, OCR confidence scores,
    confusion mutations, normalized Re-ID feature vectors, and HSRP SVG crops.
    """

    OCR_CONFUSIONS: Dict[str, List[str]] = {
        '0': ['O', 'D', 'Q'],
        'O': ['0', 'Q', 'D'],
        'D': ['0', 'O'],
        '8': ['B', '3'],
        'B': ['8', 'R'],
        '1': ['I', 'T', 'L'],
        'I': ['1', 'J', 'T'],
        '5': ['S'],
        'S': ['5'],
        '2': ['Z'],
        'Z': ['2'],
        '4': ['A'],
        'A': ['4'],
        '6': ['G', 'C'],
        'G': ['6', 'C'],
    }

    def __init__(self, fusion: Optional[WeightedConfidenceFusion] = None):
        self.fusion = fusion or WeightedConfidenceFusion()

    async def process_frame(self, camera_id: str, frame_bytes: bytes) -> List[UnifiedDetectionPayload]:
        """Process incoming raw frame bytes (fallback / future bridge)."""
        return []

    def generate_reid_vector(self, plate_number: str, vehicle_type: str, color: str) -> ReIDEmbedding:
        """Generates a reproducible 512-dimensional L2-normalized vector for a given vehicle profile.
        Matching vehicles produce identical embeddings (cosine similarity = 1.0),
        while distinct vehicles diverge (cosine similarity ~ 0.0).
        """
        seed_str = f"{plate_number}:{vehicle_type}:{color}"
        seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed_int)

        # 512-dim feature vector normalized to unit length: ||v||_2 = 1.0
        raw_vec = rng.normal(0.0, 1.0, 512)
        norm = np.linalg.norm(raw_vec)
        unit_vec = (raw_vec / norm).tolist() if norm > 0 else raw_vec.tolist()

        sig_hash = hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:12].upper()
        return ReIDEmbedding(
            vector=unit_vec,
            signature_hash=sig_hash,
            similarity_threshold=0.82
        )

    # Backward-compatibility alias
    _generate_reid_vector = generate_reid_vector

    def generate_hsrp_plate_svg(
        self,
        plate_text: str,
        bg_color: str = "#FEF08A",
        text_color: str = "#0F172A"
    ) -> str:
        """Generates an authentic Indian High Security Registration Plate (HSRP) SVG crop."""
        # Commercial / EV / Private plate spacing (e.g. DL 01 AB 1234)
        formatted_plate = plate_text
        clean_compact = plate_text.replace(" ", "").replace("-", "")
        if len(clean_compact) >= 9 and ' ' not in plate_text:
            formatted_plate = f"{clean_compact[:2]} {clean_compact[2:4]} {clean_compact[4:6]} {clean_compact[6:]}"

        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 60" width="240" height="60" class="rounded shadow-md border border-slate-700">
  <defs>
    <filter id="emboss" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="1" dy="1" stdDeviation="0.5" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect width="240" height="60" rx="6" fill="{bg_color}" stroke="#334155" stroke-width="2"/>
  <!-- Blue IND band on left -->
  <rect x="0" y="0" width="34" height="60" rx="4" fill="#1D4ED8"/>
  <circle cx="17" cy="18" r="7" fill="#F8FAFC" opacity="0.9"/>
  <text x="17" y="21" font-size="7" font-weight="900" fill="#1E3A8A" text-anchor="middle" font-family="monospace">☸</text>
  <text x="17" y="44" font-size="10" font-weight="900" fill="#F8FAFC" text-anchor="middle" font-family="sans-serif" letter-spacing="1">IND</text>
  <!-- Hologram mark -->
  <rect x="38" y="8" width="10" height="10" rx="2" fill="#94A3B8" opacity="0.6"/>
  <!-- Registration Number with emboss effect -->
  <text x="136" y="41" font-size="22" font-weight="900" fill="{text_color}" text-anchor="middle" font-family="monospace" letter-spacing="3" filter="url(#emboss)">{formatted_plate}</text>
</svg>'''

    # Backward-compatibility alias
    _generate_hsrp_plate_svg = generate_hsrp_plate_svg

    def generate_hsrp_plate_svg_data_uri(
        self,
        plate_text: str,
        bg_color: str = "#FEF08A",
        text_color: str = "#0F172A"
    ) -> str:
        """Encodes the HSRP SVG plate crop as a Base64 data URI."""
        svg_xml = self.generate_hsrp_plate_svg(plate_text, bg_color=bg_color, text_color=text_color)
        b64 = base64.b64encode(svg_xml.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"

    def apply_ocr_noise(self, clean_plate: str) -> Tuple[str, float]:
        """Simulates realistic optical camera OCR confusion and confidence degradation.
        Identifies confusable characters and mutates 1-2 characters with optical noise.
        """
        chars = list(clean_plate)
        mutable_indices = [i for i, ch in enumerate(chars) if ch in self.OCR_CONFUSIONS]

        if mutable_indices:
            num_mutations = min(len(mutable_indices), random.choice([1, 2]))
            chosen_indices = random.sample(mutable_indices, num_mutations)
            for idx in chosen_indices:
                orig_char = chars[idx]
                candidates = [c for c in self.OCR_CONFUSIONS[orig_char] if c != orig_char]
                if candidates:
                    chars[idx] = random.choice(candidates)
        else:
            # Fallback if no characters matched standard confusions
            if len(chars) > 2:
                idx = random.randint(0, len(chars) - 1)
                chars[idx] = random.choice(['0', '8', 'B', 'O'])

        mutated_text = "".join(chars)
        conf = round(random.uniform(0.68, 0.84), 3)
        return mutated_text, conf

    # Backward-compatibility alias
    _apply_ocr_noise = apply_ocr_noise

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
        det_id = f"det_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Normalize vehicle type
        if isinstance(vehicle_type, str):
            try:
                v_type = VehicleType(vehicle_type.upper())
            except ValueError:
                v_type = VehicleType.CAR
        else:
            v_type = vehicle_type

        # Vehicle detector confidence
        det_conf = round(random.uniform(0.89, 0.99), 3)

        # Realistic Bounding box within normalized image [0, 1]
        x_min = round(random.uniform(0.15, 0.35), 3)
        y_min = round(random.uniform(0.20, 0.45), 3)
        x_max = round(min(0.98, x_min + random.uniform(0.30, 0.50)), 3)
        y_max = round(min(0.98, y_min + random.uniform(0.30, 0.50)), 3)

        bbox = BoundingBox(
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max
        )

        vehicle_det = VehicleDetection(
            bbox=bbox,
            vehicle_type=v_type,
            confidence=det_conf,
            color=color,
            make_model=make_model
        )

        # ANPR simulation
        if ocr_noise:
            ocr_text, ocr_conf = self.apply_ocr_noise(plate_number)
            # Confused/mutated characters have lower character confidence
            char_confs = []
            for i, ch in enumerate(ocr_text):
                is_mutated = (i < len(plate_number) and ch != plate_number[i])
                if is_mutated:
                    char_confs.append(round(random.uniform(0.48, 0.72), 2))
                else:
                    char_confs.append(round(random.uniform(0.86, 0.98), 2))
        else:
            ocr_text = plate_number
            ocr_conf = round(random.uniform(0.92, 0.99), 3)
            char_confs = [round(random.uniform(0.90, 0.99), 2) for _ in ocr_text]

        # License plate bounding box located within lower-center of vehicle
        plate_bbox = BoundingBox(
            x_min=round(x_min + (x_max - x_min) * 0.25, 3),
            y_min=round(y_min + (y_max - y_min) * 0.65, 3),
            x_max=round(x_min + (x_max - x_min) * 0.75, 3),
            y_max=round(y_min + (y_max - y_min) * 0.88, 3)
        )

        anpr_result = ANPRResult(
            plate_text=plate_number,
            raw_text=ocr_text,
            confidence=ocr_conf,
            plate_bbox=plate_bbox,
            character_confidences=char_confs
        )

        # Re-ID simulation
        reid_result = self.generate_reid_vector(plate_number, v_type.value, color)

        # Fused Confidence
        fused = self.fusion.fuse(vehicle_det, anpr_result, reid_result)

        # Plate SVG Crop Styling:
        # Green for EVs, Yellow for Commercial (BUS/TRUCK/AUTO), White for Private
        model_upper = (make_model or "").upper()
        if "EV" in model_upper or "ELECTRIC" in model_upper:
            bg_plate = "#15803D"
            text_plate = "#FFFFFF"
        elif v_type in [VehicleType.BUS, VehicleType.TRUCK, VehicleType.AUTO]:
            bg_plate = "#FACC15"
            text_plate = "#0F172A"
        else:
            bg_plate = "#F8FAFC"
            text_plate = "#0F172A"

        crop_svg = self.generate_hsrp_plate_svg(ocr_text, bg_color=bg_plate, text_color=text_plate)

        return UnifiedDetectionPayload(
            id=det_id,
            camera_id=camera_id,
            timestamp=now,
            detection=vehicle_det,
            anpr=anpr_result,
            reid=reid_result,
            fused_confidence=fused,
            estimated_speed_kmh=round(speed_kmh, 1),
            crop_svg=crop_svg,
            metadata={"source": "SIMULATOR_PROVIDER_V1"}
        )
