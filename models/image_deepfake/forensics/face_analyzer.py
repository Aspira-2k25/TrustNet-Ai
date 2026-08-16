import io
from typing import Dict, Any, List, Tuple, Optional
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
        self.cascades = []
        if cv2 is not None:
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
        Robust multi-pass face detection using contrast-equalized cascades,
        multi-angle tilt compensation (+/-15, +/-25 deg), and distance-transform skin topography fallback.
        """
        if cv2 is None:
            return []

        detected_boxes: List[Tuple[int, int, int, int]] = []
        h, w = gray_np.shape[:2]

        def add_box(bx: int, by: int, bw: int, bh: int):
            bx = max(0, min(w - 1, int(bx)))
            by = max(0, min(h - 1, int(by)))
            bw = max(16, min(w - bx, int(bw)))
            bh = max(16, min(h - by, int(bh)))
            for (ox, oy, ow, oh) in detected_boxes:
                if abs(bx - ox) < min(bw, ow) * 0.5 and abs(by - oy) < min(bh, oh) * 0.5:
                    return
            detected_boxes.append((int(bx), int(by), int(bw), int(bh)))

        # 1. Multi-pass cascade search on upright image (0 degrees) if cascades available
        if self.cascades:
            equalized_gray = cv2.equalizeHist(gray_np)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            clahe_gray = clahe.apply(gray_np)
            variants = [gray_np, equalized_gray, clahe_gray]

            for cascade in self.cascades:
                for img_variant in variants:
                    faces = cascade.detectMultiScale(
                        img_variant,
                        scaleFactor=1.06,
                        minNeighbors=3,
                        minSize=(24, 24)
                    )
                    if len(faces) > 0:
                        for (x, y, bw, bh) in faces:
                            add_box(x, y, bw, bh)
                if len(detected_boxes) > 0:
                    break

            # 2. Multi-Angle Rotation Sweeps for Tilted Heads (+/-15 deg, +/-25 deg)
            if len(detected_boxes) == 0:
                for angle in [15.0, -15.0, 25.0, -25.0]:
                    rot_img, M_inv = self._rotate_image_and_get_matrix(clahe_gray, angle)
                    for cascade in self.cascades[:3]:
                        faces = cascade.detectMultiScale(rot_img, scaleFactor=1.08, minNeighbors=3, minSize=(28, 28))
                        for (rx, ry, rw, rh) in faces:
                            rcx, rcy = rx + rw / 2.0, ry + rh / 2.0
                            orig_pt = M_inv @ np.array([rcx, rcy, 1.0])
                            orig_x = int(orig_pt[0] - rw / 2.0)
                            orig_y = int(orig_pt[1] - rh / 2.0)
                            add_box(orig_x, orig_y, rw, rh)
                    if len(detected_boxes) > 0:
                        break

        # 3. Distance-Transform Skin Topography & Multi-Peak Face Proposal (Universal Fallback)
        if len(detected_boxes) == 0 and color_arr is not None:
            r = color_arr[:, :, 0].astype(np.float32)
            g = color_arr[:, :, 1].astype(np.float32)
            b = color_arr[:, :, 2].astype(np.float32)
            cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
            cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b
            # Real human skin has moderate R-G difference (10-75) and R/(G+1) <= 2.2; reject saturated red clothing
            skin_mask = ((cr >= 130) & (cr <= 175) & (cb >= 75) & (cb <= 128) & (r > 45) & (r > g) & ((r - g) <= 75) & (r / (g + 1.0) <= 2.2)).astype(np.uint8) * 255
            
            # Reject full-screen flat surfaces (e.g. wood textures or solid walls)
            skin_coverage = float(np.mean(skin_mask > 0))
            if skin_coverage > 0.85:
                return []

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            skin_clean = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
            skin_clean = cv2.morphologyEx(skin_clean, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            
            dist = cv2.distanceTransform(skin_clean, cv2.DIST_L2, 5)
            d_copy = dist.copy()
            
            for _ in range(4):
                min_v, max_v, min_l, max_l = cv2.minMaxLoc(d_copy)
                if max_v < min(h, w) * 0.08:
                    break
                px, py = max_l
                radius = int(max_v * 1.6)
                bx = max(0, int(px) - radius)
                by = max(0, int(py) - radius)
                bw = min(w - bx, radius * 2)
                bh = min(h - by, radius * 2)
                if bw >= 24 and bh >= 24 and (bw * bh < h * w * 0.85):
                    add_box(bx, by, bw, bh)
                cv2.circle(d_copy, (int(px), int(py)), int(max_v * 1.4), 0.0, -1)

            # Connected component contour bounding boxes fallback
            if len(detected_boxes) == 0:
                contours, _ = cv2.findContours(skin_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                img_area = h * w
                for c in contours:
                    area = cv2.contourArea(c)
                    if img_area * 0.015 < area < img_area * 0.85:
                        cx, cy, cw, ch = cv2.boundingRect(c)
                        aspect = float(ch) / max(1, cw)
                        if 0.5 <= aspect <= 2.2:
                            add_box(cx, cy, cw, ch)

        return detected_boxes

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
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
