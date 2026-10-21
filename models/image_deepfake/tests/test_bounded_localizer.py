import time
import pytest
from models.image_deepfake.inference.bounded_localizer import BoundedLocalizer


def sleeping_worker(connection):
    connection.send(('ready',None))
    connection.recv()
    time.sleep(20)


def working_worker(connection):
    connection.send(('ready',None))
    while True:
        try:
            data,budget=connection.recv()
            connection.send(('ok',{'source':data,'budget':budget}))
        except EOFError:return


def test_native_operation_is_killed_and_no_partial_map_is_returned():
    model=BoundedLocalizer(startup_timeout=10,request_timeout=.15,worker=sleeping_worker)
    started=time.monotonic()
    with pytest.raises(ValueError,match='Analysis incomplete'):model.predict(b'bytes')
    assert time.monotonic()-started<3
    assert model.process is None


def test_resident_model_is_reused_across_requests():
    model=BoundedLocalizer(startup_timeout=10,worker=working_worker)
    try:
        pid=model.process.pid
        assert model.predict(b'one')['source']==b'one'
        assert model.predict(b'two')['source']==b'two'
        assert model.process.pid==pid
    finally:model.close()
