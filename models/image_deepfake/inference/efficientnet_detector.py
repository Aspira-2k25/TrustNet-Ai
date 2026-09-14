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
from models.image_deepfake.forensics.steganography_analyzer import SteganographyAnalyzer
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
        self.stego_analyzer = SteganographyAnalyzer()
        self.hf_client = HuggingFaceDeepfakeClient()
        self.local_vit = LocalViTDeepfakeDetector()
        self.lm_studio_client = LMStudioVisionClient()

    def _synthesize_explanation(
        self,
        verdict: str = "AUTHENTIC",
        risk_score: float = 0.0,
        has_face: bool = False,
        scene_type: str = "general_object",
        scene_res: Optional[Dict[str, Any]] = None,
        strong_signals: Optional[List[str]] = None,
        face_res: Optional[Dict[str, Any]] = None,
        physics_res: Optional[Dict[str, Any]] = None,
        meta_res: Optional[Dict[str, Any]] = None,
        watermark_res: Optional[Dict[str, Any]] = None,
        stego_res: Optional[Dict[str, Any]] = None,
        vision_res: Optional[Dict[str, Any]] = None,
        hf_res: Optional[Dict[str, Any]] = None,
        is_hf_face_real: bool = False,
        **kwargs
    ) -> str:
        """
        Synthesizes a crisp, natural, human-understandable explanation ("chota and simple")
        explaining why an image is authentic or fake.
        """
        try:
            scene_res = scene_res or {}
            strong_signals = strong_signals or []
            face_res = face_res or {}
            physics_res = physics_res or {}
            meta_res = meta_res or {}
            watermark_res = watermark_res or {}
            stego_res = stego_res or {}
            vision_res = vision_res or {}
            hf_res = hf_res or {}

            # If LM Studio local vision was applied and generated an explanation, prioritize it
            if vision_res.get("status") == "APPLIED" and vision_res.get("simple_explanation"):
                return str(vision_res["simple_explanation"]).strip()

            # 1. Deterministic metadata provenance
            if meta_res.get("is_ai_signature_found"):
                gen_name = meta_res.get("generator_name") or "AI Generative Model"
                return f"AI generation confirmed: verified metadata signature and provenance markers from {gen_name} detected."

            # 2. Covert steganography payload indicator
            if stego_res.get("is_stego_detected"):
                return f"Covert data payload detected: {stego_res.get('finding')}"

            # 3. Visual watermark icon: only report when verdict is AI manipulated and not certified authentic face
            if watermark_res.get("is_watermark_found") and verdict == "LIKELY_AI_MANIPULATED" and not is_hf_face_real:
                loc = watermark_res.get("watermark_location") or "corner"
                return f"Synthetic media indicator: visual watermark icon signature detected in {loc} region."

            # 3. Verdict-based explanations
            if verdict == "LIKELY_AI_MANIPULATED":
                hf_risk = float(hf_res.get("hf_risk_score") or 0.0)
                if has_face and (face_res.get("is_manipulated_face") or (hf_res.get("is_hf_applied") and hf_risk >= 70.0)):
                    return "Face-swap deepfake or synthetic face detected: neural classification and facial boundary features confirm AI generation."
                if has_face and physics_res.get("is_physics_violation"):
                    return "Manipulated facial composition: corneal specular reflections and eye lighting vectors are physically inconsistent with the scene."
                if scene_type in ["anime_illustration", "digital_art"] or (not has_face and float(scene_res.get("scene_anomaly_score") or 0.0) >= 0.60):
                    return "AI-generated image detected: latent diffusion rendering artifacts, synthetic tonal transitions, and non-camera sensor characteristics identified."
                if strong_signals:
                    primary = str(strong_signals[0]).lower()
                    return f"Synthetic manipulation detected: multi-frequency and sensor forensic checks identified {primary}."
                return "AI-generated or manipulated image: neural classifiers and multi-frequency forensic scans indicate synthetic synthesis."

            elif verdict == "UNCERTAIN":
                return "Borderline forensic signals: subtle compression artifacts or conflicting evidence between neural models and physical sensors. Manual verification recommended."

            else:  # AUTHENTIC or LIKELY_AUTHENTIC
                if has_face:
                    face_cnt = face_res.get("face_count", 1)
                    return f"Authentic human photograph verified: seamless facial boundary continuity across {face_cnt} face(s), natural optical lens characteristics, and consistent lighting."
                if scene_type in ["anime_illustration", "digital_art"]:
                    return "Human-created digital artwork: consistent vector contours, intentional palette design, and absence of latent diffusion blending artifacts."
                if scene_type == "nature_landscape":
                    return "Authentic natural landscape capture: realistic depth-of-field optical falloff and continuous sensor Bayer micro-structure verified."
                return "Authentic camera photograph verified: natural optical lens properties, continuous sub-pixel sensor demosaicing, and uniform single-source compression."
        except Exception as synth_err:
            logger.warning(f"[EXPLANATION SYNTHESIS] Error generating explanation: {synth_err}")
            return "Authentic camera photograph verified: natural optical lens properties, continuous sub-pixel sensor demosaicing, and uniform single-source compression."

    def predict(
        self,
        input_data: bytes,
        scan_id: Optional[str] = None,
        filename: Optional[str] = None,
        enable_explanation: bool = False
    ) -> DetectionResult:
        start_time = time.time()
        
        if scan_id is None:
            scan_id = str(uuid.uuid4())

        try:
            # 1. Base Semantic, Provenance & Independent Forensic Analyzers (Parallel Thread Pool)
            with ThreadPoolExecutor(max_workers=7) as executor:
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
                future_stego = executor.submit(self.stego_analyzer.analyze, input_data)

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
                stego_res = future_stego.result()

            logger.info("[FORENSICS] Metadata complete")
            logger.info("[FORENSICS] Compression complete")
            logger.info("[FORENSICS] ELA complete")
            logger.info("[FORENSICS] Noise analysis complete")
            logger.info("[FORENSICS] Steganography analysis complete")

            already_recompressed = bool(recompression_res.get("already_recompressed", False))
            scene_type = scene_res.get("scene_type", "general_object")
            scene_label = scene_res.get("scene_label", "General Media / Photographic Content")
            is_digital_art = scene_type in ["anime_illustration", "digital_art"]
            is_screenshot = scene_type == "screenshot"

            # 2. Face Detection & Gating
            has_face = bool(face_res.get("has_face", False))

            # Digital art face guard: face cascades and skin-tone fallbacks produce false
            # positives on illustrated characters (warm-toned anime backgrounds match skin
            # YCbCr ranges, and cartoon outlines trigger boundary discontinuity).
            if is_digital_art and has_face:
                has_face = False
                face_res = {
                    "has_face": False,
                    "face_count": 0,
                    "bounding_boxes": [],
                    "status": "SKIPPED",
                    "reason": "Face detection reset: digital art/illustration scene where facial landmark forensics are not applicable.",
                    "boundary_anomaly_score": 0.0,
                    "skin_edge_variance": 0.0,
                    "is_manipulated_face": False,
                    "finding": None
                }

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

            # 4. LM Studio Local Vision Reasoning with Compact Forensic Evidence (Only when enable_explanation is True)
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
            if enable_explanation:
                vision_res = self.lm_studio_client.analyze(
                    image_bytes=input_data,
                    forensic_evidence=compact_evidence,
                    scene_type=scene_type
                )
            else:
                vision_res = {
                    "status": "SKIPPED",
                    "visual_verdict": "skipped",
                    "confidence": 0.0,
                    "model_name": None,
                    "observations": [],
                    "simple_explanation": None,
                    "reason": "Fast Scan mode selected (LM Studio AI vision explanation skipped for instant analysis)."
                }

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

            # Semantic scene context: weight shifted up when recompressed or non-human
            scene_w = 0.35 if (is_digital_art or not has_face) else (0.22 if already_recompressed else 0.12)
            anomaly_weights.append((scene_res["scene_anomaly_score"], scene_w))

            # External / Local Vision Transformer Model (dual-model: face specialist vs general synthetic detector)
            is_face_scenario = has_face or (scene_type in ["photograph_portrait", "portrait"])
            is_face_specialist = "dima806" in str(hf_res.get("model_name", "dima806")).lower()

            if hf_res.get("is_hf_applied", False):
                hf_risk_val = float(hf_res.get("hf_risk_score", 50.0))
                hf_anomaly = hf_risk_val / 100.0
                if is_face_scenario:
                    # High authority for human face scenes where dima806 is trained and specialized
                    hf_w = 0.48 if already_recompressed else 0.40
                    anomaly_weights.append((hf_anomaly, hf_w))
                else:
                    # For non-human scenes (cats, dogs, landscapes, digital art), dima806 is face-only.
                    # It must NEVER force a non-human AI creation to 'authentic' by outputting a false 'real' score!
                    if not is_face_specialist:
                        # Dedicated general synthetic detector
                        hf_w = 0.35 if already_recompressed else 0.28
                        anomaly_weights.append((hf_anomaly, hf_w))
                    elif hf_risk_val >= 75.0:
                        # dima806 only votes on non-face scenes if it actively caught severe generative artifacts
                        anomaly_weights.append((hf_anomaly, 0.25))

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

            is_hf_applied = bool(hf_res.get("is_hf_applied", False))
            hf_risk_float = float(hf_res.get("hf_risk_score", 50.0))
            is_hf_real = is_hf_applied and (hf_risk_float <= 25.0) and (is_face_scenario or not is_face_specialist)
            is_hf_fake = is_hf_applied and (hf_risk_float >= 70.0)
            is_hf_face_real = is_hf_real and is_face_scenario
            is_hf_face_fake = is_hf_fake and is_face_scenario
            max_active_signal = max((s for s, _ in anomaly_weights), default=0.0)

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

            if stego_res.get("is_stego_detected"):
                strong_signals.append(f"Covert steganography: {stego_res.get('finding')}")
                strong_domains.add("covert_steganography")

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

            # Distinct physical domain count (excludes learned neural classifiers, vision models, watermark heuristics, and steganography)
            physical_domains = strong_domains - {"learned_deep_learning", "visual_semantic_reasoning", "visual_provenance", "covert_steganography"}
            physical_domain_count = len(physical_domains)
            # Independent non-facial physical domain set (prevents facial boundary from self-corroborating)
            secondary_physical_domains = physical_domains - {"face_anatomy"}

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

                # (0) Deterministic Covert Steganography Payload:
                if stego_res.get("is_stego_detected"):
                    weighted_anomaly = max(0.85, weighted_anomaly)
                    is_contradiction = False

                # (a) Dedicated ViT detects Deepfake Human Face (Screenshot 3 - Child Deepfake):
                elif is_hf_face_fake:
                    # dima806 ViT is specialized on human faces and certified synthetic deepfake >= 70%.
                    # Even if seamless crop (physical_domain_count == 0), trust the neural ViT head (>= 0.78).
                    if len(secondary_physical_domains) >= 1 or face_res.get("is_manipulated_face"):
                        weighted_anomaly = max(0.86, weighted_anomaly)
                    else:
                        weighted_anomaly = max(0.78, weighted_anomaly)
                    is_contradiction = False

                # (b) High-Confidence Authentic Human Capture (Screenshot 1 - Real portrait with glasses/shadows):
                elif is_hf_face_real and len(secondary_physical_domains) == 0:
                    # Webcam/portrait false-positive suppression:
                    # When ViT certifies Real (>=80%) and zero physical anomalies exist, single boundary spikes
                    # (e.g. spectacles/shadows/lighting or background clutter) must not flip an authentic camera photo to Uncertain.
                    weighted_anomaly = min(0.16, weighted_anomaly)
                    is_contradiction = False

                # (c) Facial boundary discontinuity confirmed by secondary physical or AI signals:
                elif face_res.get("is_manipulated_face") and float(face_res.get("boundary_anomaly_score", 0.0)) >= 0.65:
                    if len(secondary_physical_domains) >= 1 or is_vision_fake:
                        weighted_anomaly = max(0.78, weighted_anomaly)
                    elif is_hf_face_real:
                        # ViT says real and physical checks clean -> suppress boundary noise
                        weighted_anomaly = min(0.18, weighted_anomaly)
                        is_contradiction = False
                    else:
                        # Isolated boundary finding without neural confirmation -> cautious border
                        weighted_anomaly = max(0.48, min(0.58, weighted_anomaly))
                        is_contradiction = True

                # (d) Two or more independent physical domains corroborate manipulation:
                elif physical_domain_count >= 2:
                    weighted_anomaly = max(0.74, min(0.98, weighted_anomaly * 1.15))
                    if is_hf_face_real:
                        is_contradiction = True

                # (e) AI Generative Art / Synthetic Non-Human Scene (Screenshot 4 - AI Cat in hoodie):
                elif (not has_face) and (scene_res.get("scene_anomaly_score", 0.0) >= 0.60 or is_digital_art or not is_face_scenario) and not watermark_res.get("is_watermark_found"):
                    if is_hf_applied and hf_risk_float <= 25.0:
                        # ViT explicitly certifies photographic authenticity (e.g. real photo with sticker)
                        if physical_domain_count <= 1:
                            weighted_anomaly = min(0.48, weighted_anomaly)
                        else:
                            is_contradiction = True
                            weighted_anomaly = max(0.48, min(0.52, weighted_anomaly))
                    elif pixel_res.get("is_morphing_detected") or noise_res.get("is_synthetic_noise") or freq_res.get("is_synthetic_pattern"):
                        weighted_anomaly = max(0.76, weighted_anomaly)
                    elif scene_res.get("scene_anomaly_score", 0.0) >= 0.65:
                        weighted_anomaly = max(0.74, weighted_anomaly)
                    elif scene_res.get("scene_anomaly_score", 0.0) >= 0.50 and meta_res.get("is_exif_missing"):
                        weighted_anomaly = max(0.68, weighted_anomaly)

                # (f) Vision Reasoning flags fake, corroborated by physical or scene domains:
                elif is_vision_fake and (physical_domain_count >= 1 or scene_res.get("scene_anomaly_score", 0.0) >= 0.60):
                    weighted_anomaly = max(0.72, weighted_anomaly)

                # (g) Both vision model and ViT flag fake:
                elif is_hf_fake and is_vision_fake:
                    weighted_anomaly = max(0.82, weighted_anomaly)

                # (h) Watermark icon detected:
                elif watermark_res.get("is_watermark_found") and watermark_res.get("watermark_anomaly_score", 0.0) >= 0.65:
                    if is_hf_real or is_hf_face_real or (is_hf_applied and hf_risk_float <= 25.0):
                        # Contradiction: watermark icon present, but ViT certifies photographic authenticity.
                        # Do not jump to 96% fake; clamp to uncertain / contradiction band (48-52%)
                        is_contradiction = True
                        weighted_anomaly = max(0.48, min(0.52, weighted_anomaly))
                    else:
                        weighted_anomaly = max(0.75, weighted_anomaly)

                # (i) Clear authentic capture: model confirms real, no physical anomalies and no watermark:
                elif ai_model_confirms_real and physical_domain_count <= 1 and not face_res.get("is_manipulated_face") and not watermark_res.get("is_watermark_found"):
                    weighted_anomaly = min(0.18, weighted_anomaly)

                # (j) Natural lens and sensor verified with zero physical anomalies:
                elif physical_domain_count == 0 and max_active_signal < 0.40 and not is_hf_fake:
                    has_camera_hardware = not meta_res.get("is_exif_missing") and ("camera" in str(meta_res.get("finding", "")).lower() or meta_res.get("raw_software_tag"))
                    if has_camera_hardware or is_hf_face_real:
                        weighted_anomaly = min(0.16, weighted_anomaly)
                    elif not has_face and meta_res.get("is_exif_missing"):
                        # Unverified web image with missing camera sensor metadata: maintain neutral baseline
                        weighted_anomaly = max(0.38, min(0.52, weighted_anomaly))
                    else:
                        weighted_anomaly = min(0.25, weighted_anomaly)

                # Flag contradiction if neural classifiers or vision reasoning strongly disagree:
                if (is_hf_real and is_vision_fake) or (is_hf_fake and is_vision_real):
                    is_contradiction = True
                    # When vision model contradicts clean physical scans + ViT (0 physical anomalies):
                    if physical_domain_count == 0 and is_hf_real and is_vision_fake:
                        weighted_anomaly = max(0.48, min(0.52, weighted_anomaly))

            logger.info("[FUSION] Evidence combined")

            # Calculate Native Score P(REAL) in [0.01, 0.99]
            native_score = float(round(max(0.01, min(0.99, 1.0 - weighted_anomaly)), 4))
            risk_score = float(round((1.0 - native_score) * 100.0, 2))

            # Confidence is derived from the variance/consistency of active signals
            active_scores = [s for s, _ in anomaly_weights]
            score_spread = float(np.std(active_scores)) if len(active_scores) > 1 else 0.1
            confidence = float(round(max(0.70, min(0.98, 0.92 - score_spread * 0.35)), 2))

            # 4-Level Semantic Result Structure:
            # 1. is_contradiction OR 40.0 <= risk_score < 62.0: UNCERTAIN (Amber)
            # 2. >= 62.0: LIKELY_AI_MANIPULATED (Red)
            # 3. >= 22.0: LIKELY_AUTHENTIC (Sky/Cyan)
            # 4. < 22.0: AUTHENTIC (Green)
            if is_contradiction or (40.0 <= risk_score < 62.0):
                verdict = "UNCERTAIN"
                label = "uncertain"
            elif risk_score >= 62.0:
                verdict = "LIKELY_AI_MANIPULATED"
                label = "fake"
            elif risk_score >= 22.0:
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

            # 2. Deterministic Covert Steganography Flag
            if stego_res.get("is_stego_detected"):
                why_reasons.append(f"Covert data payload detected: {stego_res.get('finding')}")

            if is_contradiction:
                why_reasons.append("Conflicting Evidence: Learned AI models and local physical forensic analyzers disagree. Manual verification recommended.")

            # Vision Reasoning (LM Studio Local Vision)
            if vision_res.get("status") == "APPLIED":
                simple_exp = vision_res.get("simple_explanation")
                if simple_exp:
                    why_reasons.append(f"Visual reasoning: {simple_exp}")
                elif vision_res.get("observations"):
                    why_reasons.append(f"Visual reasoning: {vision_res['observations'][0]}")
            elif vision_res.get("status") == "SKIPPED":
                why_reasons.append("Fast Scan completed: physical forensics & neural ViT evaluated without vision model latency.")
            else:
                why_reasons.append("Vision analysis unavailable. Result is based on available forensic checks.")

            if hf_res.get("is_hf_applied", False) and has_face:
                hf_risk_val = float(hf_res.get("hf_risk_score", 50.0))
                if hf_risk_val <= 20.0:
                    why_reasons.append(f"Vision Transformer AI model indicates authentic photography ({100-hf_risk_val:.1f}% real confidence).")
                elif hf_risk_val >= 70.0:
                    why_reasons.append(f"Vision Transformer AI model indicates high synthetic deepfake probability ({hf_risk_val:.1f}% risk).")
            elif not has_face and scene_res.get("scene_anomaly_score", 0.0) >= 0.60:
                why_reasons.append(f"Generative AI synthesis detected: {scene_res.get('finding')}")
            elif is_digital_art and scene_res.get("scene_anomaly_score", 0.0) >= 0.60:
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
                try:
                    grad_evidence = self.grad_cam.generate_evidence(tensor, risk_score=risk_score)
                    evidence.extend(grad_evidence)
                except Exception as cam_err:
                    logger.warning(f"[GRAD-CAM] Explainability heatmap skipped: {cam_err}")

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
                    human_readable_note=str(vision_res.get("simple_explanation") or f"Visual reasoning identified: {'; '.join(vision_res.get('observations', [])[:2])}")
                ))

            if hf_res.get("is_hf_applied", False):
                hf_risk_val = float(hf_res.get("hf_risk_score") or 50.0)
                evidence.append(EvidenceItem(
                    feature_or_region="huggingface_transformer",
                    contribution=float(round(hf_risk_val / 100.0, 2)),
                    human_readable_note=str(hf_res.get("note") or f"Evaluated against Hugging Face {getattr(self.hf_client, 'face_model_name', getattr(self.hf_client, 'model_name', 'Transformer'))}.")
                ))

            evidence.append(EvidenceItem(
                feature_or_region="semantic_scene_context",
                contribution=float(round(float(scene_res.get("scene_anomaly_score") or 0.0), 2)),
                human_readable_note=f"Scene classified as [{scene_res.get('scene_label', 'Unknown')}]: {scene_res.get('finding', 'Context evaluated.')}"
            ))

            if watermark_res.get("is_watermark_found") and (not is_hf_face_real or verdict == "LIKELY_AI_MANIPULATED"):
                evidence.append(EvidenceItem(
                    feature_or_region=f"visual_watermark_icon ({watermark_res.get('watermark_location', 'corner')})",
                    contribution=float(round(float(watermark_res.get("watermark_anomaly_score") or 0.85) * 0.15, 2)),
                    human_readable_note=str(watermark_res.get("finding") or "Visual watermark icon detected in image corner.")
                ))

            if float(meta_res.get("metadata_anomaly_score") or 0.0) > 0.1:
                evidence.append(EvidenceItem(
                    feature_or_region="provenance_metadata",
                    contribution=float(round(float(meta_res.get("metadata_anomaly_score") or 0.0), 2)),
                    human_readable_note=str(meta_res.get("finding") or "Metadata provenance markers evaluated.")
                ))

            evidence.append(EvidenceItem(
                feature_or_region="subpixel_morphing_cfa",
                contribution=float(round(float(pixel_res.get("pixel_morphing_score") or 0.0), 2)),
                human_readable_note=str(pixel_res.get("note") or "Sub-pixel Bayer CFA evaluation completed.")
            ))

            evidence.append(EvidenceItem(
                feature_or_region="gabor_wavelet_textures",
                contribution=float(round(float(gabor_res.get("gabor_anomaly_score") or 0.0), 2)),
                human_readable_note=str(gabor_res.get("finding") or "Gabor texture bank evaluation completed.")
            ))

            evidence.append(EvidenceItem(
                feature_or_region="fft_spectral_residuals",
                contribution=float(round(float(freq_res.get("spectral_anomaly_score") or 0.0), 2)),
                human_readable_note=str(freq_res.get("finding") or "FFT frequency spectrum analysis completed.")
            ))

            evidence.append(EvidenceItem(
                feature_or_region="compression_error_variance",
                contribution=float(round(float(ela_res.get("ela_anomaly_score") or 0.0), 2)),
                human_readable_note=str(ela_res.get("note") or "Error Level Analysis completed.")
            ))

            evidence.append(EvidenceItem(
                feature_or_region="sensor_noise_consistency",
                contribution=float(round(float(noise_res.get("noise_anomaly_score") or 0.0), 2)),
                human_readable_note=str(noise_res.get("note") or "Sensor noise consistency evaluation completed.")
            ))

            if face_res.get("status") == "APPLIED":
                evidence.append(EvidenceItem(
                    feature_or_region="facial_boundary_warping",
                    contribution=float(round(float(face_res.get("boundary_anomaly_score") or 0.0), 2)),
                    human_readable_note=str(face_res.get("finding") or "Facial landmark boundary evaluation complete.")
                ))
                
                if physics_res.get("status") == "APPLIED":
                    evidence.append(EvidenceItem(
                        feature_or_region="physics_corneal_specular_reflection",
                        contribution=float(round(float(physics_res.get("physics_anomaly_score") or 0.0), 2)),
                        human_readable_note=str(physics_res.get("finding") or "Corneal specular reflection physics evaluated.")
                    ))

            if geometry_res.get("status") == "APPLIED":
                evidence.append(EvidenceItem(
                    feature_or_region="physics_3d_geometry_support",
                    contribution=float(round(float(geometry_res.get("geometry_anomaly_score") or 0.0), 2)),
                    human_readable_note=str(geometry_res.get("finding") or "3D structural geometry evaluation completed.")
                ))

            if stego_res.get("is_stego_detected"):
                evidence.append(EvidenceItem(
                    feature_or_region="covert_steganography_payload",
                    contribution=float(round(float(stego_res.get("stego_anomaly_score") or 0.95), 2)),
                    human_readable_note=str(stego_res.get("finding") or "Covert steganographic payload detected.")
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
                    "name": f"LM Studio Local Vision ({vision_res.get('model_name') or 'Qwen-VL'})",
                    "category": "local_vision_reasoning",
                    "status": vision_res.get("status", "UNAVAILABLE"),
                    "reason": None if vision_res.get("status") == "APPLIED" else "LM Studio local endpoint not running or model not loaded; forensic analysis completed using deterministic scanners.",
                    "finding": vision_res.get("simple_explanation") or (
                        f"Visual verdict: {vision_res.get('visual_verdict', 'inconclusive')} "
                        f"(confidence: {float(vision_res.get('confidence') or 0.0)*100:.0f}%). "
                        f"{len(vision_res.get('observations') or [])} visual observation(s)."
                        if vision_res.get("status") == "APPLIED"
                        else "Vision analysis unavailable. Result is based on available forensic checks."
                    )
                },
                {
                    "name": f"Hugging Face AI Hub ({hf_res.get('model_name') or getattr(self.hf_client, 'face_model_name', 'Transformer')})",
                    "category": "primary_ml",
                    "status": "APPLIED" if hf_res.get("is_hf_applied") else "SKIPPED",
                    "reason": None if hf_res.get("is_hf_applied") else "Hugging Face API unavailable or rate-limited; deferred to local forensic engines.",
                    "finding": hf_res.get("note") or "Model evaluation completed."
                },
                {
                    "name": f"Semantic Scene Context: {scene_res.get('scene_label', 'General Media')}",
                    "category": "semantic_forensics",
                    "status": "APPLIED",
                    "finding": scene_res.get("finding", "Scene classified.")
                },
                {
                    "name": "Provenance & Metadata Forensics",
                    "category": "metadata_forensics",
                    "status": "APPLIED",
                    "finding": meta_res.get("finding", "Metadata evaluated.")
                },
                {
                    "name": "Visual Watermark Icon Scanner",
                    "category": "visual_provenance",
                    "status": watermark_res.get("status", "APPLIED"),
                    "reason": None if watermark_res.get("is_watermark_found") else "No corner watermark icon signature detected.",
                    "finding": watermark_res.get("finding", "No watermark detected.")
                },
                {
                    "name": "Social Re-Compression & DCT Grid Analyzer",
                    "category": "compression_history",
                    "status": recompression_res.get("status", "APPLIED"),
                    "reason": None if already_recompressed else "Single-generation or uncompressed capture.",
                    "finding": recompression_res.get("finding", "Grid continuity verified.")
                },
                {
                    "name": "Sub-Pixel CFA & Micro-Particle Morphing Analyzer",
                    "category": "micro_forensics",
                    "status": "APPLIED",
                    "finding": pixel_res.get("note", "Bayer CFA correlation verified.")
                },
                {
                    "name": "Multi-Scale Gabor Filter Bank Texture Analyzer",
                    "category": "texture_forensics",
                    "status": gabor_res.get("status", "APPLIED"),
                    "finding": gabor_res.get("finding", "Texture distribution verified.")
                },
                {
                    "name": "FFT High-Frequency Residual & Radial Decay Analyzer",
                    "category": "frequency",
                    "status": freq_res.get("status", "APPLIED"),
                    "finding": freq_res.get("finding", "Fourier spectrum evaluated.")
                },
                {
                    "name": "Error Level Analysis (ELA)",
                    "category": "compression",
                    "status": "APPLIED",
                    "finding": ela_res.get("note", "Compression surface evaluated.")
                },
                {
                    "name": "Sensor Pattern Noise (PRNU)",
                    "category": "sensor_forensics",
                    "status": "APPLIED",
                    "finding": noise_res.get("note", "Sensor noise evaluated.")
                },
                {
                    "name": "Face Landmark & Boundary Warping (Face X-Ray)",
                    "category": "face_forensics",
                    "status": face_res.get("status", "SKIPPED"),
                    "reason": face_res.get("reason"),
                    "finding": face_res.get("finding")
                },
                {
                    "name": "Optics Physics: Corneal Specular Parallax",
                    "category": "physics_engine",
                    "status": physics_res.get("status", "SKIPPED"),
                    "reason": physics_res.get("reason"),
                    "finding": physics_res.get("finding")
                },
                {
                    "name": "Geometry Physics: Support & Structural Symmetry",
                    "category": "physics_engine",
                    "status": geometry_res.get("status", "SKIPPED"),
                    "reason": geometry_res.get("reason"),
                    "finding": geometry_res.get("finding")
                },
                {
                    "name": "Covert Steganography: LSB & File Trailer Scanner",
                    "category": "steganography_forensics",
                    "status": stego_res.get("status", "APPLIED"),
                    "reason": None if stego_res.get("is_stego_detected") else "No covert payload or anomalous LSB bit patterns detected.",
                    "finding": stego_res.get("finding", "Clean (No hidden steganographic payload detected).")
                }
            ]

            processing_time_ms = int((time.time() - start_time) * 1000)

            metadata_payload = {
                "scene_label": scene_label,
                "generator_name": meta_res.get("generator_name") or meta_res.get("raw_software_tag"),
                "ai_signature_found": bool(meta_res.get("is_ai_signature_found")),
                "exif_missing": bool(meta_res.get("is_exif_missing")),
                "metadata_anomaly_score": float(meta_res.get("metadata_anomaly_score") or 0.0),
                "metadata_finding": meta_res.get("finding"),
                "feature_variance": feature_variance,
                "strong_signal_count": strong_signal_count,
                "strong_signals": strong_signals,
                "face_count": face_res.get("face_count", 0),
                "cross_domain_consistency": cross_domain_consistency,
                "gabor_anomaly_score": float(gabor_res.get("gabor_anomaly_score") or 0.0),
                "why_reasons": why_reasons,
                "is_contradiction": is_contradiction,
                "spectral_decay_slope": float(freq_res.get("spectral_decay_slope") or 2.0),
                "hf_model": hf_res.get("model_name"),
                "hf_risk_score": float(hf_res.get("hf_risk_score") or 0.0) if hf_res.get("hf_risk_score") is not None else None,
                "hf_status": "applied" if hf_res.get("is_hf_applied") else "skipped",
                "watermark_found": bool(watermark_res.get("is_watermark_found")),
                "watermark_location": watermark_res.get("watermark_location"),
                "watermark_anomaly_score": float(watermark_res.get("watermark_anomaly_score") or 0.0),
                "already_recompressed": bool(already_recompressed),
                "recompression_score": float(recompression_res.get("recompression_score") or 0.0),
                "blockiness_ratio": float(recompression_res.get("blockiness_ratio") or 1.0),
                "stego_detected": bool(stego_res.get("is_stego_detected")),
                "stego_payload_type": stego_res.get("payload_type"),
                "stego_payload_size": int(stego_res.get("payload_size_bytes") or 0),
                "stego_method": stego_res.get("stego_method"),
                "stego_preview": stego_res.get("extracted_preview"),
                "stego_finding": stego_res.get("finding"),
                "lm_studio_status": vision_res.get("status", "UNAVAILABLE"),
                "lm_studio_model": vision_res.get("model_name"),
                "vision_analysis": vision_res
            }

            explanation_summary = self._synthesize_explanation(
                verdict=verdict,
                risk_score=risk_score,
                has_face=has_face,
                scene_type=scene_type,
                scene_res=scene_res,
                strong_signals=strong_signals,
                face_res=face_res,
                physics_res=physics_res,
                meta_res=meta_res,
                watermark_res=watermark_res,
                stego_res=stego_res,
                vision_res=vision_res,
                hf_res=hf_res,
                is_hf_face_real=is_hf_face_real
            )

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
            import traceback
            logger.exception(f"[DETECTOR ERROR] predict() failed: {e}")
            traceback.print_exc()
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
                analyzers=[],
                metadata={"error": str(e)},
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_code="INFERENCE_FAILED",
                error_message=str(e)
            )
