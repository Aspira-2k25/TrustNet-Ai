from enum import Enum

class ModuleEnum(str, Enum):
    phishing = "phishing"
    scam_message = "scam_message"
    fake_review = "fake_review"
    image_deepfake = "image_deepfake"
    audio_deepfake = "audio_deepfake"
    video_deepfake = "video_deepfake"
    osint = "osint"
