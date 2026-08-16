"""
TrustNet AI — Canonical Kafka Topic Definitions
Per Master Spec Section 7.2 and Architecture Specifications.
"""

TOPIC_SCAN_CREATED = "scan.created"
TOPIC_TRUST_SCORE_GENERATED = "trust_score.generated"
TOPIC_EXPLANATION_GENERATED = "explanation.generated"
TOPIC_DEAD_LETTER = "trustnet.dead_letter"

# The .dlq suffix pattern
DLQ_SUFFIX = ".dlq"

def get_detection_requested_topic(module_name: str) -> str:
    """Returns Kafka topic name for dispatching detection work to a module."""
    return f"detection.requested.{module_name}"

def get_detector_completed_topic(module_name: str) -> str:
    """Returns Kafka topic name for publishing completed detector results."""
    return f"detector.{module_name}.completed"

def get_dlq_topic(topic_name: str) -> str:
    """Returns corresponding dead-letter topic name."""
    return f"{topic_name}{DLQ_SUFFIX}"

class Topics:
    SCAN_CREATED = TOPIC_SCAN_CREATED
    TRUST_SCORE_GENERATED = TOPIC_TRUST_SCORE_GENERATED
    EXPLANATION_GENERATED = TOPIC_EXPLANATION_GENERATED
    DEAD_LETTER = TOPIC_DEAD_LETTER
    
    # Active AI Module Kafka Topics
    DETECTION_REQUESTED_IMAGE = "detection.requested.image_deepfake"
    DETECTOR_IMAGE_COMPLETED = "detector.image_deepfake.completed"

    # Future Extension Topics
    DETECTION_REQUESTED_AUDIO = "detection.requested.audio_deepfake"
    DETECTOR_AUDIO_COMPLETED = "detector.audio_deepfake.completed"

    DETECTION_REQUESTED_VIDEO = "detection.requested.video_deepfake"
    DETECTOR_VIDEO_COMPLETED = "detector.video_deepfake.completed"

    DETECTION_REQUESTED_PHISHING = "detection.requested.phishing"
    DETECTOR_PHISHING_COMPLETED = "detector.phishing.completed"
    DETECTION_REQUESTED_URL = DETECTION_REQUESTED_PHISHING

    DETECTION_REQUESTED_SCAM = "detection.requested.scam_message"
    DETECTOR_SCAM_COMPLETED = "detector.scam_message.completed"
    DETECTION_REQUESTED_TEXT = DETECTION_REQUESTED_SCAM

    DETECTION_REQUESTED_REVIEW = "detection.requested.fake_review"
    DETECTOR_REVIEW_COMPLETED = "detector.fake_review.completed"

    DETECTION_REQUESTED_OSINT = "detection.requested.osint"
    DETECTOR_OSINT_COMPLETED = "detector.osint.completed"
