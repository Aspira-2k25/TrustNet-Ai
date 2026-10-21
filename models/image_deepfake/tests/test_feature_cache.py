import json
import pytest
from benchmark.feature_cache import append_record


def test_cache_append_retries_open_lock_without_duplicate(tmp_path):
    target=tmp_path/'features.jsonl'
    class Locked:
        attempts=0
        def open(self,*args,**kwargs):
            self.attempts+=1
            if self.attempts<3:raise PermissionError('temporary lock')
            return target.open(*args,**kwargs)
    locked=Locked()
    append_record(locked,{'identity':'saved'},delay=0)
    assert locked.attempts==3
    assert [json.loads(x) for x in target.read_text().splitlines()]==[{'identity':'saved'}]


def test_cache_persistent_permission_failure_is_not_hidden():
    class Locked:
        def open(self,*args,**kwargs):raise PermissionError('persistent lock')
    with pytest.raises(PermissionError):append_record(Locked(),{},attempts=2,delay=0)
