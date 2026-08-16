from shared.constants.topics import (
    TOPIC_SCAN_CREATED,
    TOPIC_TRUST_SCORE_GENERATED,
    TOPIC_EXPLANATION_GENERATED,
    TOPIC_DEAD_LETTER,
    Topics,
    get_detection_requested_topic,
    get_detector_completed_topic,
    get_dlq_topic
)

def test_topic_constants():
    assert TOPIC_SCAN_CREATED == "scan.created"
    assert TOPIC_TRUST_SCORE_GENERATED == "trust_score.generated"
    assert TOPIC_EXPLANATION_GENERATED == "explanation.generated"
    assert TOPIC_DEAD_LETTER == "trustnet.dead_letter"

def test_topic_helpers():
    assert get_detection_requested_topic("image_deepfake") == "detection.requested.image_deepfake"
    assert get_detector_completed_topic("image_deepfake") == "detector.image_deepfake.completed"
    assert get_dlq_topic("scan.created") == "scan.created.dlq"

def test_topics_class_attributes():
    assert Topics.SCAN_CREATED == "scan.created"
    assert Topics.DETECTION_REQUESTED_IMAGE == "detection.requested.image_deepfake"
    assert Topics.DETECTOR_IMAGE_COMPLETED == "detector.image_deepfake.completed"
    assert Topics.TRUST_SCORE_GENERATED == "trust_score.generated"
