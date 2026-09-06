import time
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
import numpy as np
import torch
import torchvision.models as models

load_dotenv()

from shared.schemas.detection_result import (
    DetectionResult,
    EvidenceItem,
    ModuleEnum,
    StatusEnum,
    NativeScoreSemanticsEnum
)
from models.image_deepfake.preprocessing.transforms import process_image_bytes
from models.image_deepfake.explainability.grad_cam import GradCAM
from models.image_deepfake.forensics.frequency_analyzer import FrequencyAnalyzer
from models.image_deepfake.forensics.ela_analyzer import ELAAnalyzer
from models.image_deepfake.forensics.noise_analyzer import NoiseAnalyzer
from models.image_deepfake.forensics.face_analyzer import FaceAnalyzer
from models.image_deepfake.forensics.pixel_morphing_analyzer import PixelMorphingAnalyzer
from models.image_deepfake.forensics.gabor_analyzer import GaborTextureAnalyzer
from models.image_deepfake.forensics.scene_analyzer import SceneContextAnalyzer
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer
from models.image_deepfake.forensics.watermark_analyzer import WatermarkIconAnalyzer, WatermarkAnalyzer
from models.image_deepfake.forensics.recompression_analyzer import RecompressionAnalyzer
from models.image_deepfake.forensics.physics_eye_reflection_analyzer import PhysicsEyeReflectionAnalyzer
from models.image_deepfake.forensics.geometry_physics_analyzer import GeometryPhysicsAnalyzer
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient
from models.image_deepfake.inference.local_vit_detector import LocalViTDeepfakeDetector
from models.image_deepfake.inference.lm_studio_vision_client import LMStudioVisionClient

logger = logging.getLogger("trustnet.detector")


class BaseDetector:
    pass


