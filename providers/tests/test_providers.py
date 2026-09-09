import asyncio
import math
import time
import pytest
import numpy as np

from providers.base import (
    VehicleType,
    BoundingBox,
    VehicleDetection,
    ANPRResult,
    ReIDEmbedding,
    UnifiedDetectionPayload,
    IVisionProvider,
)
from providers.confidence_fusion import (
    WeightedConfidenceFusion,
    compute_cosine_similarity,
)
from providers.simulator_provider import SimulatorVisionProvider
from providers.real.yolo_provider import YOLOv8VehicleDetector
from providers.real.paddle_provider import PaddleOCRProvider
from providers.real.reid_provider import TorchReIDProvider
from providers.real.yolo_paddle_provider import YoloPaddleVisionProvider


# =====================================================================
# 1. Payload Generation & Schema Conformance Tests
# =====================================================================

@pytest.mark.asyncio
async def test_payload_generation_conformance():
    """Verifies that SimulatorVisionProvider generates conforming UnifiedDetectionPayload instances."""
    provider = SimulatorVisionProvider()
    
    test_cases = [
        ("CAM-01", "DL01AB1234", VehicleType.CAR, "White", "Honda City", 54.5),
        ("CAM-02", "HR26DK8899", VehicleType.SUV, "Black", "Tata Harrier", 68.0),
        ("CAM-03", "UP16BT9900", VehicleType.BUS, "Blue", "Tata Starbus", 42.0),
        ("CAM-04", "DL3CBA1122", VehicleType.TRUCK, "Yellow", "Ashok Leyland", 35.0),
        ("CAM-05", "MH12QZ4321", VehicleType.MOTORCYCLE, "Red", "Bajaj Pulsar", 45.0),
        ("CAM-06", "DL1ER7788", VehicleType.AUTO, "Green", "Bajaj RE", 28.5),
    ]

    for cam_id, plate, v_type, color, model, speed in test_cases:
        payload = await provider.generate_simulated_detection(
            camera_id=cam_id,
            plate_number=plate,
            vehicle_type=v_type,
            color=color,
            make_model=model,
            speed_kmh=speed,
            ocr_noise=False
        )

        assert isinstance(payload, UnifiedDetectionPayload)
        assert payload.id.startswith("det_")
        assert payload.camera_id == cam_id
        assert payload.timestamp.tzinfo is not None  # UTC timezone aware
        assert payload.estimated_speed_kmh == round(speed, 1)

        # Vehicle Detection validation
        det = payload.detection
        assert isinstance(det, VehicleDetection)
        assert det.vehicle_type == v_type
        assert det.color == color
        assert det.make_model == model
        assert 0.0 <= det.confidence <= 1.0

        # Bounding box coordinates validation
        bbox = det.bbox
        assert isinstance(bbox, BoundingBox)
        assert 0.0 <= bbox.x_min < bbox.x_max <= 1.0
        assert 0.0 <= bbox.y_min < bbox.y_max <= 1.0

        # ANPR Result validation
        anpr = payload.anpr
        assert isinstance(anpr, ANPRResult)
        assert anpr.plate_text == plate
        assert anpr.raw_text == plate
        assert 0.0 <= anpr.confidence <= 1.0
        assert len(anpr.character_confidences) == len(plate)
        for c_conf in anpr.character_confidences:
            assert 0.0 <= c_conf <= 1.0

        # Plate bounding box check
        assert anpr.plate_bbox is not None
        assert 0.0 <= anpr.plate_bbox.x_min < anpr.plate_bbox.x_max <= 1.0
        assert 0.0 <= anpr.plate_bbox.y_min < anpr.plate_bbox.y_max <= 1.0

        # Re-ID Embedding validation
        reid = payload.reid
        assert isinstance(reid, ReIDEmbedding)
        assert len(reid.vector) == 512
        assert len(reid.signature_hash) > 0

        # Fused confidence bounds
        assert 0.0 <= payload.fused_confidence <= 1.0

        # Metadata
        assert payload.metadata.get("source") == "SIMULATOR_PROVIDER_V1"


@pytest.mark.asyncio
async def test_string_vehicle_type_handling():
    """Verifies that passing a string vehicle_type gracefully maps to VehicleType enum."""
    provider = SimulatorVisionProvider()
    payload = await provider.generate_simulated_detection(
        camera_id="CAM-01",
        plate_number="DL01AB1234",
        vehicle_type="suv",  # lowercase string
        color="Silver",
        make_model="Hyundai Creta",
        speed_kmh=60.0
    )
    assert payload.detection.vehicle_type == VehicleType.SUV


# =====================================================================
# 2. HSRP SVG Plate Crop Synthesizer Tests
# =====================================================================

