import io

import pytest
from PIL import Image, ImageDraw

from models.image_deepfake.forensics.physics_eye_reflection_analyzer import (
    PhysicsEyeReflectionAnalyzer,
    cv2,
)


class Cascade:
    def __init__(self, detections):
        self.detections = detections

    def empty(self):
        return False

    def detectMultiScale(self, *args, **kwargs):
        return self.detections


def test_eyes_from_different_people_are_not_paired():
    eyes = [(20, 20, 30, 30), (140, 20, 30, 30)]
    faces = [(0, 0, 100, 120), (120, 0, 100, 120)]
    assert PhysicsEyeReflectionAnalyzer._select_eye_pair(eyes, faces) is None


def test_pair_is_selected_within_one_face_in_group_photo():
    eyes = [(20, 20, 30, 30), (140, 20, 30, 30), (185, 22, 30, 30)]
    faces = [(0, 0, 100, 120), (120, 0, 100, 120)]
    assert PhysicsEyeReflectionAnalyzer._select_eye_pair(eyes, faces) == (eyes[1], eyes[2])


@pytest.mark.parametrize("eyes", [
    [(20, 20, 30, 30), (30, 20, 30, 30)],  # Duplicate overlapping detections.
    [(10, 10, 20, 20), (60, 50, 20, 20)],  # Vertically misaligned.
    [(10, 90, 20, 20), (60, 90, 20, 20)],  # Detections outside eye area.
])
def test_invalid_pairs_are_rejected(eyes):
    assert PhysicsEyeReflectionAnalyzer._select_eye_pair(eyes, [(0, 0, 100, 120)]) is None


@pytest.mark.skipif(cv2 is None, reason="OpenCV not installed")
def test_cross_person_eyes_do_not_produce_physics_violation():
    analyzer = PhysicsEyeReflectionAnalyzer()
    analyzer.eye_cascade = Cascade([(20, 20, 30, 30), (140, 20, 30, 30)])
    analyzer.face_cascade = Cascade([(0, 0, 100, 120), (120, 0, 100, 120)])
    buf = io.BytesIO()
    Image.new("RGB", (240, 140), "white").save(buf, format="PNG")
    result = analyzer.analyze(buf.getvalue())
    assert result["status"] == "SKIPPED"
    assert result["is_physics_violation"] is False
    assert result["physics_anomaly_score"] == 0.0
    assert "same detected face" in result["finding"]


@pytest.mark.skipif(cv2 is None, reason="OpenCV not installed")
@pytest.mark.parametrize("right_highlight_x,violation,score", [(112, False, 0.05), (98, True, 0.65)])
def test_same_face_reflection_scoring_is_preserved(right_highlight_x, violation, score):
    analyzer = PhysicsEyeReflectionAnalyzer()
    analyzer.eye_cascade = Cascade([(30, 25, 30, 30), (90, 25, 30, 30)])
    analyzer.face_cascade = Cascade([(0, 0, 160, 120)])
    image = Image.new("RGB", (160, 120), (40, 40, 40))
    draw = ImageDraw.Draw(image)
    for x in (52, right_highlight_x):
        draw.ellipse((x - 5, 35, x + 5, 45), fill="white")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    result = analyzer.analyze(buf.getvalue())
    assert result["status"] == "APPLIED"
    assert result["is_physics_violation"] is violation
    assert result["physics_anomaly_score"] == score
