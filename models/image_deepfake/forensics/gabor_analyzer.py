import io
from typing import Dict, Any, List
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class GaborTextureAnalyzer:
    """
    Multi-Scale, Multi-Orientation Gabor Filter Bank Forensic Analyzer.
    
    Biological and optical camera textures exhibit rich, natural multi-directional
    high-frequency energy variations. In contrast, generative AI architectures
    (GANs, Diffusion models, and digital face-swaps) produce distinct texture anomalies:
    1. Unnatural Spatial Smoothing: Loss of micro-texture energy across skin and background.
    2. Directional Brush / Latent Artifacts: Abnormal energy concentration at specific angles (e.g. 45° or 135°).
    3. Scale-Inconsistency: Disparity between fine-scale (wavelength 4.0) and coarse-scale (wavelength 8.0) responses.
    
    This analyzer applies a deterministic bank of 8 zero-mean Gabor kernels across 4 orientations:
    [0°, 45°, 90°, 135°] and 2 spatial frequencies [lambda=4.0, 8.0].
    """

    def __init__(self):
        self.is_available = cv2 is not None
        self.orientations = [0.0, np.pi / 4.0, np.pi / 2.0, 3.0 * np.pi / 4.0]
        self.wavelengths = [4.0, 8.0]
        self.ksize = 21
        self.sigma = 3.5
        self.gamma = 0.5
        self.psi = 0.0

    def _generate_kernels(self) -> List[np.ndarray]:
        """Generates the 8 zero-mean Gabor filter kernels for pure AC texture extraction."""
        kernels = []
        if not self.is_available:
            return kernels

        for wavelength in self.wavelengths:
            for theta in self.orientations:
                kernel = cv2.getGaborKernel(
                    (self.ksize, self.ksize),
                    self.sigma,
                    theta,
                    wavelength,
                    self.gamma,
                    self.psi,
                    ktype=cv2.CV_32F
                )
                # Zero-mean DC subtraction to isolate pure texture variation from DC brightness
                kernel = kernel - np.mean(kernel)
                kernels.append(kernel)
        return kernels

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyzes the image for micro-texture and Gabor spatial-frequency anomalies.
        Returns:
            - gabor_anomaly_score (float in [0.0, 1.0])
            - is_texture_anomalous (bool)
            - mean_energy (float)
            - orientation_entropy (float)
            - directional_variance (float)
            - finding (str)
        """
        if not self.is_available:
            return {
                "gabor_anomaly_score": 0.1,
                "is_texture_anomalous": False,
                "mean_energy": 15.0,
                "orientation_entropy": 1.35,
                "directional_variance": 0.2,
                "status": "SKIPPED",
                "finding": "OpenCV unavailable for Gabor filter bank analysis."
            }

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("L")
            img_resized = img.resize((256, 256), Image.Resampling.BILINEAR)
            img_arr = np.array(img_resized, dtype=np.float32)

            kernels = self._generate_kernels()
            energy_responses: List[float] = []

            for kernel in kernels:
                filtered = cv2.filter2D(img_arr, cv2.CV_32F, kernel)
                energy = float(np.mean(np.abs(filtered)))
                energy_responses.append(energy)

            if len(energy_responses) != 8:
                return {
                    "gabor_anomaly_score": 0.1,
                    "is_texture_anomalous": False,
                    "mean_energy": 15.0,
                    "orientation_entropy": 1.35,
                    "directional_variance": 0.2,
                    "status": "PARTIAL_SUCCESS",
                    "finding": "Gabor kernel bank generation incomplete."
                }

            # Fine-scale energies (first 4: 0°, 45°, 90°, 135° at wavelength 4.0)
            fine_energies = np.array(energy_responses[:4], dtype=np.float32)
            # Coarse-scale energies (last 4: 0°, 45°, 90°, 135° at wavelength 8.0)
            coarse_energies = np.array(energy_responses[4:], dtype=np.float32)

            mean_fine = float(np.mean(fine_energies))
            mean_coarse = float(np.mean(coarse_energies))
            total_mean_energy = (mean_fine + mean_coarse) / 2.0

            # 1. Directional Texture Entropy (Normalized distribution across 4 angles)
            fine_sum = float(np.sum(fine_energies)) + 1e-6
            fine_probs = fine_energies / fine_sum
            fine_entropy = float(-np.sum(fine_probs * np.log(fine_probs + 1e-8)))
            
            # Directional variance ratio
            dir_var = float(np.std(fine_energies) / (mean_fine + 1e-6))

            # Maximum theoretical entropy for 4 uniform angles is ln(4) ≈ 1.386
            # Low entropy (< 1.05) or high directional variance (> 0.85) indicates unnatural directional bias
            is_directional_bias = (fine_entropy < 1.05) or (dir_var > 0.85)

            # 2. Micro-Texture Absence (Over-smoothed skin / latent rendering)
            # With zero-mean AC filtering, flat/blank images have total_mean_energy < 1.0
            is_over_smoothed = total_mean_energy < 1.5

            is_texture_anomalous = is_directional_bias or is_over_smoothed

            # Continuous anomaly mapping
            if is_over_smoothed:
                anomaly_score = 0.78
            elif is_directional_bias:
                anomaly_score = min(0.85, max(0.50, dir_var * 0.70))
            else:
                # Normal natural optical texture distribution
                anomaly_score = float(round(max(0.04, min(0.30, dir_var * 0.25)), 3))

            finding_text = (
                "Multi-scale Gabor filter bank detected anomalous directional texture clustering and synthetic micro-smoothing."
                if is_texture_anomalous
                else "Natural multi-orientation spatial-frequency texture distribution verified."
            )

            return {
                "gabor_anomaly_score": float(round(anomaly_score, 3)),
                "is_texture_anomalous": is_texture_anomalous,
                "mean_energy": float(round(total_mean_energy, 2)),
                "orientation_entropy": float(round(fine_entropy, 3)),
                "directional_variance": float(round(dir_var, 3)),
                "status": "APPLIED",
                "finding": finding_text
            }

        except Exception as e:
            return {
                "gabor_anomaly_score": 0.1,
                "is_texture_anomalous": False,
                "mean_energy": 15.0,
                "orientation_entropy": 1.35,
                "directional_variance": 0.2,
                "status": "FALLBACK",
                "finding": f"Gabor texture analysis fallback: {str(e)}"
            }
