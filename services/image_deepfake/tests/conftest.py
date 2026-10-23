import time
import jwt
import pytest
from services.image_deepfake.app.config.settings import settings

@pytest.fixture
def authorized_headers():
    token = jwt.encode({'sub':'image-test-owner','token_type':'access','exp':int(time.time())+60},
                       settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {'Authorization':'Bearer '+token}
