import base64
import pytest
from shared.utils.image_assets import persist,asset_path,directory


def test_original_and_derived_assets_keep_separate_exact_bytes(tmp_path):
    original=b'original bytes including metadata'
    encoded={'mask':base64.b64encode(b'pixel model mask').decode()}
    folder,urls=persist(tmp_path,'scan-0123456789',original,encoded)
    assert asset_path(tmp_path,'scan-0123456789','original').read_bytes()==original
    assert asset_path(tmp_path,'scan-0123456789','mask').read_bytes()==b'pixel model mask'
    assert urls['mask']=='/api/v1/scans/scan-0123456789/image/mask'
    with pytest.raises(FileExistsError):persist(tmp_path,'scan-0123456789',b'overwrite',{})


@pytest.mark.parametrize('identifier',['../outside','scan-../../evil','C:\\outside','scan-zzzzzzzzzz'])
def test_storage_rejects_untrusted_identifiers(tmp_path,identifier):
    with pytest.raises(ValueError):directory(tmp_path,identifier)


def test_asset_failure_removes_only_new_scan_directory(tmp_path):
    unrelated=tmp_path/'existing.db';unrelated.write_bytes(b'keep')
    with pytest.raises(ValueError):persist(tmp_path,'scan-0123456789',b'original',{'evil':'===='})
    assert not directory(tmp_path,'scan-0123456789').exists()
    assert unrelated.read_bytes()==b'keep'
