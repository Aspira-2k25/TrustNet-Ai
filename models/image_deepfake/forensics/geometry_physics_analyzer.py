import io
import math
import numpy as np
from PIL import Image
from typing import Dict, Any

try:
    import cv2
except ImportError:
    cv2 = None

class GeometryPhysicsAnalyzer:
    """
    3D Geometry Plausibility & Structural Physics Branch.
    Analyzes images for impossible structural intersections, edge density anomalies,
    and severe bilateral asymmetry which often plague 2D generative models.
    """
    
    def __init__(self):
        self.is_available = cv2 is not None
        if self.is_available:
            self.orb = cv2.ORB_create(nfeatures=500)

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyzes the image for geometric and structural physics anomalies.
        Returns:
            - is_geometry_violation (bool)
            - geometry_anomaly_score (float)
            - finding (str)
        """
        if not self.is_available:
            return {
                "status": "SKIPPED",
                "is_geometry_violation": False,
                "geometry_anomaly_score": 0.0,
                "finding": "OpenCV unavailable for Geometry Physics processing."
            }

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(img)
            
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            h, w = gray.shape
            
            # 1. Structural Symmetry & Feature Distribution
            keypoints, _ = self.orb.detectAndCompute(gray, None)
            
            symmetry_anomaly = 0.0
            if keypoints and len(keypoints) > 50:
                # Split image into left and right halves
                mid_x = w // 2
                left_kps = sum(1 for kp in keypoints if kp.pt[0] < mid_x)
                right_kps = sum(1 for kp in keypoints if kp.pt[0] >= mid_x)
                
                total = left_kps + right_kps
                ratio = min(left_kps, right_kps) / max(left_kps, right_kps) if max(left_kps, right_kps) > 0 else 1.0
                
                # If one side of the image has massively more structural features than the other (ratio < 0.15),
                # it's highly asymmetrical. We use a very low threshold to ensure real asymmetrical scenes (e.g. side-profiles) don't trigger.
                if ratio < 0.15:
                    symmetry_anomaly = (0.15 - ratio) * 1.5 # Maps to 0.0 - 0.22
                    
            # 2. Edge Intersection / "Anti-Gravity" Plausibility
            edges = cv2.Canny(gray, 100, 200)
            
            # Calculate edge density in the bottom 15% of the image
            bottom_slice = edges[int(h*0.85):h, :]
            edge_density = np.sum(bottom_slice > 0) / (bottom_slice.shape[0] * bottom_slice.shape[1])
            
            intersection_anomaly = 0.0
            # If the bottom 15% has almost zero edges (e.g. perfectly smooth sky/wall) but the top has dense geometry,
            # this *could* indicate floating objects without contact shadows, or just someone jumping (stunt).
            # We assign a very low penalty (0.15) so it doesn't cause a false positive for real stunt jumps.
            if edge_density < 0.005:
                top_edges = edges[0:int(h*0.4), :]
                top_density = np.sum(top_edges > 0) / (top_edges.shape[0] * top_edges.shape[1])
                if top_density > 0.08:
                    intersection_anomaly = 0.15 # Mild suspicion of floating geometry
            
            # Combine anomalies
            total_anomaly = min(0.6, symmetry_anomaly + intersection_anomaly)
            
            if total_anomaly > 0.25:
                return {
                    "status": "APPLIED",
                    "is_geometry_violation": True,
                    "geometry_anomaly_score": float(round(total_anomaly, 2)),
                    "finding": f"Mild geometric anomaly detected (Asymmetry/Support score: {total_anomaly:.2f}). Could indicate synthetic blending or unusual staging."
                }
            else:
                return {
                    "status": "APPLIED",
                    "is_geometry_violation": False,
                    "geometry_anomaly_score": float(round(total_anomaly, 2)),
                    "finding": "Structural symmetry and ground-plane edge density are consistent with plausible 3D physics."
                }
                
        except Exception as e:
            return {
                "status": "SKIPPED",
                "is_geometry_violation": False,
                "geometry_anomaly_score": 0.0,
                "finding": f"Geometry engine fallback: {str(e)}"
            }
