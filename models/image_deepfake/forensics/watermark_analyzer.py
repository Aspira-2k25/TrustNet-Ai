import io
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class WatermarkIconAnalyzer:
    """
    Pixel-Level Generative-Platform Watermark Analyzer (v2 — false-positive hardened).

    IMPORTANT CALIBRATION NOTE (read before wiring into fusion):
    This is a SHAPE HEURISTIC, not logo recognition. It cannot semantically
    distinguish a generative-platform sparkle from a sticker, badge, small
    logo on clothing, or lens flare that happens to sit in a corner. It MUST
    be treated as one corroborating vote among many in the fusion, gated by
    the SAME multi-domain corroboration rule as every other analyzer
    (strong_domain_count >= 2 before it can push the score toward "confirmed
    fake"). It must NEVER be wired into the deterministic metadata-signature
    override path (the one reserved for actual embedded AI-generator text
    signatures) -- that path assumes near-zero false-positive risk, which
    this heuristic does not have.

    v2 changes from v1:
    - Added a convexity-defect ("pointedness") check. A 4-pointed sparkle
      icon has ~3-5 distinct concave notches around its outline; a circular
      sticker, button, badge, or lens flare has ~0. Solidity range alone
      (v1's only shape test) does not reliably separate these, so this is
      now a REQUIRED additional condition, not just a nice-to-have.
    - Raised the acceptance bar overall: both the solidity band AND the
      defect-count/depth condition must pass, and the combined confidence
      threshold to report a hit is unchanged (0.55/0.60) but is now harder to
      reach by accident.
    """

    def __init__(self, corner_fraction: float = 0.14, min_area_frac: float = 0.0006, max_area_frac: float = 0.08):
        self.is_available = cv2 is not None
        self.corner_fraction = corner_fraction
        self.min_area_frac = min_area_frac
        self.max_area_frac = max_area_frac

    def _get_corners(self, gray: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        h, w = gray.shape
        cw = max(8, int(w * self.corner_fraction))
        ch = max(8, int(h * self.corner_fraction))
        return [
            ("top_left", gray[0:ch, 0:cw]),
            ("top_right", gray[0:ch, w - cw:w]),
            ("bottom_left", gray[h - ch:h, 0:cw]),
            ("bottom_right", gray[h - ch:h, w - cw:w]),
        ]

    def _symmetry_score(self, mask: np.ndarray) -> float:
        if mask.size == 0:
            return 0.0
        flipped_h = np.fliplr(mask)
        flipped_v = np.flipud(mask)
        agree_h = np.mean(mask == flipped_h)
        agree_v = np.mean(mask == flipped_v)
        return float(max(agree_h, agree_v))

    def _pointedness_score(self, contour) -> float:
        """
        Counts significant convexity defects (concave notches) relative to
        contour size. A star/sparkle glyph has several deep, evenly-spaced
        notches. A circle, blob, or rounded sticker has none deep enough to
        count. Returns 0.0 (not pointed) to 1.0 (clearly star-shaped).
        """
        try:
            hull_idx = cv2.convexHull(contour, returnPoints=False)
            if hull_idx is None or len(hull_idx) < 4:
                return 0.0
            defects = cv2.convexityDefects(contour, hull_idx)
            if defects is None:
                return 0.0

            _, _, w_box, h_box = cv2.boundingRect(contour)
            scale = max(1.0, float(max(w_box, h_box)))

            # A defect's depth (4th column, fixed-point: depth in 1/256 of pixel) scaled by contour size.
            # In OpenCV Python, defects can have shape (M, 1, 4) or (M, 4).
            depths = defects[:, 0, 3] if defects.ndim == 3 else defects[:, 3]
            significant = [float(d) / 256.0 for d in depths if (float(d) / 256.0) / scale > 0.06]

            if len(significant) < 3:
                return 0.0
            # Peak confidence around 4 notches (matches a 4-pointed sparkle);
            # too many (>8) suggests noisy/jagged compression artifact, not a glyph.
            count_score = 1.0 - min(1.0, abs(len(significant) - 4) / 5.0)
            return max(0.0, count_score)
        except Exception:
            return 0.0

    def _is_watermark_shaped(self, contour, corner_area: int) -> Tuple[bool, float]:
        area = cv2.contourArea(contour)
        frac = area / max(1, corner_area)
        if not (self.min_area_frac <= frac <= self.max_area_frac):
            return False, 0.0

        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area <= 0:
            return False, 0.0

        solidity = area / hull_area
        is_pointed_shape = 0.35 <= solidity <= 0.85
        if not is_pointed_shape:
            return False, 0.0

        pointedness = self._pointedness_score(contour)
        if pointedness <= 0.0:
            # Solidity alone matched, but the outline has no actual star-like
            # notches -- almost certainly a sticker/badge/blob, not a glyph.
            return False, 0.0

        solidity_conf = 1.0 - abs(solidity - 0.6) / 0.6
        combined_conf = 0.5 * max(0.0, min(1.0, solidity_conf)) + 0.5 * pointedness
        return True, combined_conf

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self.is_available:
            return {
                "status": "SKIPPED",
                "is_watermark_found": False,
                "is_watermark_detected": False,
                "watermark_anomaly_score": 0.0,
                "watermark_location": None,
                "watermark_type": None,
                "finding": "OpenCV unavailable; corner watermark scan skipped.",
            }

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(image)
            gray_full = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            corners = self._get_corners(gray_full)

            best_hit = None
            best_score = 0.0

            for corner_name, corner_gray in corners:
                if corner_gray.size == 0:
                    continue

                blurred = cv2.GaussianBlur(corner_gray, (3, 3), 0)
                thresh = cv2.adaptiveThreshold(
                    blurred, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                    15, -8
                )

                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                corner_area = corner_gray.shape[0] * corner_gray.shape[1]

                for c in contours:
                    if len(c) < 5:
                        continue  # convexityDefects needs enough points to be meaningful
                    shaped, shape_conf = self._is_watermark_shaped(c, corner_area)
                    if not shaped:
                        continue

                    x, y, cw, ch = cv2.boundingRect(c)
                    patch_mask = thresh[y:y + ch, x:x + cw] > 0
                    sym_score = self._symmetry_score(patch_mask)

                    combined = 0.7 * shape_conf + 0.3 * sym_score
                    if combined > best_score:
                        best_score = combined
                        best_hit = corner_name

            if best_hit and best_score >= 0.60:
                location_str = best_hit.replace("_", " ")
                return {
                    "status": "APPLIED",
                    "is_watermark_found": True,
                    "is_watermark_detected": True,
                    "watermark_anomaly_score": round(min(0.90, best_score), 2),
                    "watermark_location": best_hit,
                    "watermark_type": f"Corner AI Watermark ({location_str})",
                    "finding": f"Small pointed/symmetric icon detected in the {location_str} corner "
                               f"(confidence {best_score*100:.0f}%), with convexity-defect notches consistent with "
                               f"a star/sparkle-style glyph. Treated as a single corroborating signal, not a "
                               f"confirmed provenance match.",
                }

            return {
                "status": "APPLIED",
                "is_watermark_found": False,
                "is_watermark_detected": False,
                "watermark_anomaly_score": 0.0,
                "watermark_location": None,
                "watermark_type": None,
                "finding": "No corner watermark icon signature detected.",
            }

        except Exception as e:
            return {
                "status": "SKIPPED",
                "is_watermark_found": False,
                "is_watermark_detected": False,
                "watermark_anomaly_score": 0.0,
                "watermark_location": None,
                "watermark_type": None,
                "finding": f"Watermark scan fallback: {str(e)}",
            }


# Alias for backward compatibility
WatermarkAnalyzer = WatermarkIconAnalyzer
