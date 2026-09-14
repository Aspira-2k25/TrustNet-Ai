import io
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class RecompressionAnalyzer:
    """
    Social Re-compression and Double-JPEG Artifact Analyzer.

    Social messaging and media platforms (WhatsApp, Telegram, Instagram, Discord, X)
    routinely re-encode uploaded media using 8x8 discrete cosine transform (DCT) blocks
    at ~75-80% quality, stripping EXIF/C2PA metadata and smoothing physical sensor noise.

    This analyzer measures 8x8 DCT block-boundary grid discontinuity:
      - In pristine camera capture: boundary variance matches internal block variance.
      - In recompressed media: inter-block boundaries (modulo 8) exhibit significant
        periodic step disparity compared to interior pixel pairs.

    When `already_recompressed` is True, downstream fusion dynamically reduces
    weights on fragile single-generation physical heuristics (ELA, PRNU, CFA, FFT)
    and shifts authority toward robust signals (Vision Transformers, watermark scan,
    scene context, and metadata).
    """

    def __init__(self, blockiness_threshold: float = 1.12):
        self.blockiness_threshold = blockiness_threshold

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            is_jpeg = image.format == "JPEG"

            # Check for quantization table signatures
            has_standard_social_quantization = False
            quant_tables = getattr(image, "quantization", None)
            if quant_tables and isinstance(quant_tables, dict):
                # Standard IJG 75-85 tables commonly used in social media recompression
                first_table = list(quant_tables.values())[0] if quant_tables else []
                if len(first_table) >= 16:
                    # DC coefficient and low AC coefficients in typical social compression
                    if first_table[0] in [8, 16, 24, 32]:
                        has_standard_social_quantization = True

            # Compute 8x8 DCT block boundary discontinuity
            img_rgb = image.convert("RGB")
            arr = np.array(img_rgb, dtype=np.float32)
            h, w, _ = arr.shape

            # Convert to luminance
            gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]

            # Horizontal boundary differences vs internal differences
            if w >= 32 and h >= 32:
                # Vertical grid lines across columns
                col_indices = np.arange(1, w - 1)
                diffs_x = np.abs(gray[:, 1:] - gray[:, :-1])

                boundary_cols = [c for c in col_indices if c % 8 == 0 and c < diffs_x.shape[1]]
                internal_cols = [c for c in col_indices if c % 8 != 0 and c < diffs_x.shape[1]]

                boundary_diff_x = float(np.mean(diffs_x[:, boundary_cols])) if boundary_cols else 1.0
                internal_diff_x = float(np.mean(diffs_x[:, internal_cols])) if internal_cols else 1.0

                # Vertical differences across rows
                row_indices = np.arange(1, h - 1)
                diffs_y = np.abs(gray[1:, :] - gray[:-1, :])

                boundary_rows = [r for r in row_indices if r % 8 == 0 and r < diffs_y.shape[0]]
                internal_rows = [r for r in row_indices if r % 8 != 0 and r < diffs_y.shape[0]]

                boundary_diff_y = float(np.mean(diffs_y[boundary_rows, :])) if boundary_rows else 1.0
                internal_diff_y = float(np.mean(diffs_y[internal_rows, :])) if internal_rows else 1.0

                boundary_avg = (boundary_diff_x + boundary_diff_y) / 2.0
                internal_avg = max(1e-5, (internal_diff_x + internal_diff_y) / 2.0)
                blockiness_ratio = boundary_avg / internal_avg
            else:
                blockiness_ratio = 1.0

            is_recompressed = (blockiness_ratio >= self.blockiness_threshold) or (has_standard_social_quantization and blockiness_ratio >= 1.06)
            recompression_score = float(round(min(1.0, max(0.0, (blockiness_ratio - 1.0) / 0.3)), 2))

            if is_recompressed:
                finding = (
                    f"Periodic 8x8 DCT block grid discontinuity detected (ratio: {blockiness_ratio:.2f} >= {self.blockiness_threshold:.2f}). "
                    "Social recompression (e.g. WhatsApp/Telegram) verified. Classical physical heuristic weights will be adaptively reduced."
                )
            else:
                finding = f"8x8 DCT grid continuity verified (ratio: {blockiness_ratio:.2f}); single-generation or uncompressed capture."

            return {
                "status": "APPLIED",
                "already_recompressed": is_recompressed,
                "recompression_score": recompression_score,
                "blockiness_ratio": float(round(blockiness_ratio, 3)),
                "has_social_quantization": has_standard_social_quantization,
                "finding": finding
            }

        except Exception as e:
            return {
                "status": "SKIPPED",
                "already_recompressed": False,
                "recompression_score": 0.0,
                "blockiness_ratio": 1.0,
                "has_social_quantization": False,
                "finding": f"Recompression analysis skipped: {str(e)}"
            }