class EfficientNetDetector(BaseDetector):
    """
    Production Multi-Signal Forensic Image Deepfake Detector.
    Fuses spatial convolutional neural representations (EfficientNet-B0), Hugging Face transformer models,
    2D Fourier frequency residuals (FFT with 1/f^alpha baseline), Gabor multi-orientation texture bank,
    Error Level Analysis (ELA), PRNU sensor pattern noise, Face X-Ray boundary analysis,
    sub-pixel CFA micro-particle morphing, and semantic scene context (Nature, Architecture, Anime, Objects).
    """

    def __init__(self, enable_explainability: bool = True):
        try:
            weights = models.EfficientNet_B0_Weights.DEFAULT
            self.model = models.efficientnet_b0(weights=weights)
        except Exception:
            self.model = models.efficientnet_b0(pretrained=True)
            
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.enable_explainability = enable_explainability
        
        if self.enable_explainability:
            self.grad_cam = GradCAM(self.model)
        else:
            self.grad_cam = None

        self.freq_analyzer = FrequencyAnalyzer()
        self.ela_analyzer = ELAAnalyzer()
        self.noise_analyzer = NoiseAnalyzer()
        self.face_analyzer = FaceAnalyzer()
        self.pixel_analyzer = PixelMorphingAnalyzer()
        self.gabor_analyzer = GaborTextureAnalyzer()
        self.scene_analyzer = SceneContextAnalyzer()
        self.metadata_analyzer = MetadataAnalyzer()
        self.watermark_analyzer = WatermarkIconAnalyzer()
        self.recompression_analyzer = RecompressionAnalyzer()
        self.physics_analyzer = PhysicsEyeReflectionAnalyzer()
        self.geometry_analyzer = GeometryPhysicsAnalyzer()
        self.hf_client = HuggingFaceDeepfakeClient()
        self.local_vit = LocalViTDeepfakeDetector()
        self.lm_studio_client = LMStudioVisionClient()

    def predict(self, input_data: bytes, scan_id: Optional[str] = None, filename: Optional[str] = None) -> DetectionResult:
        start_time = time.time()
        
        if scan_id is None:
            scan_id = str(uuid.uuid4())

        try:
            # 1. Base Semantic, Provenance & Independent Forensic Analyzers (Parallel Thread Pool)
            with ThreadPoolExecutor(max_workers=6) as executor:
                future_scene = executor.submit(self.scene_analyzer.analyze, input_data)
                future_meta = executor.submit(self.metadata_analyzer.analyze, input_data, filename)
                future_watermark = executor.submit(self.watermark_analyzer.analyze, input_data)
                future_recomp = executor.submit(self.recompression_analyzer.analyze, input_data)
                future_face = executor.submit(self.face_analyzer.analyze, input_data)
                future_freq = executor.submit(self.freq_analyzer.analyze, input_data)
                future_pixel = executor.submit(self.pixel_analyzer.analyze, input_data)
                future_gabor = executor.submit(self.gabor_analyzer.analyze, input_data)
                future_ela = executor.submit(self.ela_analyzer.analyze, input_data)
                future_noise = executor.submit(self.noise_analyzer.analyze, input_data)

                scene_res = future_scene.result()
                meta_res = future_meta.result()
                watermark_res = future_watermark.result()
                recompression_res = future_recomp.result()
                face_res = future_face.result()
                freq_res = future_freq.result()
                pixel_res = future_pixel.result()
                gabor_res = future_gabor.result()
                ela_res = future_ela.result()
                noise_res = future_noise.result()

            logger.info("[FORENSICS] Metadata complete")
            logger.info("[FORENSICS] Compression complete")
            logger.info("[FORENSICS] ELA complete")
            logger.info("[FORENSICS] Noise analysis complete")

            already_recompressed = bool(recompression_res.get("already_recompressed", False))
            scene_type = scene_res.get("scene_type", "general_object")
            scene_label = scene_res.get("scene_label", "General Media / Photographic Content")
            is_digital_art = scene_type in ["anime_illustration", "digital_art"]
            is_screenshot = scene_type == "screenshot"

            # 2. Face Detection & Gating
            has_face = bool(face_res.get("has_face", False))

            # 3. Optics / Geometry conditional branch
            if has_face:
                physics_res = self.physics_analyzer.analyze(input_data)
                geometry_res = {
                    "status": "SKIPPED",
                    "is_geometry_violation": False,
                    "geometry_anomaly_score": 0.0,
                    "finding": "Human face subject detected; 3D structural perspective analysis skipped in favor of facial forensics."
                }
            else:
                physics_res = {
                    "status": "SKIPPED",
                    "is_physics_violation": False,
                    "physics_anomaly_score": 0.0,
                    "finding": "No human eyes detected; corneal specular reflection parallax analysis skipped."
                }
                geometry_res = self.geometry_analyzer.analyze(input_data)

            # External Transformer inference (dual-model: face specialist vs general synthetic detector + local fallback)
            hf_res = self.hf_client.predict(input_data, has_face=has_face, scene_type=scene_type)
            if not hf_res.get("is_hf_applied"):
                hf_res = self.local_vit.predict(input_data, has_face=has_face, scene_type=scene_type)

            # 4. LM Studio Local Vision Reasoning with Compact Forensic Evidence
            compact_evidence = {
                "has_face": has_face,
                "face_count": face_res.get("face_count", 0),
                "face_boundary_anomaly_score": face_res.get("boundary_anomaly_score", 0.0),
                "physics_anomaly_score": physics_res.get("physics_anomaly_score", 0.0),
                "geometry_anomaly_score": geometry_res.get("geometry_anomaly_score", 0.0),
                "spectral_anomaly_score": freq_res.get("spectral_anomaly_score", 0.0),
                "ela_anomaly_score": ela_res.get("ela_anomaly_score", 0.0),
                "noise_anomaly_score": noise_res.get("noise_anomaly_score", 0.0),
                "pixel_morphing_score": pixel_res.get("pixel_morphing_score", 0.0),
                "gabor_anomaly_score": gabor_res.get("gabor_anomaly_score", 0.0),
                "is_watermark_found": watermark_res.get("is_watermark_found", False),
                "already_recompressed": already_recompressed,
                "metadata_ai_found": meta_res.get("is_ai_signature_found", False),
            }
            vision_res = self.lm_studio_client.analyze(
                image_bytes=input_data,
                forensic_evidence=compact_evidence,
                scene_type=scene_type
            )

            # 5. Extract deep CNN feature embeddings via PyTorch EfficientNet-B0 backbone
            tensor = process_image_bytes(input_data).to(self.device)
            with torch.no_grad():
                features = self.model.features(tensor)
                feature_variance = float(torch.var(features).item())

            # 6. Scientific Multi-Signal Conditional Fusion
            anomaly_weights: List[Tuple[float, float]] = []

            # Adaptive Recompression Scaling: When heavy social recompression (8x8 DCT) is detected,
            # single-generation physical heuristics (FFT, CFA, Gabor, ELA, PRNU) are flattened.
            # Downweight this cluster by 0.50x and shift authority to ML classifiers, watermark, and scene.
            phys_scale = 0.50 if already_recompressed else 1.0

            # Frequency DFT (radial power-law baseline + periodic spikes)
            freq_w = (0.12 if is_digital_art else 0.20) * phys_scale
            anomaly_weights.append((freq_res["spectral_anomaly_score"], freq_w))
            
            # Sub-Pixel CFA & micro-jitter
            pixel_w = (0.12 if is_digital_art else 0.16) * phys_scale
            anomaly_weights.append((pixel_res["pixel_morphing_score"], pixel_w))

            # Multi-scale Gabor Texture Bank
            gabor_w = (0.08 if (is_digital_art or is_screenshot) else 0.16) * phys_scale
            anomaly_weights.append((gabor_res["gabor_anomaly_score"], gabor_w))

            # Compression ELA: De-emphasized for digital art / screenshots / recompressed
            ela_w = (0.05 if (is_digital_art or is_screenshot) else 0.12) * phys_scale
            anomaly_weights.append((ela_res["ela_anomaly_score"], ela_w))

            # Sensor Pattern Noise: De-emphasized for non-camera digital graphics / recompressed
            noise_w = (0.04 if (is_digital_art or is_screenshot) else 0.10) * phys_scale
            anomaly_weights.append((noise_res["noise_anomaly_score"], noise_w))

            # Facial boundary & Corneal optics (Only when applied)
            if face_res.get("status") == "APPLIED":
                anomaly_weights.append((face_res["boundary_anomaly_score"], 0.25))

            if physics_res.get("status") == "APPLIED":
                anomaly_weights.append((physics_res["physics_anomaly_score"], 0.20))

            # Geometry Physics (Only when applied)
            if geometry_res.get("status") == "APPLIED":
                anomaly_weights.append((geometry_res["geometry_anomaly_score"], 0.18))

            # Semantic scene context: weight shifted up when recompressed
            scene_w = 0.35 if is_digital_art else (0.22 if already_recompressed else 0.12)
            anomaly_weights.append((scene_res["scene_anomaly_score"], scene_w))

            # External / Local Vision Transformer Model
            if hf_res.get("is_hf_applied", False):
                hf_anomaly = float(hf_res.get("hf_risk_score", 50.0)) / 100.0
                hf_w = (0.45 if already_recompressed else 0.35) if is_digital_art else (0.42 if already_recompressed else 0.30)
                anomaly_weights.append((hf_anomaly, hf_w))

            # LM Studio Local Vision Reasoning (Only when applied)
            vision_anomaly = 0.50
            if vision_res.get("status") == "APPLIED":
                verdict_str = vision_res.get("visual_verdict", "inconclusive").lower()
                vision_conf = float(vision_res.get("confidence", 0.75))
                if verdict_str == "suspicious":
                    vision_anomaly = max(0.60, min(0.95, vision_conf))
                elif verdict_str == "authentic":
                    vision_anomaly = max(0.05, min(0.40, 1.0 - vision_conf))
                else:
                    vision_anomaly = 0.50
                
                vision_w = 0.20 if is_digital_art else 0.18
                anomaly_weights.append((vision_anomaly, vision_w))

            # Pixel-Level Corner Watermark Icon Scanner (standard weighted vote: 0.15)
            anomaly_weights.append((float(watermark_res.get("watermark_anomaly_score", 0.0)), 0.15))

            # Compute normalized weighted average
            total_weight = sum(w for _, w in anomaly_weights)
            weighted_anomaly = sum(s * w for s, w in anomaly_weights) / max(1e-6, total_weight)

            # Evidential Max-Pooling Floor & Strong Signals
            max_active_signal = max((s for s, _ in anomaly_weights), default=0.0)
            is_hf_real = hf_res.get("is_hf_applied", False) and (float(hf_res.get("hf_risk_score", 50.0)) <= 15.0)

            # Count genuinely independent strong synthetic indicators across distinct physical domains
            strong_signals = []
            strong_domains = set()

            # Watermark corroboration (participates as normal strong signal/domain, NO hard override)
            if watermark_res.get("is_watermark_found") and watermark_res.get("watermark_anomaly_score", 0.0) >= 0.60:
                strong_signals.append(f"Visual watermark icon detected ({watermark_res.get('watermark_location')})")
                strong_domains.add("visual_provenance")

            if freq_res.get("is_synthetic_pattern") and freq_res.get("spectral_anomaly_score", 0) >= 0.60:
                strong_signals.append("2D Fourier periodic grid artifacts / 1/f^alpha deviation")
                strong_domains.add("frequency")

            if pixel_res.get("is_morphing_detected") and pixel_res.get("pixel_morphing_score", 0) >= 0.60:
                strong_signals.append("Sub-pixel CFA demosaicing discontinuity")
                strong_domains.add("sensor_microstructure")

            if gabor_res.get("is_texture_anomalous") and gabor_res.get("gabor_anomaly_score", 0) >= 0.60:
                strong_signals.append("Multi-scale Gabor filter bank texture anomaly")
                strong_domains.add("spatial_texture")

            if noise_res.get("is_synthetic_noise") and noise_res.get("noise_anomaly_score", 0) >= 0.60:
                strong_signals.append("Non-physical sensor noise distribution")
                strong_domains.add("sensor_microstructure")

            if ela_res.get("is_anomalous") and ela_res.get("ela_anomaly_score", 0) >= 0.60:
                strong_signals.append("Non-uniform Error Level Analysis surface across foreground and background")
                strong_domains.add("compression_splicing")

            if face_res.get("is_manipulated_face") and face_res.get("boundary_anomaly_score", 0) >= 0.60:
                strong_signals.append("Facial boundary blending discontinuity (Face X-Ray)")
                strong_domains.add("face_anatomy")

            if physics_res.get("is_physics_violation") and physics_res.get("physics_anomaly_score", 0) >= 0.60:
                strong_signals.append("Asymmetrical corneal specular reflection vectors")
                strong_domains.add("physical_optics_geometry")

            if geometry_res.get("is_geometry_violation") and geometry_res.get("geometry_anomaly_score", 0) >= 0.60:
                strong_signals.append("Geometric structural asymmetry / missing contact shadow")
                strong_domains.add("physical_optics_geometry")

            if is_digital_art and scene_res.get("scene_anomaly_score", 0.0) >= 0.70:
                strong_signals.append(f"AI Digital Art & Latent Diffusion Texture: {scene_res.get('finding')}")
                strong_domains.add("generative_art_synthesis")

            if hf_res.get("is_hf_applied", False) and float(hf_res.get("hf_risk_score", 0.0)) >= 70.0:
                model_name_str = hf_res.get("model_name") or "Transformer"
                strong_signals.append(f"Vision Transformer ({model_name_str}) high synthetic probability")
                strong_domains.add("learned_deep_learning")

            if vision_res.get("status") == "APPLIED":
                v_verdict = vision_res.get("visual_verdict", "inconclusive").lower()
                v_conf = float(vision_res.get("confidence", 0.0))
                if v_verdict == "suspicious" and v_conf >= 0.70:
                    model_tag = vision_res.get("model_name") or "Local Vision"
                    strong_signals.append(f"LM Studio Local Vision ({model_tag}) visual anomaly detection")
                    strong_domains.add("visual_semantic_reasoning")

            # Distinct physical domain count (excludes learned neural classifiers and vision model)
            physical_domains = strong_domains - {"learned_deep_learning", "visual_semantic_reasoning"}
            physical_domain_count = len(physical_domains)

            strong_domain_count = len(strong_domains)
            strong_signal_count = len(strong_signals)
            if meta_res.get("is_ai_signature_found"):
                strong_signal_count += 3
                strong_domains.add("provenance_metadata")
                strong_domain_count += 2
                physical_domain_count += 2

            if max_active_signal >= 0.75 and not is_hf_real:
                weighted_anomaly = max(weighted_anomaly, max_active_signal * 0.85)

            # Cross-Domain Consistency Score (CDCF): Measures cross-modal agreement
            # across Spatial (Gabor/CFA/Noise), Frequency (FFT), Compression (ELA), ML (HF), and Vision
            domain_scores = [
                (pixel_res["pixel_morphing_score"] + gabor_res["gabor_anomaly_score"] + noise_res["noise_anomaly_score"]) / 3.0,
                freq_res["spectral_anomaly_score"],
                ela_res["ela_anomaly_score"]
            ]
            if hf_res.get("is_hf_applied"):
                domain_scores.append(float(hf_res.get("hf_risk_score", 50.0)) / 100.0)
            if vision_res.get("status") == "APPLIED":
                domain_scores.append(vision_anomaly)

            cross_domain_spread = float(np.std(domain_scores))
            cross_domain_consistency = float(round(max(0.60, min(0.98, 1.0 - cross_domain_spread * 0.45)), 2))

            # Multi-Vector Corroboration Calibration (Requires >= 2 Distinct Physical Domains):
            is_hf_fake = hf_res.get("is_hf_applied", False) and (float(hf_res.get("hf_risk_score", 50.0)) >= 75.0)
            is_vision_real = (vision_res.get("status") == "APPLIED" and 
                              vision_res.get("visual_verdict") == "authentic" and 
                              float(vision_res.get("confidence", 0.0)) >= 0.75)
            is_vision_fake = (vision_res.get("status") == "APPLIED" and 
                              vision_res.get("visual_verdict") == "suspicious" and 
                              float(vision_res.get("confidence", 0.0)) >= 0.75)
            ai_model_flags_fake = is_hf_fake or is_vision_fake
            ai_model_confirms_real = is_hf_real or is_vision_real
            is_contradiction = False

            # 1. Immediate override for deterministic AI provenance markers (ChatGPT / DALL-E / Midjourney / prompts in metadata)
            if meta_res.get("is_ai_signature_found"):
                weighted_anomaly = max(0.96, weighted_anomaly)
                is_contradiction = False
            else:
                # 2. Evidential Multimodal Corroboration & Calibration:

                # (a) High-Confidence Authentic Capture:
                # When dedicated ViT certifies Real (>=75%) AND zero physical anomalies exist AND no face boundary seam:
                # The photo is physically genuine. A subjective VL model hallucination (e.g. ambient indoor lighting)
                # must not flip an authentic camera photo to fake.
                if is_hf_real and physical_domain_count == 0 and not face_res.get("is_manipulated_face"):
                    weighted_anomaly = min(0.18, weighted_anomaly)
                    if is_vision_fake:
                        is_contradiction = True

                # (b) Facial boundary discontinuity is direct physical proof of face-swap / synthetic composition:
                elif face_res.get("is_manipulated_face") and float(face_res.get("boundary_anomaly_score", 0.0)) >= 0.65:
                    weighted_anomaly = max(0.68, weighted_anomaly)
                    if is_hf_real:
                        is_contradiction = True

                # (c) Two or more independent physical domains corroborate manipulation:
                elif physical_domain_count >= 2:
                    weighted_anomaly = max(0.72, min(0.98, weighted_anomaly * 1.15))
                    if is_hf_real:
                        is_contradiction = True

                # (d) Both AI models flag fake, or model fake is corroborated by at least 1 physical domain:
                elif (is_hf_fake and is_vision_fake) or (ai_model_flags_fake and physical_domain_count >= 1):
                    weighted_anomaly = max(0.70, weighted_anomaly)

                # (e) Visual Reasoning (LM Studio Vision) flags fake, and ViT does not strongly certify real:
                elif is_vision_fake and not is_hf_real:
                    weighted_anomaly = max(0.68, weighted_anomaly)

                # (f) AI model says fake, but all physical forensic checks confirm natural camera capture (0 physical anomalies):
                elif ai_model_flags_fake and physical_domain_count == 0:
                    is_contradiction = True
                    # Do not force fake; keep in cautious borderline zone
                    weighted_anomaly = max(0.48, min(0.54, weighted_anomaly))

                # (g) Clear authentic capture: model confirms real and no physical boundary anomalies:
                elif ai_model_confirms_real and physical_domain_count <= 1 and not face_res.get("is_manipulated_face"):
                    weighted_anomaly = min(0.20, weighted_anomaly)

                # (h) Natural lens and sensor verified with zero physical anomalies:
                elif physical_domain_count == 0 and max_active_signal < 0.45:
                    weighted_anomaly = min(0.18, weighted_anomaly)

                # (i) Flag contradiction between neural classifiers if they strongly disagree:
                if (is_hf_real and is_vision_fake) or (is_hf_fake and is_vision_real):
                    is_contradiction = True

            logger.info("[FUSION] Evidence combined")

            # Calculate Native Score P(REAL) in [0.01, 0.99]
            native_score = float(round(max(0.01, min(0.99, 1.0 - weighted_anomaly)), 4))
            risk_score = float(round((1.0 - native_score) * 100.0, 2))

            # Confidence is derived from the variance/consistency of active signals
            active_scores = [s for s, _ in anomaly_weights]
            score_spread = float(np.std(active_scores)) if len(active_scores) > 1 else 0.1
            confidence = float(round(max(0.70, min(0.98, 0.92 - score_spread * 0.35)), 2))

            # 4-Level Semantic Result Structure:
            # 0.00 - 24.99: AUTHENTIC (Green)
            # 25.00 - 47.99: LIKELY_AUTHENTIC (Sky/Cyan)
            # 48.00 - 54.00: UNCERTAIN (Amber, only true dead-splits where evidence is genuinely balanced)
            # 52.01 - 100.0: LIKELY_AI_MANIPULATED (Red)
            if (46.0 <= risk_score <= 54.0) and is_contradiction:
                verdict = "UNCERTAIN"
                label = "uncertain"
            elif risk_score > 52.0:
                verdict = "LIKELY_AI_MANIPULATED"
                label = "fake"
            elif risk_score >= 25.0:
                verdict = "LIKELY_AUTHENTIC"
                label = "real"
            else:
                verdict = "AUTHENTIC"
                label = "real"

            # Dynamic "Why This Result" Explanations:
            why_reasons: List[str] = []

            # 1. Deterministic AI Provenance Flag (Top priority)
            if meta_res.get("is_ai_signature_found"):
                why_reasons.append(f"Deterministic AI generator signature detected ({meta_res.get('generator_name')}).")

            if is_contradiction:
                why_reasons.append("Conflicting Evidence: Learned AI models and local physical forensic analyzers disagree. Manual verification recommended.")

            # Vision Reasoning (LM Studio Local Vision)
            if vision_res.get("status") == "APPLIED":
                simple_exp = vision_res.get("simple_explanation")
                if simple_exp:
                    why_reasons.append(f"Visual reasoning: {simple_exp}")
                elif vision_res.get("observations"):
                    why_reasons.append(f"Visual reasoning: {vision_res['observations'][0]}")
            else:
                why_reasons.append("Vision analysis unavailable. Result is based on available forensic checks.")

            if hf_res.get("is_hf_applied", False):
                hf_risk_val = float(hf_res.get("hf_risk_score", 50.0))
                if hf_risk_val <= 15.0:
                    why_reasons.append(f"Vision Transformer AI model indicates authentic photography ({100-hf_risk_val:.1f}% real confidence).")
                elif hf_risk_val >= 70.0:
                    why_reasons.append(f"Vision Transformer AI model indicates high synthetic deepfake probability ({hf_risk_val:.1f}% risk).")

            if is_digital_art and scene_res.get("scene_anomaly_score", 0.0) >= 0.60:
                why_reasons.append(f"Scene analysis: {scene_res.get('finding')}")

            if freq_res.get("is_synthetic_pattern") and freq_res.get("spectral_anomaly_score", 0) >= 0.50:
                why_reasons.append("2D Fourier spectrum exhibits periodic grid spikes / un-natural frequency energy concentration.")
            elif not is_digital_art:
                why_reasons.append("2D Fourier power spectrum follows natural optical lens 1/f^alpha roll-off.")

            if pixel_res.get("is_morphing_detected") and pixel_res.get("pixel_morphing_score", 0) >= 0.50:
                why_reasons.append("Sub-pixel Bayer CFA correlation broken (indicates synthetic diffusion/upscaling).")
            elif not is_digital_art:
                why_reasons.append("Sub-pixel Bayer CFA demosaicing and micro-edge continuity verified.")

            if ela_res.get("is_anomalous") and ela_res.get("ela_anomaly_score", 0) >= 0.50:
                why_reasons.append("Error Level Analysis detected non-uniform compression disparities consistent with splicing.")
            elif not is_digital_art:
                why_reasons.append("Error Level Analysis confirms homogeneous single-source compression.")

            if face_res.get("has_face"):
                if face_res.get("is_manipulated_face"):
                    why_reasons.append("Face X-Ray boundary analysis detected localized blending step gradients.")
                else:
                    why_reasons.append(f"Seamless facial skin tone and boundary transitions verified across {face_res.get('face_count')} face(s).")

            # Keep top 4 most informative reasons
            why_reasons = why_reasons[:4]

            # 7. Structured Evidence Items
            evidence: List[EvidenceItem] = []
            
            if self.enable_explainability and self.grad_cam is not None:
                grad_evidence = self.grad_cam.generate_evidence(tensor, risk_score=risk_score)
                evidence.extend(grad_evidence)

            # EfficientNet Backbone Feature note
            evidence.append(EvidenceItem(
                feature_or_region="efficientnet_spatial_backbone",
                contribution=float(round(min(1.0, feature_variance / 5.0), 2)),
                human_readable_note=f"EfficientNet-B0 extracted 1280-dim convolutional feature embeddings (spatial variance: {feature_variance:.2f})."
            ))

            if vision_res.get("status") == "APPLIED":
                evidence.append(EvidenceItem(
                    feature_or_region=f"lm_studio_vision ({vision_res.get('visual_verdict', 'inconclusive')})",
                    contribution=float(round(vision_anomaly, 2)),
                    human_readable_note=vision_res.get("simple_explanation") or f"Visual reasoning identified: {'; '.join(vision_res.get('observations', [])[:2])}"
                ))

            if hf_res.get("is_hf_applied", False):
                evidence.append(EvidenceItem(
                    feature_or_region="huggingface_transformer",
                    contribution=float(round(hf_res.get("hf_risk_score", 50.0) / 100.0, 2)),
                    human_readable_note=hf_res.get("note", f"Evaluated against Hugging Face {getattr(self.hf_client, 'face_model_name', getattr(self.hf_client, 'model_name', 'Transformer'))}.")
                ))

            evidence.append(EvidenceItem(
                feature_or_region="semantic_scene_context",
                contribution=float(round(scene_res["scene_anomaly_score"], 2)),
                human_readable_note=f"Scene classified as [{scene_res['scene_label']}]: {scene_res['finding']}"
            ))

            if watermark_res.get("is_watermark_found"):
                evidence.append(EvidenceItem(
                    feature_or_region=f"visual_watermark_icon ({watermark_res.get('watermark_location', 'corner')})",
                    contribution=float(round(watermark_res.get("watermark_anomaly_score", 0.85) * 0.15, 2)),
                    human_readable_note=watermark_res.get("finding", "Visual watermark icon detected in image corner.")
                ))

            if meta_res.get("metadata_anomaly_score", 0) > 0.1:
                evidence.append(EvidenceItem(
                    feature_or_region="provenance_metadata",
                    contribution=float(round(meta_res["metadata_anomaly_score"], 2)),
                    human_readable_note=meta_res["finding"]
                ))

            evidence.append(EvidenceItem(
                feature_or_region="subpixel_morphing_cfa",
                contribution=float(round(pixel_res["pixel_morphing_score"], 2)),
                human_readable_note=pixel_res["note"]
            ))

            evidence.append(EvidenceItem(
                feature_or_region="gabor_wavelet_textures",
                contribution=float(round(gabor_res["gabor_anomaly_score"], 2)),
                human_readable_note=gabor_res["finding"]
            ))

            evidence.append(EvidenceItem(
                feature_or_region="fft_spectral_residuals",
                contribution=float(round(freq_res["spectral_anomaly_score"], 2)),
                human_readable_note=freq_res["finding"]
            ))

            evidence.append(EvidenceItem(
                feature_or_region="compression_error_variance",
                contribution=float(round(ela_res["ela_anomaly_score"], 2)),
                human_readable_note=ela_res["note"]
            ))

            evidence.append(EvidenceItem(
                feature_or_region="sensor_noise_consistency",
                contribution=float(round(noise_res["noise_anomaly_score"], 2)),
                human_readable_note=noise_res["note"]
            ))

            if face_res.get("status") == "APPLIED":
                evidence.append(EvidenceItem(
                    feature_or_region="facial_boundary_warping",
                    contribution=float(round(face_res["boundary_anomaly_score"], 2)),
                    human_readable_note=face_res["finding"] or "Facial landmark boundary evaluation complete."
                ))
                
                if physics_res.get("status") == "APPLIED":
                    evidence.append(EvidenceItem(
                        feature_or_region="physics_corneal_specular_reflection",
                        contribution=float(round(physics_res["physics_anomaly_score"], 2)),
                        human_readable_note=physics_res["finding"]
                    ))

            if geometry_res.get("status") == "APPLIED":
                evidence.append(EvidenceItem(
                    feature_or_region="physics_3d_geometry_support",
                    contribution=float(round(geometry_res["geometry_anomaly_score"], 2)),
                    human_readable_note=geometry_res["finding"]
                ))

            # 8. Complete Analyzers Telemetry List
            analyzers = [
                {
                    "name": "EfficientNet-B0 Convolutional Backbone",
                    "category": "primary_ml",
                    "status": "APPLIED",
                    "finding": f"Extracted 1280-dim convolutional spatial representations (variance: {feature_variance:.2f}). Deepfake head pending dedicated training."
                },
                {
                    "name": f"LM Studio Local Vision ({vision_res.get('model_name', 'Qwen-VL')})",
                    "category": "local_vision_reasoning",
                    "status": vision_res.get("status", "UNAVAILABLE"),
                    "reason": None if vision_res.get("status") == "APPLIED" else "LM Studio local endpoint not running or model not loaded; forensic analysis completed using deterministic scanners.",
                    "finding": vision_res.get("simple_explanation") or (
                        f"Visual verdict: {vision_res.get('visual_verdict', 'inconclusive')} "
                        f"(confidence: {vision_res.get('confidence', 0.0)*100:.0f}%). "
                        f"{len(vision_res.get('observations', []))} visual observation(s)."
                        if vision_res.get("status") == "APPLIED"
                        else "Vision analysis unavailable. Result is based on available forensic checks."
                    )
                },
                {
                    "name": f"Hugging Face AI Hub ({hf_res.get('model_name', self.hf_client.face_model_name)})",
                    "category": "primary_ml",
                    "status": "APPLIED" if hf_res.get("is_hf_applied") else "SKIPPED",
                    "reason": None if hf_res.get("is_hf_applied") else "Hugging Face API unavailable or rate-limited; deferred to local forensic engines.",
                    "finding": hf_res.get("note")
                },
                {
                    "name": f"Semantic Scene Context: {scene_res['scene_label']}",
                    "category": "semantic_forensics",
                    "status": "APPLIED",
                    "finding": scene_res["finding"]
                },
                {
                    "name": "Provenance & Metadata Forensics",
                    "category": "metadata_forensics",
                    "status": "APPLIED",
                    "finding": meta_res["finding"]
                },
                {
                    "name": "Visual Watermark Icon Scanner",
                    "category": "visual_provenance",
                    "status": watermark_res.get("status", "APPLIED"),
                    "reason": None if watermark_res.get("is_watermark_found") else "No corner watermark icon signature detected.",
                    "finding": watermark_res.get("finding")
                },
                {
                    "name": "Social Re-Compression & DCT Grid Analyzer",
                    "category": "compression_history",
                    "status": recompression_res.get("status", "APPLIED"),
                    "reason": None if already_recompressed else "Single-generation or uncompressed capture.",
                    "finding": recompression_res.get("finding")
                },
                {
                    "name": "Sub-Pixel CFA & Micro-Particle Morphing Analyzer",
                    "category": "micro_forensics",
                    "status": "APPLIED",
                    "finding": pixel_res["note"]
                },
                {
                    "name": "Multi-Scale Gabor Filter Bank Texture Analyzer",
                    "category": "texture_forensics",
                    "status": gabor_res.get("status", "APPLIED"),
                    "finding": gabor_res.get("finding")
                },
                {
                    "name": "FFT High-Frequency Residual & Radial Decay Analyzer",
                    "category": "frequency",
                    "status": freq_res.get("status", "APPLIED"),
                    "finding": freq_res.get("finding")
                },
                {
                    "name": "Error Level Analysis (ELA)",
                    "category": "compression",
                    "status": "APPLIED",
                    "finding": ela_res["note"]
                },
                {
                    "name": "Sensor Pattern Noise (PRNU)",
                    "category": "sensor_forensics",
                    "status": "APPLIED",
                    "finding": noise_res["note"]
                },
                {
                    "name": "Face Landmark & Boundary Warping (Face X-Ray)",
                    "category": "face_forensics",
                    "status": face_res["status"],
                    "reason": face_res.get("reason"),
                    "finding": face_res.get("finding")
                },
                {
                    "name": "Optics Physics: Corneal Specular Parallax",
                    "category": "physics_engine",
                    "status": physics_res["status"],
                    "reason": physics_res.get("reason"),
                    "finding": physics_res["finding"]
                },
                {
                    "name": "Geometry Physics: Support & Structural Symmetry",
                    "category": "physics_engine",
                    "status": geometry_res["status"],
                    "reason": geometry_res.get("reason"),
                    "finding": geometry_res["finding"]
                }
            ]

            processing_time_ms = int((time.time() - start_time) * 1000)

            metadata_payload = {
                "scene_label": scene_label,
                "generator_name": meta_res.get("generator_name") or meta_res.get("raw_software_tag"),
                "ai_signature_found": bool(meta_res.get("is_ai_signature_found")),
                "exif_missing": bool(meta_res.get("is_exif_missing")),
                "metadata_anomaly_score": float(meta_res.get("metadata_anomaly_score", 0.0)),
                "metadata_finding": meta_res.get("finding"),
                "feature_variance": feature_variance,
                "strong_signal_count": strong_signal_count,
                "strong_signals": strong_signals,
                "face_count": face_res.get("face_count", 0),
                "cross_domain_consistency": cross_domain_consistency,
                "gabor_anomaly_score": gabor_res.get("gabor_anomaly_score", 0.0),
                "why_reasons": why_reasons,
                "is_contradiction": is_contradiction,
                "spectral_decay_slope": freq_res.get("spectral_decay_slope", 2.0),
                "hf_model": hf_res.get("model_name"),
                "hf_risk_score": hf_res.get("hf_risk_score"),
                "hf_status": "applied" if hf_res.get("is_hf_applied") else "skipped",
                "watermark_found": bool(watermark_res.get("is_watermark_found")),
                "watermark_location": watermark_res.get("watermark_location"),
                "watermark_anomaly_score": float(watermark_res.get("watermark_anomaly_score", 0.0)),
                "already_recompressed": bool(already_recompressed),
                "recompression_score": float(recompression_res.get("recompression_score", 0.0)),
                "blockiness_ratio": float(recompression_res.get("blockiness_ratio", 1.0)),
                "lm_studio_status": vision_res.get("status", "UNAVAILABLE"),
                "lm_studio_model": vision_res.get("model_name"),
                "vision_analysis": vision_res
            }

            risk_adjective = 'CRITICAL' if risk_score >= 75 else ('HIGH' if risk_score >= 50 else ('MEDIUM' if risk_score >= 25 else 'LOW'))
            explanation_summary = f"Trust Net analyzed this [{scene_label}] across {len(active_scores)} active forensic signals. Risk Score: {risk_score:.0f}/100 ({risk_adjective} RISK, Confidence: {confidence*100:.0f}%, Consistency: {cross_domain_consistency*100:.0f}%)."

            logger.info(f"[RESULT] Final verdict generated: {verdict} (Risk: {risk_score}%, Confidence: {confidence*100:.0f}%)")

            return DetectionResult(
                scan_id=scan_id,
                module=ModuleEnum.image_deepfake,
                detector_id="image_deepfake.efficientnet_b0.v1",
                model_version="v1.0.0",
                preprocessing_version="v1.0.0",
                native_score=native_score,
                native_score_semantics=NativeScoreSemanticsEnum.probability_of_negative_class,
                risk_score=risk_score,
                confidence=confidence,
                label=label,
                status=StatusEnum.SUCCESS,
                evidence=evidence,
                analyzers=analyzers,
                has_face=has_face,
                verdict=verdict,
                explanation=explanation_summary,
                vision_analysis=vision_res,
                metadata=metadata_payload,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
                
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return DetectionResult(
                scan_id=scan_id,
                module=ModuleEnum.image_deepfake,
                detector_id="image_deepfake.efficientnet_b0.v1",
                model_version="v1.0.0",
                preprocessing_version="v1.0.0",
                native_score=0.0,
                native_score_semantics=NativeScoreSemanticsEnum.probability_of_negative_class,
                risk_score=0.0,
                confidence=0.0,
                label="error",
                status=StatusEnum.FAILED,
                evidence=[],
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_code="INFERENCE_FAILED",
                error_message=str(e)
            )
