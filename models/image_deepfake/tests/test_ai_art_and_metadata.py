import io
import pytest
from PIL import Image, PngImagePlugin
from models.image_deepfake.forensics.metadata_analyzer import MetadataAnalyzer
from models.image_deepfake.forensics.scene_analyzer import SceneContextAnalyzer
from models.image_deepfake.inference.huggingface_client import HuggingFaceDeepfakeClient
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
from shared.constants.status import StatusEnum

def create_sample_png_bytes(info_dict=None) -> bytes:
    img = Image.new("RGB", (256, 256), color=(60, 120, 200))
    buffer = io.BytesIO()
    
    pnginfo = PngImagePlugin.PngInfo()
    if info_dict:
        for k, v in info_dict.items():
            pnginfo.add_text(k, str(v))
            
    img.save(buffer, format="PNG", pnginfo=pnginfo)
    return buffer.getvalue()

def test_metadata_analyzer_detects_chatgpt_filename():
    analyzer = MetadataAnalyzer()
    raw_bytes = create_sample_png_bytes()
    
    # 1. Test ChatGPT image filename
    res = analyzer.analyze(raw_bytes, filename="ChatGPT Image Mar 2, 2026, 11_11_56 PM.png")
    assert res["is_ai_signature_found"] is True
    assert res["metadata_anomaly_score"] == 1.0
    assert "Chatgpt" in res["generator_name"] or "Chatgpt" in res["ai_tool"]
    assert "Filename" in res["finding"]

def test_metadata_analyzer_detects_dalle_and_midjourney():
    analyzer = MetadataAnalyzer()
    raw_bytes = create_sample_png_bytes()
    
    # Test DALL-E
    res_dalle = analyzer.analyze(raw_bytes, filename="DALL-E 2026-03-02 cat in hoodie.png")
    assert res_dalle["is_ai_signature_found"] is True
    assert "Dall-E" in res_dalle["generator_name"] or "Dalle" in res_dalle["generator_name"]

    # Test Midjourney
    res_mj = analyzer.analyze(raw_bytes, filename="user_midjourney_v6_ultra_cat.png")
    assert res_mj["is_ai_signature_found"] is True
    assert "Midjourney" in res_mj["generator_name"]

def test_metadata_analyzer_detects_png_prompt_info():
    analyzer = MetadataAnalyzer()
    # Embedded prompt parameter in PNG info
    raw_bytes = create_sample_png_bytes(info_dict={"parameters": "a cat wearing a blue hoodie, masterpiece, 8k, detailed"})
    
    res = analyzer.analyze(raw_bytes, filename="unknown_art.png")
    assert res["is_ai_signature_found"] is True
    assert res["metadata_anomaly_score"] == 1.0

def test_scene_analyzer_identifies_digital_art_illustration():
    analyzer = SceneContextAnalyzer()
    
    # Create stylized illustration-like image with saturated blue hoodie and line contours
    img = Image.new("RGB", (256, 256), color=(40, 60, 100))
    pixels = img.load()
    for y in range(256):
        for x in range(256):
            if 60 < x < 196 and 60 < y < 196:
                # Saturated blue hoodie
                pixels[x, y] = (30, 130, 240)
            elif (x == 60 or x == 196 or y == 60 or y == 196):
                # Black contour line
                pixels[x, y] = (0, 0, 0)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    res = analyzer.analyze(buffer.getvalue())
    assert res["scene_type"] == "anime_illustration"
    assert "Anime / Digital Illustration" in res["scene_label"]

def test_huggingface_client_skips_face_only_model_on_non_face():
    client = HuggingFaceDeepfakeClient(api_key="hf_test_mock_token_123", model_name="dima806/deepfake_vs_real_image_detection")
    raw_bytes = create_sample_png_bytes()
    
    # Non-face media
    res = client.predict(raw_bytes, has_face=False)
    assert res["is_hf_applied"] is False
    assert "image does not contain a human face" in res["note"]

def test_efficientnet_detector_evaluates_chatgpt_image_as_ai():
    detector = EfficientNetDetector(enable_explainability=False)
    raw_bytes = create_sample_png_bytes()
    
    result = detector.predict(raw_bytes, scan_id="test-chatgpt-scan", filename="ChatGPT Image Mar 2, 2026, 11_11_56 PM.png")
    
    assert result.status == StatusEnum.SUCCESS
    assert result.verdict in ("LIKELY_AI_MANIPULATED", "AI_GENERATED")
    assert result.risk_score >= 90.0
    assert result.metadata.get("ai_signature_found") is True
    assert "Chatgpt" in str(result.metadata.get("generator_name")) or "Chatgpt" in str(result.explanation)

def test_real_restaurant_photo_evaluated_as_authentic():
    from PIL import ImageDraw
    detector = EfficientNetDetector(enable_explainability=False)
    
    # Create realistic photo-like image with a person, table, cake, and natural gradients
    img = Image.new("RGB", (512, 512), (90, 60, 110))
    draw = ImageDraw.Draw(img)
    
    # Wooden table (warm brown)
    draw.rectangle((0, 360, 512, 512), fill=(160, 110, 70))
    # Person shirt & body
    draw.rectangle((140, 240, 372, 380), fill=(80, 100, 95))
    # Person face with YCbCr human skin tone (approx R=165, G=125, B=100)
    draw.ellipse((200, 120, 312, 250), fill=(175, 130, 105))
    # Cake
    draw.rectangle((180, 320, 332, 420), fill=(45, 30, 25))
    
    # Add subtle natural camera sensor variation
    pixels = img.load()
    for y in range(512):
        for x in range(512):
            r, g, b = pixels[x, y]
            jitter = (x % 5) - 2
            pixels[x, y] = (max(0, min(255, r + jitter)), max(0, min(255, g + jitter)), max(0, min(255, b + jitter)))
            
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    
    result = detector.predict(buffer.getvalue(), scan_id="test-restaurant-scan", filename="WhatsApp Image 2026-08-16 at 5.25.34 PM.jpeg")
    
    assert result.status == StatusEnum.SUCCESS
    assert result.risk_score <= 25.0
    assert result.verdict in ("AUTHENTIC", "LIKELY_AUTHENTIC")
    assert result.label == "real"

