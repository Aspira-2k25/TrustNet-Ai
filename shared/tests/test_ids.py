import re
from shared.utils.ids import generate_request_id, generate_scan_id, generate_event_id

def test_generate_request_id_uniqueness_and_format():
    ids = {generate_request_id() for _ in range(1000)}
    assert len(ids) == 1000
    # verify format is standard UUID
    for i in ids:
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', i)

def test_generate_scan_id_uniqueness_and_format():
    ids = {generate_scan_id() for _ in range(1000)}
    assert len(ids) == 1000
    for i in ids:
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', i)

def test_generate_event_id_uniqueness_and_format():
    ids = {generate_event_id() for _ in range(1000)}
    assert len(ids) == 1000
    for i in ids:
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', i)