def test_hsrp_svg_plate_crop_rendering():
    """Verifies that the generated SVG conforms to authentic Indian HSRP plate layout."""
    provider = SimulatorVisionProvider()
    
    # Standard Private Plate
    svg = provider.generate_hsrp_plate_svg("DL01AB1234")
    assert svg.startswith('<svg')
    assert svg.endswith('</svg>')
    assert 'viewBox="0 0 240 60"' in svg

    # Blue IND strip on the left side
    assert 'fill="#1D4ED8"' in svg
    assert 'IND' in svg

    # Ashoka Chakra wheel icon
    assert '☸' in svg

    # Hologram emblem indicator
    assert 'opacity="0.6"' in svg

    # Embossed filter definition
    assert '<filter id="emboss"' in svg

    # Formatted spaced plate number
    assert "DL 01 AB 1234" in svg


def test_hsrp_plate_color_schemes():
    """Verifies plate color theming: EV (Green), Commercial (Yellow), Private (White)."""
    provider = SimulatorVisionProvider()

    # EV styling
    svg_ev = provider.generate_hsrp_plate_svg("DL01EV9999", bg_color="#15803D", text_color="#FFFFFF")
    assert 'fill="#15803D"' in svg_ev
    assert 'fill="#FFFFFF"' in svg_ev

    # Commercial styling
    svg_comm = provider.generate_hsrp_plate_svg("DL1T9999", bg_color="#FACC15", text_color="#0F172A")
    assert 'fill="#FACC15"' in svg_comm

    # Private styling
    svg_priv = provider.generate_hsrp_plate_svg("DL01AB1234", bg_color="#F8FAFC", text_color="#0F172A")
    assert 'fill="#F8FAFC"' in svg_priv


@pytest.mark.asyncio
async def test_hsrp_plate_color_automatic_assignment():
    """Verifies that generate_simulated_detection correctly styles plates based on vehicle attributes."""
    provider = SimulatorVisionProvider()

    # Electric car
    payload_ev = await provider.generate_simulated_detection(
        camera_id="CAM-01", plate_number="DL01EV1111", vehicle_type=VehicleType.CAR,
        color="Teal", make_model="Tata Nexon EV", speed_kmh=50.0
    )
    assert '#15803D' in payload_ev.crop_svg

    # Commercial Truck
    payload_truck = await provider.generate_simulated_detection(
        camera_id="CAM-01", plate_number="HR55AA9999", vehicle_type=VehicleType.TRUCK,
        color="Brown", make_model="BharatBenz 2823", speed_kmh=40.0
    )
    assert '#FACC15' in payload_truck.crop_svg

    # Private Car
    payload_car = await provider.generate_simulated_detection(
        camera_id="CAM-01", plate_number="DL01AB1234", vehicle_type=VehicleType.CAR,
        color="White", make_model="Maruti Dzire", speed_kmh=50.0
    )
    assert '#F8FAFC' in payload_car.crop_svg


def test_hsrp_svg_data_uri():
    """Verifies Base64 data URI output for embedding in web UI."""
    provider = SimulatorVisionProvider()
    data_uri = provider.generate_hsrp_plate_svg_data_uri("DL01AB1234")
    assert data_uri.startswith("data:image/svg+xml;base64,")
    assert len(data_uri) > 50


# =====================================================================
# 3. OCR Confusion Noise & Character Degradation Tests
# =====================================================================

def test_ocr_confusion_noise_mutation():
    """Verifies that OCR noise mutates optical confusion characters and lowers confidence."""
    provider = SimulatorVisionProvider()
    plate = "DL01AB1234"

    mutated_plate, conf = provider.apply_ocr_noise(plate)
    # The plate has '0', '1', 'A', 'B', '2' which are confusable
    assert mutated_plate != plate
    assert 0.65 <= conf <= 0.85
    assert len(mutated_plate) == len(plate)


@pytest.mark.asyncio
async def test_ocr_noise_simulation_payload():
    """Verifies character confidences degrade for confused characters when ocr_noise is True."""
    provider = SimulatorVisionProvider()
    clean_plate = "DL01AB1234"

    # Clean detection
    clean_payload = await provider.generate_simulated_detection(
        camera_id="CAM-01", plate_number=clean_plate, vehicle_type=VehicleType.CAR,
        color="White", make_model="Swift", speed_kmh=50.0, ocr_noise=False
    )
    assert clean_payload.anpr.raw_text == clean_plate
    assert clean_payload.anpr.confidence >= 0.90
    for char_conf in clean_payload.anpr.character_confidences:
        assert char_conf >= 0.88

    # Noisy detection
    noisy_payload = await provider.generate_simulated_detection(
        camera_id="CAM-01", plate_number=clean_plate, vehicle_type=VehicleType.CAR,
        color="White", make_model="Swift", speed_kmh=50.0, ocr_noise=True
    )
    assert noisy_payload.anpr.raw_text != clean_plate
    assert noisy_payload.anpr.confidence <= 0.85
    assert len(noisy_payload.anpr.character_confidences) == len(noisy_payload.anpr.raw_text)

    # At least one character confidence should reflect optical confusion degradation (< 0.75)
    has_low_char_conf = any(c < 0.75 for c in noisy_payload.anpr.character_confidences)
    assert has_low_char_conf


