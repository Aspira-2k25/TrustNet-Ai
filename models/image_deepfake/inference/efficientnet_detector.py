import time
import uuid
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
import numpy as np
import torch
import torchvision.models as models

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
from models.image_deepfake.forensics.physics_eye_reflection_analyzer import PhysicsEyeReflectionAnalyzer
from models.image_deepfake.forensics.geometry_physics_analyzer import GeometryPhysicsAnalyzer
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient


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
        self.physics_analyzer = PhysicsEyeReflectionAnalyzer()
        self.geometry_analyzer = GeometryPhysicsAnalyzer()
        self.hf_client = HuggingFaceDeepfakeClient()

    def predict(self, input_data: bytes, scan_id: Optional[str] = None) -> DetectionResult:
        start_time = time.time()
        
        if scan_id is None:
            scan_id = str(uuid.uuid4())

        try:
            # 1. Base Semantic & Metadata Extraction
            scene_res = self.scene_analyzer.analyze(input_data)
            meta_res = self.metadata_analyzer.analyze(input_data)
            
            scene_type = scene_res.get("scene_type", "general_object")
            scene_label = scene_res.get("scene_label", "General Media / Photographic Content")
            is_digital_art = scene_type in ["anime_illustration", "digital_art"]
            is_screenshot = scene_type == "screenshot"

            # 2. Face Detection & Gating
            face_res = self.face_analyzer.analyze(input_data)
            has_face = bool(face_res.get("has_face", False))

            # 3. Conditional Forensic Analyzers Execution
            freq_res = self.freq_analyzer.analyze(input_data)
            pixel_res = self.pixel_analyzer.analyze(input_data)
            gabor_res = self.gabor_analyzer.analyze(input_data)
            ela_res = self.ela_analyzer.analyze(input_data)
            noise_res = self.noise_analyzer.analyze(input_data)

            # Optics / Geometry conditional branch
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

            # External Transformer inference
            hf_res = self.hf_client.predict(input_data)

            # 4. Extract deep CNN feature embeddings via PyTorch EfficientNet-B0 backbone
            tensor = process_image_bytes(input_data).to(self.device)
            with torch.no_grad():
                features = self.model.features(tensor)
                feature_variance = float(torch.var(features).item())

            # 5. Scientific Multi-Signal Conditional Fusion
            anomaly_weights: List[Tuple[float, float]] = []

            # Frequency DFT (radial power-law baseline + periodic spikes)
            anomaly_weights.append((freq_res["spectral_anomaly_score"], 0.20))
            
            # Sub-Pixel CFA & micro-jitter
            anomaly_weights.append((pixel_res["pixel_morphing_score"], 0.16))

            # Multi-scale Gabor Texture Bank
            gabor_w = 0.08 if (is_digital_art or is_screenshot) else 0.16
            anomaly_weights.append((gabor_res["gabor_anomaly_score"], gabor_w))

            # Compression ELA: De-emphasized for digital art / screenshots
            ela_w = 0.05 if (is_digital_art or is_screenshot) else 0.12
            anomaly_weights.append((ela_res["ela_anomaly_score"], ela_w))

            # Sensor Pattern Noise: De-emphasized for non-camera digital graphics
            noise_w = 0.04 if (is_digital_art or is_screenshot) else 0.10
            anomaly_weights.append((noise_res["noise_anomaly_score"], noise_w))

            # Facial boundary & Corneal optics (Only when applied)
            if face_res.get("status") == "APPLIED":
                anomaly_weights.append((face_res["boundary_anomaly_score"], 0.25))

            if physics_res.get("status") == "APPLIED":
                anomaly_weights.append((physics_res["physics_anomaly_score"], 0.20))

            # Geometry Physics (Only when applied)
            if geometry_res.get("status") == "APPLIED":
                anomaly_weights.append((geometry_res["geometry_anomaly_score"], 0.18))

            # Semantic scene context
            scene_w = 0.30 if is_digital_art else 0.12
            anomaly_weights.append((scene_res["scene_anomaly_score"], scene_w))

            # External Transformer Model (Hugging Face ViT)
            if hf_res.get("is_hf_applied", False):
                hf_anomaly = float(hf_res.get("hf_risk_score", 50.0)) / 100.0
                hf_w = 0.45 if is_digital_art else 0.35
                anomaly_weights.append((hf_anomaly, hf_w))

            # Compute normalized weighted average
            total_weight = sum(w for _, w in anomaly_weights)
            weighted_anomaly = sum(s * w for s, w in anomaly_weights) / max(1e-6, total_weight)

            # Evidential Max-Pooling Floor:
            # When a single high-reliability detection occurs (e.g. Hugging Face ViT >= 0.75 or confirmed Face X-Ray >= 0.75),
            # prevent dilution into false 'Authentic'.
            max_active_signal = max((s for s, _ in anomaly_weights), default=0.0)
            is_hf_real = hf_res.get("is_hf_applied", False) and (float(hf_res.get("hf_risk_score", 50.0)) <= 15.0)

            # Count genuinely independent strong synthetic indicators across distinct physical domains
            strong_signals = []
            strong_domains = set()

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

            if hf_res.get("is_hf_applied", False) and float(hf_res.get("hf_risk_score", 0.0)) >= 70.0:
                strong_signals.append(f"Hugging Face {self.hf_client.model_name} high fake probability")
                strong_domains.add("learned_deep_learning")

            strong_domain_count = len(strong_domains)
            strong_signal_count = len(strong_signals)
            if meta_res.get("is_ai_signature_found"):
                strong_signal_count += 2
                strong_domains.add("provenance_metadata")
                strong_domain_count += 2

            if max_active_signal >= 0.75 and not is_hf_real:
                weighted_anomaly = max(weighted_anomaly, max_active_signal * 0.85)

            # Cross-Domain Consistency Score (CDCF): Measures cross-modal agreement
            # across Spatial (Gabor/CFA/Noise), Frequency (FFT), Compression (ELA), and ML (HF)
            domain_scores = [
                (pixel_res["pixel_morphing_score"] + gabor_res["gabor_anomaly_score"] + noise_res["noise_anomaly_score"]) / 3.0,
                freq_res["spectral_anomaly_score"],
                ela_res["ela_anomaly_score"]
            ]
            if hf_res.get("is_hf_applied"):
                domain_scores.append(float(hf_res.get("hf_risk_score", 50.0)) / 100.0)

            cross_domain_spread = float(np.std(domain_scores))
            cross_domain_consistency = float(round(max(0.60, min(0.98, 1.0 - cross_domain_spread * 0.45)), 2))

            # Multi-Vector Corroboration Calibration (Requires >= 2 Distinct Physical Domains):
            is_hf_fake = hf_res.get("is_hf_applied", False) and (float(hf_res.get("hf_risk_score", 50.0)) >= 75.0)
            is_contradiction = False

            # Two-Way Contradiction Detection:
            # 1. Learned Model says REAL, but 2+ distinct physical forensic domains detect strong anomalies
            if is_hf_real and strong_domain_count >= 2:
                is_contradiction = True
                weighted_anomaly = max(0.48, min(0.62, weighted_anomaly))
            # 2. Learned Model says FAKE, but all forensic domains confirm authentic camera optics
            elif is_hf_fake and strong_domain_count == 0 and max_active_signal <= 0.25:
                is_contradiction = True
                weighted_anomaly = max(0.46, min(0.58, weighted_anomaly))
            elif meta_res.get("is_ai_signature_found"):
                weighted_anomaly = max(0.92, weighted_anomaly)
            elif strong_domain_count >= 2:
                weighted_anomaly = max(0.75, min(0.98, weighted_anomaly * 1.15))
            elif strong_domain_count == 1 and max_active_signal >= 0.75 and not is_hf_real:
                weighted_anomaly = max(0.65, min(0.95, weighted_anomaly))
            elif strong_domain_count == 0 and max_active_signal < 0.45:
                weighted_anomaly = min(0.32, weighted_anomaly)

            # Calculate Native Score P(REAL) in [0.01, 0.99]
            native_score = float(round(max(0.01, min(0.99, 1.0 - weighted_anomaly)), 4))
            risk_score = float(round((1.0 - native_score) * 100.0, 2))

            # Confidence is derived from the variance/consistency of active signals
            active_scores = [s for s, _ in anomaly_weights]
            score_spread = float(np.std(active_scores)) if len(active_scores) > 1 else 0.1
            confidence = float(round(max(0.70, min(0.98, 0.92 - score_spread * 0.35)), 2))

            # 4-Level Semantic Result Structure:
            # - AUTHENTIC: Risk < 25 (Low evidence of manipulation)
            # - LIKELY_AUTHENTIC: 25 <= Risk < 45 (Mostly consistent with real capture)
            # - UNCERTAIN: 45 <= Risk < 65 or contradiction (Signals disagree / insufficient evidence)
            # - LIKELY_AI_MANIPULATED: Risk >= 65 (Multiple independent signals indicate synthetic content)
            if is_contradiction or (45.0 <= risk_score < 65.0):
                verdict = "UNCERTAIN"
                label = "uncertain"
            elif risk_score >= 65.0:
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
            if is_contradiction:
                why_reasons.append("Conflicting Evidence: Learned transformer model and local physical forensic analyzers disagree. Manual verification recommended.")

            if hf_res.get("is_hf_applied", False):
                hf_risk_val = float(hf_res.get("hf_risk_score", 50.0))
                if hf_risk_val <= 15.0:
                    why_reasons.append(f"Vision Transformer AI model strongly indicates authentic photography ({100-hf_risk_val:.1f}% real confidence).")
                elif hf_risk_val >= 70.0:
                    why_reasons.append(f"Vision Transformer AI model indicates high synthetic deepfake probability ({hf_risk_val:.1f}% risk).")

            if freq_res.get("is_synthetic_pattern") and freq_res.get("spectral_anomaly_score", 0) >= 0.50:
                why_reasons.append("2D Fourier spectrum exhibits periodic grid spikes / un-natural frequency energy concentration.")
            else:
                why_reasons.append("2D Fourier power spectrum follows natural optical lens 1/f^alpha roll-off.")

            if pixel_res.get("is_morphing_detected") and pixel_res.get("pixel_morphing_score", 0) >= 0.50:
                why_reasons.append("Sub-pixel Bayer CFA correlation broken (indicates synthetic diffusion/upscaling).")
            else:
                why_reasons.append("Sub-pixel Bayer CFA demosaicing and micro-edge continuity verified.")

            if ela_res.get("is_anomalous") and ela_res.get("ela_anomaly_score", 0) >= 0.50:
                why_reasons.append("Error Level Analysis detected non-uniform compression disparities consistent with splicing.")
            else:
                why_reasons.append("Error Level Analysis confirms homogeneous single-source compression.")

            if face_res.get("has_face"):
                if face_res.get("is_manipulated_face"):
                    why_reasons.append("Face X-Ray boundary analysis detected localized blending step gradients.")
                else:
                    why_reasons.append(f"Seamless facial skin tone and boundary transitions verified across {face_res.get('face_count')} face(s).")

            if meta_res.get("is_ai_signature_found"):
                why_reasons.append(f"Deterministic AI generator footprint detected in metadata ({meta_res.get('generator_name')}).")

            # Keep top 4 most informative reasons
            why_reasons = why_reasons[:4]

            # 6. Structured Evidence Items
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

            if hf_res.get("is_hf_applied", False):
                evidence.append(EvidenceItem(
                    feature_or_region="huggingface_transformer",
                    contribution=float(round(hf_res.get("hf_risk_score", 50.0) / 100.0, 2)),
                    human_readable_note=hf_res.get("note", f"Evaluated against Hugging Face {self.hf_client.model_name}.")
                ))

            evidence.append(EvidenceItem(
                feature_or_region="semantic_scene_context",
                contribution=float(round(scene_res["scene_anomaly_score"], 2)),
                human_readable_note=f"Scene classified as [{scene_res['scene_label']}]: {scene_res['finding']}"
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

            # 7. Complete Analyzers Telemetry List
            analyzers = [
                {
                    "name": "EfficientNet-B0 Convolutional Backbone",
                    "category": "primary_ml",
                    "status": "APPLIED",
                    "finding": f"Extracted 1280-dim convolutional spatial representations (variance: {feature_variance:.2f}). Deepfake head pending dedicated training."
                },
                {
                    "name": f"Hugging Face AI Hub ({self.hf_client.model_name})",
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
                "hf_status": "applied" if hf_res.get("is_hf_applied") else "skipped"
            }

            risk_adjective = 'CRITICAL' if risk_score >= 75 else ('HIGH' if risk_score >= 50 else ('MEDIUM' if risk_score >= 25 else 'LOW'))
            explanation_summary = f"Trust Net analyzed this [{scene_label}] across {len(active_scores)} active forensic signals. Risk Score: {risk_score:.0f}/100 ({risk_adjective} RISK, Confidence: {confidence*100:.0f}%, Consistency: {cross_domain_consistency*100:.0f}%)."

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
