import math
from typing import Optional, List
import numpy as np
from providers.base import IConfidenceFusion, VehicleDetection, ANPRResult, ReIDEmbedding


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two feature vectors.
    For unit-normalized vectors (||v||_2 = 1.0), this equals the dot product.
    Returns a float in [-1.0, 1.0], or 0.0 if vectors are empty or degenerate.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    arr_a = np.asarray(vec_a, dtype=np.float64)
    arr_b = np.asarray(vec_b, dtype=np.float64)

    norm_a = float(np.linalg.norm(arr_a))
    norm_b = float(np.linalg.norm(arr_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    dot = float(np.dot(arr_a, arr_b))
    similarity = dot / (norm_a * norm_b)
    return round(float(max(-1.0, min(1.0, similarity))), 4)


class WeightedConfidenceFusion(IConfidenceFusion):
    """Fuses multi-modal confidence scores using a calibrated weighting scheme.
    Default distribution:
      - ANPR: 55%
      - Object Detection: 35%
      - Re-ID Consistency / Similarity: 10%
    """

    def __init__(self, w_anpr: float = 0.55, w_det: float = 0.35, w_reid: float = 0.10):
        self.w_anpr = float(w_anpr)
        self.w_det = float(w_det)
        self.w_reid = float(w_reid)

    def fuse(
        self,
        detection: VehicleDetection,
        anpr: ANPRResult,
        reid: Optional[ReIDEmbedding] = None,
        reference_reid: Optional[ReIDEmbedding] = None,
        reid_similarity: Optional[float] = None
    ) -> float:
        """Calculates fused multi-modal confidence.
        If reference_reid or explicit reid_similarity is supplied, the Re-ID
        score is derived from cosine similarity. Otherwise, if reid is present
        with a valid unit vector, an internal consistency confidence is used.
        If reid is absent, weights are renormalized between detection and ANPR.
        """
        det_score = detection.confidence
        anpr_score = anpr.confidence

        reid_score: Optional[float] = None

        if reid_similarity is not None:
            # Map cosine similarity to [0.0, 1.0] confidence
            reid_score = max(0.0, min(1.0, reid_similarity))
        elif reference_reid is not None and reference_reid.vector and reid is not None and reid.vector:
            cos_sim = compute_cosine_similarity(reid.vector, reference_reid.vector)
            reid_score = max(0.0, min(1.0, cos_sim))
        elif reid is not None and reid.vector:
            # Unit norm verification for feature validity
            norm = math.sqrt(sum(x * x for x in reid.vector))
            reid_score = 0.95 if abs(norm - 1.0) < 0.02 else 0.50

        if reid_score is not None:
            total_weight = self.w_det + self.w_anpr + self.w_reid
            raw_score = (
                (self.w_det * det_score) +
                (self.w_anpr * anpr_score) +
                (self.w_reid * reid_score)
            )
            score = raw_score / total_weight if total_weight > 0 else 0.0
        else:
            total_weight = self.w_det + self.w_anpr
            raw_score = (self.w_det * det_score) + (self.w_anpr * anpr_score)
            score = raw_score / total_weight if total_weight > 0 else 0.0

        return round(float(min(1.0, max(0.0, score))), 3)