def test_ocr_confusions_dictionary_integrity():
    """Verifies the bidirectional and valid mappings in OCR_CONFUSIONS."""
    confusions = SimulatorVisionProvider.OCR_CONFUSIONS
    assert '0' in confusions and 'O' in confusions['0']
    assert '8' in confusions and 'B' in confusions['8']
    assert '1' in confusions and 'I' in confusions['1']
    assert '5' in confusions and 'S' in confusions['5']
    assert '2' in confusions and 'Z' in confusions['2']


# =====================================================================
# 4. Re-ID Embedding, L2-Normalization & Cosine Similarity Tests
# =====================================================================

def test_reid_l2_normalization():
    """Verifies that Re-ID embeddings are strictly unit-normalized (||v||_2 = 1.0)."""
    provider = SimulatorVisionProvider()
    reid = provider.generate_reid_vector("DL01AB1234", "CAR", "White")

    vec = np.array(reid.vector, dtype=np.float64)
    assert len(vec) == 512
    l2_norm = np.linalg.norm(vec)
    assert abs(l2_norm - 1.0) < 1e-5, f"Norm was {l2_norm}, expected 1.0"


def test_reid_reproducibility_for_genuine_vehicles():
    """Verifies that identical vehicle attributes produce identical embeddings (cos_sim = 1.0)."""
    provider = SimulatorVisionProvider()
    reid1 = provider.generate_reid_vector("DL01AB1234", "CAR", "White")
    reid2 = provider.generate_reid_vector("DL01AB1234", "CAR", "White")

    sim = compute_cosine_similarity(reid1.vector, reid2.vector)
    assert abs(sim - 1.0) < 1e-4
    assert reid1.signature_hash == reid2.signature_hash


def test_reid_divergence_for_impostors():
    """Verifies that impostors (different plate, or cloned plate with different vehicle type/color) diverge."""
    provider = SimulatorVisionProvider()
    
    # Same plate, but different vehicle type & color (cloned plate anomaly)
    reid_genuine = provider.generate_reid_vector("DL01AB1234", "CAR", "White")
    reid_clone = provider.generate_reid_vector("DL01AB1234", "TRUCK", "Red")

    sim_clone = compute_cosine_similarity(reid_genuine.vector, reid_clone.vector)
    # High-dimensional random vectors on unit sphere are near orthogonal (similarity close to 0)
    assert abs(sim_clone) < 0.25, f"Expected divergence, got cosine similarity {sim_clone}"
    assert reid_genuine.signature_hash != reid_clone.signature_hash

    # Completely different vehicles
    reid_diff = provider.generate_reid_vector("HR26DK9999", "SUV", "Black")
    sim_diff = compute_cosine_similarity(reid_genuine.vector, reid_diff.vector)
    assert abs(sim_diff) < 0.25


def test_compute_cosine_similarity_math():
    """Unit test for the compute_cosine_similarity helper with known geometric vectors."""
    # Parallel vectors
    v1 = [1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v1) == 1.0

    # Orthogonal vectors
    v2 = [0.0, 1.0, 0.0]
    assert compute_cosine_similarity(v1, v2) == 0.0

    # Opposite vectors
    v3 = [-1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v3) == -1.0

    # Empty / degenerate vectors
    assert compute_cosine_similarity([], []) == 0.0
    assert compute_cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert compute_cosine_similarity([1.0, 2.0], [1.0]) == 0.0


# =====================================================================
# 5. Confidence Fusion Engine Tests
# =====================================================================

