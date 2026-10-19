import pytest
import jwt
from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from services.scan_management.app.routers.scan_router import get_current_user_id
from services.scan_management.app.config.settings import settings

def test_identity_header_alone_cannot_read_someone_elses_history(monkeypatch):
    monkeypatch.setenv('ALLOW_MOCK_AUTH','false')
    with pytest.raises(HTTPException) as error:
        get_current_user_id(authorization=None,x_user_id='someone-else')
    assert error.value.status_code==401

def test_signed_identity_wins_over_forged_proxy_identity():
    token=jwt.encode({'sub':'signed-owner','role':'user','token_type':'access',
        'exp':datetime.now(timezone.utc)+timedelta(minutes=5)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    assert get_current_user_id(authorization='Bearer '+token,x_user_id='someone-else')=='signed-owner'
