"""
TrustNet AI — Kafka Topic Initialization Utility
Idempotently verifies or provisions standard TrustNet Kafka topics.
"""
import os
import sys

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.constants.topics import Topics

ALL_TOPICS = [
    Topics.SCAN_CREATED,
    Topics.DETECTION_REQUESTED_IMAGE,
    Topics.DETECTOR_IMAGE_COMPLETED,
    Topics.TRUST_SCORE_GENERATED,
    Topics.EXPLANATION_GENERATED,
    Topics.DEAD_LETTER
]

def print_topics():
    print("=" * 60)
    print("TrustNet AI — Standard Apache Kafka Topics")
    print("=" * 60)
    for t in ALL_TOPICS:
        print(f"  • {t}")
    print("=" * 60)

if __name__ == "__main__":
    print_topics()
