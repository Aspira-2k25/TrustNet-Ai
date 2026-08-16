import io
import numpy as np
from PIL import Image
from typing import Dict, Any, Tuple


class FrequencyAnalyzer:
    """
    Fourier Spectral Energy & Radial Power-Law (1/f^alpha) Forensic Analyzer.
    
    Natural optical camera images follow a strict physical power-law distribution in the
    frequency domain: the radially averaged power spectrum decays monotonically as P(r) ~ 1 / r^alpha,
    where alpha is typically in the range [1.8, 3.4].
    
    In contrast, generative AI architectures (GANs with transposed convolutions, Latent Diffusion models,
    and neural upsamplers) exhibit two distinct physical frequency violations:
    1. High-Frequency Periodic Spikes: Regular geometric grid artifacts visible in the 2D DFT spectrum.
    2. Radial Power-Law Deviation: High-frequency spectral flattening (alpha < 1.35) or non-monotonic
       spectral energy bumps where the generative model fails to match optical lens diffraction roll-off.
    """

    def _compute_radial_profile(self, power_spectrum: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Computes the 1D radially averaged power spectrum profile."""
        h, w = power_spectrum.shape
        cy, cx = h // 2, w // 2
        
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(np.int32)
        
        max_radius = min(cy, cx)
        radial_profile = np.zeros(max_radius, dtype=np.float32)
        radial_counts = np.zeros(max_radius, dtype=np.int32)
        
        # Bin power spectrum values by integer radius
        for radius in range(1, max_radius):
            mask = (r == radius)
            if np.any(mask):
                radial_profile[radius] = np.mean(power_spectrum[mask])
                radial_counts[radius] = 1
                
        valid = radial_counts > 0
        radii = np.arange(max_radius)[valid]
        profile = radial_profile[valid]
        return radii, profile

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("L")
            img_resized = img.resize((256, 256), Image.Resampling.BILINEAR)
            img_arr = np.array(img_resized, dtype=np.float32)

            # 2D Fast Fourier Transform
            f = np.fft.fft2(img_arr)
            fshift = np.fft.fftshift(f)
            abs_shift = np.abs(fshift) + 1e-8
            power_spectrum = abs_shift ** 2
            log_magnitude_spectrum = 20 * np.log10(abs_shift)

            # 1. Measure center vs high-frequency periphery energy ratio
            h, w = log_magnitude_spectrum.shape
            cy, cx = h // 2, w // 2
            
            # Low-frequency center box (radius 32)
            low_freq = log_magnitude_spectrum[cy-32:cy+32, cx-32:cx+32]
            
            # High-frequency perimeter
            mask = np.ones((h, w), dtype=bool)
            mask[cy-48:cy+48, cx-48:cx+48] = False
            high_freq = log_magnitude_spectrum[mask]

            low_mean = float(np.mean(low_freq))
            high_mean = float(np.mean(high_freq))
            high_std = float(np.std(high_freq))

            # 2. Periodic peak detection (GAN grid artifact index)
            threshold = high_mean + 2.5 * high_std
            peak_count = int(np.sum(high_freq > threshold))
            high_to_low_ratio = high_mean / (low_mean + 1e-6)

            # 3. Radial Power-Law Decay Analysis (Natural Image 1/f^alpha Baseline)
            # Computed on true natural-log power spectrum ln(P(r))
            radii, radial_profile = self._compute_radial_profile(power_spectrum)
            
            # Fit ln(P(r)) vs ln(r) in mid-to-high frequencies (r in [8, 96])
            fit_mask = (radii >= 8) & (radii <= 96)
            if np.sum(fit_mask) > 10:
                log_r = np.log(radii[fit_mask].astype(np.float32))
                log_p = np.log(radial_profile[fit_mask] + 1e-8)
                
                # Linear regression: ln(P(r)) = -alpha * ln(r) + C
                poly = np.polyfit(log_r, log_p, 1)
                spectral_decay_slope = float(-poly[0])
                
                # Goodness-of-fit / Residual variance from natural linear decay
                fitted = poly[0] * log_r + poly[1]
                spectral_residual = float(np.mean((log_p - fitted) ** 2))
            else:
                spectral_decay_slope = 2.0
                spectral_residual = 0.05

            # Evaluation against Natural Image Physics:
            # - Optical camera decay slope alpha: typically 1.6 to 3.4
            # - AI generative flattening slope: alpha < 1.35 (abnormally flat high frequencies)
            # - Synthetic non-monotonic bump residual: spectral_residual > 0.45
            is_slope_anomalous = (spectral_decay_slope < 1.35) or (spectral_decay_slope > 4.8)
            is_residual_anomalous = spectral_residual > 0.45
            is_peak_anomalous = (peak_count > 250) and (high_to_low_ratio > 0.78) and is_residual_anomalous

            is_synthetic_pattern = (is_slope_anomalous and is_residual_anomalous) or is_peak_anomalous

            # Continuous anomaly mapping
            peak_score = min(1.0, max(0.0, (peak_count - 150) / 400.0))
            if high_to_low_ratio <= 0.75:
                peak_score *= 0.40

            slope_score = min(1.0, max(0.0, (1.8 - spectral_decay_slope) / 0.8)) if spectral_decay_slope < 1.8 else 0.0
            
            if is_synthetic_pattern:
                spectral_anomaly_score = max(0.65, min(0.95, max(peak_score, slope_score)))
            else:
                # Natural optical frequency roll-off
                spectral_anomaly_score = float(round(min(0.32, max(0.03, peak_score * 0.5 + slope_score * 0.3)), 3))

            finding_text = (
                "Periodic grid artifacts and high-frequency radial power-law deviation detected in 2D DFT spectrum."
                if is_synthetic_pattern
                else "Uniform radial frequency roll-off consistent with optical lens capture."
            )

            return {
                "spectral_anomaly_score": float(round(spectral_anomaly_score, 3)),
                "peak_count": peak_count,
                "spectral_decay_slope": float(round(spectral_decay_slope, 2)),
                "spectral_residual": float(round(spectral_residual, 3)),
                "is_synthetic_pattern": is_synthetic_pattern,
                "status": "APPLIED",
                "finding": finding_text,
                "note": finding_text
            }

        except Exception as e:
            return {
                "spectral_anomaly_score": 0.05,
                "peak_count": 0,
                "spectral_decay_slope": 2.0,
                "spectral_residual": 0.05,
                "is_synthetic_pattern": False,
                "status": "FALLBACK",
                "finding": f"Frequency analysis fallback: {str(e)}",
                "note": f"Frequency analysis fallback: {str(e)}"
            }
