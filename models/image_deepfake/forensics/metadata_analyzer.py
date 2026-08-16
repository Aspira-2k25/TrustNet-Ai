import io
from typing import Dict, Any
from PIL import Image, ExifTags

class MetadataAnalyzer:
    """
    Provenance and Metadata Branch.
    Extracts EXIF and C2PA-like data to check for cryptographic or software footprints
    of known AI image generators.
    """
    
    AI_SOFTWARE_SIGNATURES = [
        "midjourney",
        "stable diffusion",
        "dall-e",
        "dall e",
        "adobe firefly",
        "comfyui",
        "automatic1111",
        "invokeai",
        "novelai",
        "bing image creator",
        "openai",
        "generative fill",
        "photoshop ai",
        "generative ai",
        "c2pa",
        "xmp",
        "diffusion",
        "clipdrop",
        "runway",
        "pika",
        "leonardo ai",
        "deepai",
        "tensor.art",
        "civitai",
        "fooocus",
        "krea",
        "magnific",
        "sdxl",
        "flux",
        "playground ai",
        "nightcafe"
    ]
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyzes the image bytes for EXIF anomalies and AI signatures.
        Returns:
            - is_ai_signature_found (bool)
            - is_exif_missing (bool)
            - metadata_anomaly_score (float)
            - finding (str)
            - raw_software_tag (str)
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            exif_data = image.getexif()
            
            if not exif_data:
                # Absence of EXIF is standard on web/messaging/webcam media (neutral baseline 0.05)
                return {
                    "is_ai_signature_found": False,
                    "is_exif_missing": True,
                    "metadata_anomaly_score": 0.05,
                    "finding": "Standard metadata surface (no external AI generation markers).",
                    "raw_software_tag": None
                }
                
            # Resolve EXIF tags
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                exif_dict[tag_name] = value

            software = str(exif_dict.get("Software", "")).lower()
            creator_tool = str(exif_dict.get("CreatorTool", "")).lower()
            model = str(exif_dict.get("Model", "")).lower()
            make = str(exif_dict.get("Make", "")).lower()
            
            combined_software_strings = f"{software} {creator_tool} {model} {make}"
            
            # Check for deterministic AI signatures
            found_signature = None
            for sig in self.AI_SOFTWARE_SIGNATURES:
                if sig in combined_software_strings:
                    found_signature = sig
                    break

            generator_name = software or creator_tool or model or make or "unknown"
            if found_signature:
                return {
                    "is_ai_signature_found": True,
                    "is_exif_missing": False,
                    "metadata_anomaly_score": 1.0,
                    "finding": f"Deterministic AI Signature Found: {found_signature.title()}",
                    "raw_software_tag": generator_name,
                    "generator_name": generator_name,
                    "ai_tool": found_signature.title()
                }
                
            # Check for authentic camera traces
            has_camera_hardware = bool(make or model or "FocalLength" in exif_dict or "ISOSpeedRatings" in exif_dict or "ApertureValue" in exif_dict)
            
            if has_camera_hardware:
                return {
                    "is_ai_signature_found": False,
                    "is_exif_missing": False,
                    "metadata_anomaly_score": 0.0,
                    "finding": "Authentic camera hardware metadata detected (Make/Model).",
                    "raw_software_tag": software,
                    "generator_name": None,
                    "ai_tool": None
                }
                
            return {
                "is_ai_signature_found": False,
                "is_exif_missing": False,
                "metadata_anomaly_score": 0.08,
                "finding": "Basic EXIF header verified (no AI generator footprints detected).",
                "raw_software_tag": software,
                "generator_name": None,
                "ai_tool": None
            }
            
        except Exception as e:
            return {
                "is_ai_signature_found": False,
                "is_exif_missing": True,
                "metadata_anomaly_score": 0.05,
                "finding": f"Metadata extraction fallback: {str(e)}",
                "raw_software_tag": None,
                "generator_name": None,
                "ai_tool": None
            }
