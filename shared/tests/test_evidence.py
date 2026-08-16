from shared.schemas.evidence import EvidenceItem

def test_valid_evidence_item():
    item = EvidenceItem(
        feature_or_region="face_blend_boundary",
        contribution=0.85,
        human_readable_note="High artifact concentration along the jawline."
    )
    assert item.feature_or_region == "face_blend_boundary"
    assert item.contribution == 0.85
    assert item.human_readable_note == "High artifact concentration along the jawline."

def test_contribution_accepts_float():
    # Since there's no explicitly defined bound in the spec yet, 
    # we just verify it accepts arbitrary floats (e.g., beyond [0, 1] or [-1, 1])
    item_large = EvidenceItem(
        feature_or_region="test_region",
        contribution=100.5,
        human_readable_note="Test note"
    )
    assert item_large.contribution == 100.5

    item_negative = EvidenceItem(
        feature_or_region="test_region_2",
        contribution=-5.0,
        human_readable_note="Test note 2"
    )
    assert item_negative.contribution == -5.0
