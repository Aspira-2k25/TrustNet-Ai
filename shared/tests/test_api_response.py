import pytest
from pydantic import ValidationError
from shared.schemas.api_response import APIResponse, ErrorDetail, ResponseMeta

def test_success_response():
    resp = APIResponse(
        data={"user_id": 123},
        meta=ResponseMeta(request_id="req-111")
    )
    assert resp.data == {"user_id": 123}
    assert resp.error is None
    assert resp.meta.request_id == "req-111"

def test_error_response():
    resp = APIResponse(
        error=ErrorDetail(code="AUTH_FAILED", message="Invalid token"),
        meta=ResponseMeta(request_id="req-222")
    )
    assert resp.data is None
    assert resp.error.code == "AUTH_FAILED"
    assert resp.meta.request_id == "req-222"

def test_meta_request_id_required():
    with pytest.raises(ValidationError):
        # Missing meta completely
        APIResponse(data={"user_id": 123})

    with pytest.raises(ValidationError):
        # Missing request_id inside meta
        APIResponse(data={"user_id": 123}, meta={})

def test_both_data_and_error_fails():
    with pytest.raises(ValidationError):
        APIResponse(
            data={"user_id": 123},
            error=ErrorDetail(code="ERR", message="Something"),
            meta=ResponseMeta(request_id="req-333")
        )
