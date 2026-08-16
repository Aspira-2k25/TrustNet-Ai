import io
import math
import numpy as np
from PIL import Image
from typing import Dict, Any

try:
    import cv2
except ImportError:
    cv2 = None

class PhysicsEyeReflectionAnalyzer:
    """
    Optics & Sensor Physics Branch.
    Analyzes corneal specular highlights (light reflections) in eyes.
    AI generators often fail to render consistent light source physics, 
    resulting in asymmetrical or multi-directional specular reflections.
    """
    
    def __init__(self):
        # We attempt to load OpenCV's default Haar cascades for eye detection if supported
        self.eye_cascade = None
        if cv2 is not None and hasattr(cv2, 'CascadeClassifier'):
            try:
                # Load haarcascade_eye.xml from cv2.data
                self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            except Exception:
                self.eye_cascade = None

    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyzes eye reflections for physical consistency.
        Returns:
            - is_physics_violation (bool)
            - physics_anomaly_score (float)
            - finding (str)
        """
        if cv2 is None or self.eye_cascade is None or self.eye_cascade.empty():
            return {
                "status": "SKIPPED",
                "is_physics_violation": False,
                "physics_anomaly_score": 0.0,
                "finding": "OpenCV or Haar Cascades unavailable for physics processing."
            }

        try:
            # Load image and convert to OpenCV format
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(img)
            
            # Convert RGB to BGR for OpenCV
            frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect eyes
            eyes = self.eye_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            if len(eyes) < 2:
                return {
                    "status": "SKIPPED",
                    "is_physics_violation": False,
                    "physics_anomaly_score": 0.0,
                    "finding": f"Requires exactly 2 clearly visible eyes (found {len(eyes)}). Skipped."
                }
                
            # Sort eyes left-to-right based on x coordinate
            eyes = sorted(eyes, key=lambda e: e[0])
            
            reflection_vectors = []
            
            for (ex, ey, ew, eh) in eyes[:2]:  # Take the first two (left and right eye)
                eye_roi = gray[ey:ey+eh, ex:ex+ew]
                
                # Apply Gaussian Blur to smooth noise, then adaptive thresholding to find the brightest spots (specular highlights)
                blurred = cv2.GaussianBlur(eye_roi, (5, 5), 0)
                _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
                
                # Find contours of the highlights
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if not contours:
                    continue
                    
                # Find the largest contour (primary light source reflection)
                c = max(contours, key=cv2.contourArea)
                M = cv2.moments(c)
                
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Calculate vector from the center of the eye to the reflection centroid
                    center_x, center_y = ew // 2, eh // 2
                    dx = cx - center_x
                    dy = cy - center_y
                    
                    # Normalize the vector
                    magnitude = math.sqrt(dx**2 + dy**2)
                    if magnitude > 0:
                        reflection_vectors.append((dx/magnitude, dy/magnitude))
                    else:
                        reflection_vectors.append((0.0, 0.0))

            # Physics evaluation: Are the reflection vectors parallel?
            if len(reflection_vectors) == 2:
                v1, v2 = reflection_vectors[0], reflection_vectors[1]
                
                # Compute dot product between the two vectors (1.0 means perfectly parallel, -1.0 means opposite directions)
                dot_product = v1[0]*v2[0] + v1[1]*v2[1]
                
                # We must be very conservative to avoid false positives in complex real-world lighting (e.g., stadiums, multi-flash setups).
                # Only flag as a severe violation if reflections are almost pointing in opposite directions (dot product < 0.2)
                if dot_product < 0.20:
                    return {
                        "status": "APPLIED",
                        "is_physics_violation": True,
                        "physics_anomaly_score": 0.65, # Reduced from 0.85 to prevent overriding real stunt photos
                        "finding": f"Highly asymmetrical corneal specular reflections detected (Vector similarity: {dot_product:.2f}). Severe multi-directional lighting anomaly."
                    }
                elif dot_product < 0.60:
                    return {
                        "status": "APPLIED",
                        "is_physics_violation": False,
                        "physics_anomaly_score": 0.25,
                        "finding": f"Mildly asymmetrical specular reflections (Similarity: {dot_product:.2f}). Could indicate complex lighting or artificial synthesis."
                    }
                else:
                    return {
                        "status": "APPLIED",
                        "is_physics_violation": False,
                        "physics_anomaly_score": 0.05,
                        "finding": f"Specular reflections are physically consistent with a shared geometric light source (Similarity: {dot_product:.2f})."
                    }
                    
            return {
                "status": "SKIPPED",
                "is_physics_violation": False,
                "physics_anomaly_score": 0.0,
                "finding": "Insufficient high-contrast reflections to determine 3D light vectors."
            }

        except Exception as e:
            return {
                "status": "SKIPPED",
                "is_physics_violation": False,
                "physics_anomaly_score": 0.0,
                "finding": f"Physics engine fallback: {str(e)}"
            }