def test_confidence_fusion_weights_and_math():
    """Verifies the multi-modal confidence fusion weighting scheme."""
    fusion = WeightedConfidenceFusion(w_anpr=0.55, w_det=0.35, w_reid=0.10)

    det = VehicleDetection(
        bbox=BoundingBox(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.5),
        vehicle_type=VehicleType.CAR,
        confidence=0.90,
        color="White"
    )
    anpr = ANPRResult(
        plate_text="DL01AB1234",
        raw_text="DL01AB1234",
        confidence=0.80,
    )

    # 1. With unit-normalized Re-ID embedding (reid_confidence = 0.95)
    # Expected: (0.35 * 0.90) + (0.55 * 0.80) + (0.10 * 0.95)
    #         = 0.315 + 0.440 + 0.095 = 0.850
    val = 1.0 / math.sqrt(512)
    reid = ReIDEmbedding(vector=[val] * 512, signature_hash="TEST")
    score_with_reid = fusion.fuse(det, anpr, reid)
    assert abs(score_with_reid - 0.850) < 1e-3

    # 2. Without Re-ID embedding: renormalized to 0.35 + 0.55 = 0.90
    # Expected: (0.315 + 0.440) / 0.90 = 0.755 / 0.90 = 0.839
    score_no_reid = fusion.fuse(det, anpr, None)
    assert abs(score_no_reid - 0.839) < 1e-3

    # 3. With explicit Re-ID similarity (e.g. cosine similarity = 0.90)
    # Expected: (0.35 * 0.90) + (0.55 * 0.80) + (0.10 * 0.90) = 0.845
    score_explicit_reid = fusion.fuse(det, anpr, reid_similarity=0.90)
    assert abs(score_explicit_reid - 0.845) < 1e-3

    # 4. Boundedness checks
    det_perfect = VehicleDetection(
        bbox=BoundingBox(x_min=0.1, y_min=0.1, x_max=0.5, y_max=0.5),
        vehicle_type=VehicleType.CAR,
        confidence=1.0,
        color="White"
    )
    anpr_perfect = ANPRResult(plate_text="DL01AB1234", raw_text="DL01AB1234", confidence=1.0)
    assert fusion.fuse(det_perfect, anpr_perfect, reid_similarity=1.0) == 1.0


# =====================================================================
# 6. Production Real AI Stubs Tests (Zero Framework Leakage)
# =====================================================================

@pytest.mark.asyncio
async def test_yolo_detector_stub():
    """Verifies that YOLOv8VehicleDetector initializes gracefully without torch/ultralytics."""
    detector = YOLOv8VehicleDetector()
    assert not detector.is_model_loaded()
    
    # Calling detect on empty or stub input returns empty list cleanly
    results = await detector.detect(b"")
    assert results == []


@pytest.mark.asyncio
async def test_paddle_ocr_stub():
    """Verifies that PaddleOCRProvider initializes gracefully without paddleocr installed."""
    ocr_provider = PaddleOCRProvider()
    assert not ocr_provider.is_model_loaded()

    # Fallback stub returns valid ANPRResult
    result = await ocr_provider.recognize(b"mock_frame_bytes")
    assert isinstance(result, ANPRResult)
    assert result.plate_text == "DL01AB1234"
    assert result.confidence == 0.98
    assert len(result.character_confidences) == 10


@pytest.mark.asyncio
async def test_torch_reid_stub():
    """Verifies that TorchReIDProvider produces an L2-normalized 512-dim embedding."""
    reid_provider = TorchReIDProvider()
    assert not reid_provider.is_model_loaded()

    crop_bytes = b"sample_vehicle_crop_image"
    embedding = await reid_provider.extract_features(crop_bytes)
    assert isinstance(embedding, ReIDEmbedding)
    assert len(embedding.vector) == 512

    # Verify unit-normalization
    vec = np.array(embedding.vector, dtype=np.float64)
    l2_norm = np.linalg.norm(vec)
    assert abs(l2_norm - 1.0) < 1e-5


@pytest.mark.asyncio
async def test_composite_yolo_paddle_provider():
    """Verifies that YoloPaddleVisionProvider implements IVisionProvider contract."""
    composite = YoloPaddleVisionProvider()
    assert isinstance(composite, IVisionProvider)

    # Verify process_frame executes
    payloads = await composite.process_frame("CAM-01", b"")
    assert isinstance(payloads, list)

    # Verify generate_simulated_detection fallback
    sim_payload = await composite.generate_simulated_detection(
        camera_id="CAM-01",
        plate_number="DL01AB1234",
        vehicle_type=VehicleType.CAR,
        color="Silver",
        make_model="City",
        speed_kmh=55.0
    )
    assert isinstance(sim_payload, UnifiedDetectionPayload)
    assert sim_payload.metadata.get("source") == "YOLO_PADDLE_SIM_FALLBACK"


# =====================================================================
# 7. Provider Throughput & Performance Benchmark (> 50 FPS)
# =====================================================================

@pytest.mark.asyncio
async def test_provider_throughput_fps():
    """Verifies that SimulatorVisionProvider exceeds 50 frames per second on CPU."""
    provider = SimulatorVisionProvider()
    iterations = 200

    start = time.perf_counter()
    for _ in range(iterations):
        await provider.generate_simulated_detection(
            camera_id="CAM-BENCH",
            plate_number="DL01AB1234",
            vehicle_type=VehicleType.CAR,
            color="White",
            make_model="Swift",
            speed_kmh=60.0,
            ocr_noise=True
        )
    elapsed = time.perf_counter() - start
    fps = iterations / elapsed

    assert fps > 50.0, f"Provider throughput {fps:.1f} fps is below required 50 fps!"
