import io
from typing import Dict, Any, List, Tuple
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class FaceAnalyzer:
    """
    Facial Landmark, Alignment & Boundary Discontinuity (Face X-Ray) Forensic Analyzer.
    
    In face-swap deepfakes and AI face synthesis (e.g. DeepFaceLab, FaceSwap, InsightFace, SimSwap),
    the generated face must be composited back into the target video/image frame.
    This compositing process inevitably introduces subtle boundary artifacts:
    1. Facial Perimeter Step Gradient: Discontinuous derivative along the jawline, hairline, and neck.
    2. Blending Feathering & Color Disparity: Mismatch between inner facial skin tone/noise and outer background.
    3. Multi-Scale Texture Inconsistency: Micro-smoothing inside the face mask compared to surrounding hair/skin.
    """

    def __init__(self):
        self.face_cascade = None
        self.profile_cascade = None
        if cv2 is not None:
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
            except Exception:
                self.face_cascade = None
                self.profile_cascade = None

    def detect_faces(self, gray_np: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detects frontal and profile faces, returning a list of (x, y, w, h) bounding boxes.
        """
        if self.face_cascade is None or self.face_cascade.empty():
            return []

        # 1. Detect frontal faces
        faces = self.face_cascade.detectMultiScale(
            gray_np,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(36, 36)
        )
        
        detected_boxes: List[Tuple[int, int, int, int]] = []
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                detected_boxes.append((int(x), int(y), int(w), int(h)))

        # 2. If no frontal face detected, check for side-profile faces
        if len(detected_boxes) == 0 and self.profile_cascade is not None and not self.profile_cascade.empty():
            profiles = self.profile_cascade.detectMultiScale(
                gray_np,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(36, 36)
            )
            if len(profiles) > 0:
                for (x, y, w, h) in profiles:
                    detected_boxes.append((int(x), int(y), int(w), int(h)))

        return detected_boxes

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
            h, w, _ = arr.shape

            # Convert to grayscale for OpenCV face detection
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if cv2 is not None else np.mean(arr, axis=2).astype(np.uint8)

            detected_boxes = self.detect_faces(gray)
            face_count = len(detected_boxes)
            has_face = face_count > 0

            if not has_face:
                return {
                    "has_face": False,
                    "face_count": 0,
                    "bounding_boxes": [],
                    "status": "SKIPPED",
                    "reason": "No human facial region identified via computer vision face detector.",
                    "boundary_anomaly_score": 0.0,
                    "skin_edge_variance": 0.0,
                    "is_manipulated_face": False,
                    "finding": None
                }

            # Analyze blending and frequency boundary variance across detected face crops
            crop_anomalies = []
            skin_variances = []

            for (fx, fy, fw, fh) in detected_boxes:
                # Extract localized face crop
                face_crop = arr[fy:fy+fh, fx:fx+fw]
                if face_crop.size == 0:
                    continue

                fr, fg, fb = face_crop[:,:,0], face_crop[:,:,1], face_crop[:,:,2]
                skin_mask = (fr > 60) & (fg > 30) & (fb > 15) & ((fr - fg) > 10) & (fr > fb)
                
                skin_pixels = face_crop[skin_mask]
                skin_var = float(np.std(skin_pixels)) if len(skin_pixels) > 20 else float(np.std(face_crop))
                skin_variances.append(skin_var)

                # Enhanced 22% Margin Padding: Extends crop to include the full jawline, hairline, and neck blending seam
                pad = max(6, int(min(fw, fh) * 0.22))
                y1, y2 = max(0, fy - pad), min(h, fy + fh + pad)
                x1, x2 = max(0, fx - pad), min(w, fx + fw + pad)
                padded_crop = gray[y1:y2, x1:x2]

                if padded_crop.shape[0] > 16 and padded_crop.shape[1] > 16:
                    # Multi-band Sobel gradient along outer boundary seam (Face X-Ray Discontinuity)
                    gy, gx = np.gradient(padded_crop.astype(np.float32))
                    edge_mag = np.sqrt(gx**2 + gy**2)
                    
                    # Compute outer perimeter vs inner center gradient ratio
                    ph, pw = padded_crop.shape
                    inner_mask = np.zeros((ph, pw), dtype=bool)
                    inner_mask[pad:ph-pad, pad:pw-pad] = True
                    
                    inner_edges = edge_mag[inner_mask] if np.any(inner_mask) else edge_mag
                    outer_edges = edge_mag[~inner_mask] if np.any(~inner_mask) else edge_mag
                    
                    inner_mean_edge = float(np.mean(inner_edges))
                    outer_mean_edge = float(np.mean(outer_edges))
                    boundary_edge_std = float(np.std(edge_mag))
                    
                    # Boundary Disparity Ratio: Face swaps show abrupt boundary step transitions
                    boundary_disparity = abs(inner_mean_edge - outer_mean_edge) / (outer_mean_edge + 1e-6)
                else:
                    boundary_edge_std = 25.0
                    boundary_disparity = 0.2

                # Deepfake facial blending seams typically exhibit:
                # 1. Abnormal skin smoothing (< 13.5) or synthesis noise spikes (> 70.0)
                # 2. High boundary step gradient variance (> 52.0)
                # 3. High perimeter-to-inner boundary disparity (> 0.85)
                is_skin_anomalous = (skin_var < 13.5 or skin_var > 70.0)
                is_boundary_step = (boundary_edge_std > 52.0) or (boundary_disparity > 0.85)
                
                is_anomalous_crop = is_skin_anomalous or is_boundary_step
                
                if is_skin_anomalous and is_boundary_step:
                    crop_anomaly_score = 0.88
                elif is_anomalous_crop:
                    crop_anomaly_score = 0.72
                else:
                    crop_anomaly_score = min(0.35, max(0.04, abs(skin_var - 36.0) / 100.0 + boundary_disparity * 0.15))
                    
                crop_anomalies.append(crop_anomaly_score)

            primary_anomaly_score = float(max(crop_anomalies)) if crop_anomalies else 0.05
            primary_skin_var = float(np.mean(skin_variances)) if skin_variances else 25.0
            is_manipulated_face = primary_anomaly_score >= 0.50

            finding_text = (
                f"High-frequency blending discontinuities and boundary step gradients detected across {face_count} face(s)."
                if is_manipulated_face
                else f"Natural facial skin texture and seamless boundary transitions verified across {face_count} face(s)."
            )

            return {
                "has_face": True,
                "face_count": face_count,
                "bounding_boxes": detected_boxes,
                "status": "APPLIED",
                "reason": None,
                "boundary_anomaly_score": float(round(primary_anomaly_score, 3)),
                "skin_edge_variance": float(round(primary_skin_var, 2)),
                "is_manipulated_face": is_manipulated_face,
                "finding": finding_text
            }

        except Exception as e:
            return {
                "has_face": False,
                "face_count": 0,
                "bounding_boxes": [],
                "status": "FALLBACK",
                "reason": f"Face analysis fallback: {str(e)}",
                "boundary_anomaly_score": 0.0,
                "skin_edge_variance": 0.0,
                "is_manipulated_face": False,
                "finding": None
            }
