import io
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class FaceAnalyzer:
    """Cascade proposals with eye-pair filtering and a boundary-gradient proxy. No trained Face X-Ray model or facial landmark reconstruction is used."""

    def __init__(self, localization="haar"):
        from models.image_deepfake.inference.face_localizer import FaceLocalizer
        self.localizer = FaceLocalizer() if localization == "yunet" else None
        self.cascades = []
        self.eye_cascade = None
        if cv2 is not None and hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            cascade_names = [
                'haarcascade_frontalface_alt2.xml',
                'haarcascade_frontalface_default.xml',
                'haarcascade_frontalface_alt.xml',
                'haarcascade_frontalface_alt_tree.xml',
                'haarcascade_profileface.xml'
            ]
            for cname in cascade_names:
                try:
                    cpath = cv2.data.haarcascades + cname
                    cascade = cv2.CascadeClassifier(cpath)
                    if not cascade.empty():
                        self.cascades.append(cascade)
                except Exception:
                    pass
            try:
                eyes = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
                if not eyes.empty():
                    self.eye_cascade = eyes
            except Exception:
                pass

    def _rotate_image_and_get_matrix(self, img_gray: np.ndarray, angle: float):
        h, w = img_gray.shape[:2]
        center = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))
        M[0, 2] += (nW / 2.0) - center[0]
        M[1, 2] += (nH / 2.0) - center[1]
        rotated = cv2.warpAffine(img_gray, M, (nW, nH))
        M_inv = cv2.invertAffineTransform(M)
        return rotated, M_inv

    def detect_faces(self, gray_np: np.ndarray, color_arr: Optional[np.ndarray] = None) -> List[Tuple[int, int, int, int]]:
        """
        Multi-pass cascade detection with contrast equalization and tilt compensation.
        Skin-colored regions are never substituted for verified detector proposals.
        """
        if self.localizer is not None:
            if color_arr is None:
                raise ValueError("RGB input required for YuNet")
            return self.localizer.detect(color_arr)
        if cv2 is None or not self.cascades or self.eye_cascade is None:
            return []

        detected_boxes: List[Tuple[int, int, int, int]] = []
        h, w = gray_np.shape[:2]

        def add_box(bx: int, by: int, bw: int, bh: int):
            bx = max(0, min(w - 1, int(bx)))
            by = max(0, min(h - 1, int(by)))
            bw = max(16, min(w - bx, int(bw)))
            bh = max(16, min(h - by, int(bh)))

            # Require a plausible eye pair before treating a cascade proposal as a face.
            # Low-confidence/profile regions are left unassessed, never replaced by skin blobs.
            face = gray_np[by:by + bh, bx:bx + bw]
            eyes = self.eye_cascade.detectMultiScale(
                face, scaleFactor=1.1, minNeighbors=4, minSize=(12, 12)
            )
            centers = [(ex + ew / 2, ey + eh / 2) for ex, ey, ew, eh in eyes
                       if ey + eh / 2 < bh * 0.65]
            if not any(0.15 * bw < abs(ax - bx2) < 0.75 * bw
                       and abs(ay - by2) < bh * 0.2
                       for i, (ax, ay) in enumerate(centers)
                       for bx2, by2 in centers[i + 1:]):
                return

            # IoU-based non-maximum suppression
            for (ox, oy, ow, oh) in detected_boxes:
                ix1 = max(bx, ox)
                iy1 = max(by, oy)
                ix2 = min(bx + bw, ox + ow)
                iy2 = min(by + bh, oy + oh)
                iw = max(0, ix2 - ix1)
                ih = max(0, iy2 - iy1)
                intersection = iw * ih
                union = (bw * bh) + (ow * oh) - intersection
                iou = intersection / max(1.0, float(union))
                if iou > 0.35:
                    return
            detected_boxes.append((int(bx), int(by), int(bw), int(bh)))

        # 1. Multi-pass cascade search across image variants for all frontal & profile faces
        if self.cascades:
            equalized_gray = cv2.equalizeHist(gray_np)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            clahe_gray = clahe.apply(gray_np)
            variants = [gray_np, equalized_gray, clahe_gray]

            for cascade in self.cascades:
                for img_variant in variants:
                    faces = cascade.detectMultiScale(
                        img_variant,
                        scaleFactor=1.08,
                        minNeighbors=4,
                        minSize=(28, 28)
                    )
                    if len(faces) > 0:
                        for (x, y, bw, bh) in faces:
                            add_box(x, y, bw, bh)

            # 2. Multi-Angle Rotation Sweeps for Tilted/Angled Heads (+/-15 deg, +/-25 deg)
            if len(detected_boxes) == 0:
                for angle in [15.0, -15.0, 25.0, -25.0]:
                    rot_img, M_inv = self._rotate_image_and_get_matrix(clahe_gray, angle)
                    for cascade in self.cascades[:3]:
                        faces = cascade.detectMultiScale(rot_img, scaleFactor=1.08, minNeighbors=4, minSize=(28, 28))
                        for (rx, ry, rw, rh) in faces:
                            rcx, rcy = rx + rw / 2.0, ry + rh / 2.0
                            orig_c = np.dot(M_inv, np.array([rcx, rcy, 1.0]))
                            add_box(int(orig_c[0] - rw / 2.0), int(orig_c[1] - rh / 2.0), rw, rh)
                    if len(detected_boxes) > 0:
                        break

            if len(detected_boxes) > 0:
                return detected_boxes

        return detected_boxes

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            if cv2 is None or (self.localizer is not None and not self.localizer.ready) or (self.localizer is None and (not self.cascades or self.eye_cascade is None)):
                return {
                    "has_face": False, "face_count": 0, "bounding_boxes": [],
                    "status": "UNAVAILABLE", "localization_available": False,
                    "reason": "Face localization unavailable: OpenCV face/eye cascade API or model resources are missing.",
                    "boundary_anomaly_score": 0.0, "skin_edge_variance": 0.0,
                    "is_manipulated_face": False, "finding": None,
                }
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
            h, w, _ = arr.shape

            # Convert to grayscale for OpenCV face detection
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if cv2 is not None else np.mean(arr, axis=2).astype(np.uint8)

            detected_boxes = self.detect_faces(gray, color_arr=arr)
            face_count = len(detected_boxes)
            has_face = face_count > 0

            if not has_face:
                return {
                    "has_face": False,
                    "localization_available": True,
                    "face_count": 0,
                    "bounding_boxes": [],
                    "localization_method": "opencv_yunet" if self.localizer is not None else "opencv_haar",
                    "localization_identity": self.localizer.identity if self.localizer else {"strategy":"haar-eye-pair-crop-v1"},
                    "rejected_proposals": self.localizer.rejected if self.localizer else [],
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
                else f"No boundary anomaly crossed the configured threshold across {face_count} face(s)."
            )

            return {
                "has_face": True,
                "localization_available": True,
                "localization_method": "opencv_yunet" if self.localizer is not None else "opencv_haar",
                "localization_identity": self.localizer.identity if self.localizer else {"strategy":"haar-eye-pair-crop-v1"},
                "rejected_proposals": self.localizer.rejected if self.localizer else [],
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
                "status": "UNAVAILABLE",
                "localization_available": False,
                "reason": f"Face analysis unavailable: {str(e)}",
                "boundary_anomaly_score": 0.0,
                "skin_edge_variance": 0.0,
                "is_manipulated_face": False,
                "finding": None
            }
