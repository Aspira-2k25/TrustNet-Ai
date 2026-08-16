import io
import re
from typing import Dict, Any, Optional
from PIL import Image, ExifTags

class MetadataAnalyzer:
    """
    Provenance and Metadata Branch.
    Extracts EXIF, PNG chunks, image.info (prompts/parameters), XMP/C2PA data,
    and file provenance to check for cryptographic or software footprints
    of known AI image generators.
    """
    
    AI_SOFTWARE_SIGNATURES = [
        "chatgpt",
        "dall-e",
        "dall e",
        "dalle",
        "midjourney",
        "stable diffusion",
        "stablediffusion",
        "adobe firefly",
        "firefly",
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
        "diffusion",
        "clipdrop",
        "runway",
        "pika",
        "leonardo ai",
        "leonardo.ai",
        "deepai",
        "tensor.art",
        "civitai",
        "fooocus",
        "krea",
        "magnific",
        "sdxl",
        "flux.1",
        "flux",
        "playground ai",
        "nightcafe",
        "ideogram"
    ]
    
    def analyze(self, image_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes the image bytes and filename for EXIF anomalies, PNG chunks,
        generation parameters, and AI provenance signatures.
        Returns:
            - is_ai_signature_found (bool)
            - is_exif_missing (bool)
            - metadata_anomaly_score (float)
            - finding (str)
            - raw_software_tag (str)
            - generator_name (str)
            - ai_tool (str)
        """
        try:
            detected_signatures = []
            extracted_sources = []
            
            # 1. Filename Provenance Check
            if filename:
                norm_fn = filename.lower()
                for sig in self.AI_SOFTWARE_SIGNATURES:
                    # Match signature as word or with hyphens/underscores/spaces
                    pattern = r'(?:^|[_\s\-\.\(\)\[\]])' + re.escape(sig) + r'(?:[_\s\-\.\(\)\[\]]|$)'
                    if sig in norm_fn or re.search(pattern, norm_fn):
                        detected_signatures.append((sig, f"Filename ({filename})"))
                        break

            # 2. Pillow Image Metadata Inspection (EXIF + PNG info + XMP)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Inspect image.info dictionary (crucial for PNGs, WebP, etc.)
            info_dict = image.info or {}
            combined_info_strings = []
            
            for k, v in info_dict.items():
                if isinstance(v, (str, bytes)):
                    val_str = v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else str(v)
                    combined_info_strings.append(f"{k}: {val_str.lower()}")
                    # Detect AI generation prompts/parameters in PNG metadata
                    k_lower = k.lower()
                    if k_lower in ("parameters", "prompt", "workflow", "generation_data", "sd-metadata"):
                        detected_signatures.append(("latent_diffusion_prompt", f"PNG info '{k}'"))

            info_text = " ".join(combined_info_strings).lower()
            for sig in self.AI_SOFTWARE_SIGNATURES:
                if sig in info_text:
                    detected_signatures.append((sig, "Image Info / XMP Metadata"))
                    break

            # 3. EXIF Inspection (JPEG / TIFF / PNG standard EXIF)
            exif_dict = {}
            exif_data = image.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_dict[tag_name] = str(value)

            software = str(exif_dict.get("Software", "")).lower()
            creator_tool = str(exif_dict.get("CreatorTool", "")).lower()
            model = str(exif_dict.get("Model", "")).lower()
            make = str(exif_dict.get("Make", "")).lower()
            user_comment = str(exif_dict.get("UserComment", "")).lower()
            img_desc = str(exif_dict.get("ImageDescription", "")).lower()
            
            combined_exif_strings = f"{software} {creator_tool} {model} {make} {user_comment} {img_desc}"
            for sig in self.AI_SOFTWARE_SIGNATURES:
                if sig in combined_exif_strings:
                    detected_signatures.append((sig, "EXIF Software / Device Tag"))
                    break

            # 4. Raw Byte Signature Scan (First/Last 32KB for XMP / C2PA / generator chunks)
            header_sample = image_bytes[:32768].lower()
            footer_sample = image_bytes[-32768:].lower() if len(image_bytes) > 32768 else b""
            raw_sample = (header_sample + b" " + footer_sample).decode("utf-8", errors="ignore")
            
            for sig in ["dall-e", "chatgpt", "midjourney", "comfyui", "c2pa", "automatic1111", "adobe firefly", "stablediffusion"]:
                if sig in raw_sample and not any(sig == s for s, _ in detected_signatures):
                    detected_signatures.append((sig, "Embedded Binary Chunk"))
                    break

            # Process AI Detection Findings
            if detected_signatures:
                top_sig, source = detected_signatures[0]
                generator_display = top_sig.replace("_", " ").title()
                finding_msg = f"Deterministic AI Provenance Signature Found: {generator_display} (Source: {source})"
                
                return {
                    "is_ai_signature_found": True,
                    "is_exif_missing": not bool(exif_data),
                    "metadata_anomaly_score": 1.0,
                    "finding": finding_msg,
                    "raw_software_tag": software or creator_tool or top_sig,
                    "generator_name": generator_display,
                    "ai_tool": generator_display,
                    "detected_signatures": [f"{s} ({src})" for s, src in detected_signatures]
                }

            # Check for authentic physical camera hardware traces
            has_camera_hardware = bool(make or model or "FocalLength" in exif_dict or "ISOSpeedRatings" in exif_dict or "ApertureValue" in exif_dict)
            
            if has_camera_hardware:
                return {
                    "is_ai_signature_found": False,
                    "is_exif_missing": False,
                    "metadata_anomaly_score": 0.0,
                    "finding": f"Authentic camera hardware metadata detected ({make} {model}).".strip(),
                    "raw_software_tag": software or f"{make} {model}",
                    "generator_name": None,
                    "ai_tool": None
                }

            if not exif_data:
                return {
                    "is_ai_signature_found": False,
                    "is_exif_missing": True,
                    "metadata_anomaly_score": 0.05,
                    "finding": "Standard sanitized metadata surface (no external AI generation markers).",
                    "raw_software_tag": None,
                    "generator_name": None,
                    "ai_tool": None
                }

            return {
                "is_ai_signature_found": False,
                "is_exif_missing": False,
                "metadata_anomaly_score": 0.08,
                "finding": "Basic metadata headers verified (no AI generator footprints detected).",
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

