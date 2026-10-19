"""Exercise real local bundle -> detection event -> report contract, offline."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from threadpoolctl import threadpool_limits
from models.phishing_url.inference.phishing_detector import PhishingDetector
from services.phishing_url.app.detection_service import DetectionService
threadpool_limits(limits=2)


def main(bundle='regional_v1'):
    detector=PhishingDetector(ROOT/('models/phishing_url/checkpoints/'+bundle+'/manifest.json'))
    version=detector.manifest['model_version']
    service=DetectionService(detector);rows=[]
    def scan(url,scan_id):
        return service.handle({'scan_id':scan_id,'module':'phishing','timestamp':'2026-10-18T00:00:00Z','payload':{'url':url}}).payload
    with patch.dict(os.environ,{'PHISHING_COLLECTOR_URL':''}):
        for i,url in enumerate(['https://google.com/','https://www.google.com/','https://paypal.com/','https://github.com/','https://docs.python.org/3/']):
            result=scan(url,'regional-'+str(i))
            assert result.model_version==version
            assert result.status.value=='PARTIAL_SUCCESS'
            assert result.verdict!='SUSPICIOUS',url
            assert result.metadata['score_basis']=='regional_url_model'
            assert not result.metadata['model_calibrated']
            assert not result.metadata['confidence_available']
            assert 0<=result.risk_score<=100
            rows.append({'url':url,'verdict':result.verdict,'risk_score':result.risk_score,
                         'trust_index':round(100-result.risk_score,1),'region':result.metadata['url_region'],
                         'selected_expert':result.metadata['selected_expert'],'threshold':result.metadata['threshold']})
        lookalike=scan('https://paypaI.com/','regional-lookalike')
        assert lookalike.verdict=='SUSPICIOUS'
        assert any(e.feature_or_region=='forensic:VISUAL_DOMAIN_IMPERSONATION' for e in lookalike.evidence)
    observed={'signals':{'http':{'status':'observed','status_code':200,'final_url':'https://example.com/'},
        'reputation':{'status':'OBSERVED','matched':True,'fresh_match':True,'provider':'fixture','match_scope':'redirect_hop'}}}
    with patch.dict(os.environ,{'PHISHING_COLLECTOR_URL':'http://fixture:8008'}),patch('httpx.post') as post:
        post.return_value=Mock();post.return_value.json.return_value=observed
        result=scan('https://example.com/','regional-reputation')
        assert result.verdict=='SUSPICIOUS'
        assert any('intermediate' in e.human_readable_note for e in result.evidence)
        assert result.metadata['score_basis']=='model_and_live_evidence'
    rescue_checks=[]
    if version=='regional-recall-v1':
        import joblib
        import hashlib
        data=joblib.load(ROOT/'models/phishing_url/data/recall_development_20261018/validation.joblib')
        with patch.dict(os.environ,{'PHISHING_COLLECTOR_URL':''}):
            for shape,rule in detector.manifest['rescue'].items():
                if rule is None:continue
                found=False
                for i,url in enumerate(data['urls']):
                    if data['regions'][i]!=shape or data['y'][i]!=1 or data['primary'][i]>=data['thresholds'][i] or data['experts'][rule['expert']][i]<rule['threshold']:continue
                    r=scan(url,'recall-smoke-'+shape)
                    assert r.metadata['rescue_applied'] and r.verdict=='SUSPICIOUS'
                    assert r.metadata['primary_model_probability']<r.metadata['primary_model_threshold']
                    rescue_checks.append({'region':shape,'url_sha256':hashlib.sha256(url.encode()).hexdigest(),'rescue_applied':True})
                    found=True;break
                assert found,'No development rescue fixture for '+shape
    report={'model_version':version,'offline_actual_inference':rows,'lookalike_risk_detected':True,
            'actual_rescue_checks':rescue_checks,
            'mocked_fresh_intermediate_report_detected':True,'no_live_network_requests':True,
            'not_a_live_gateway_kafka_or_browser_test':True}
    destination=ROOT/('models/phishing_url/research/recall_runtime_20261018.json' if version=='regional-recall-v1' else 'models/phishing_url/research/regional_runtime_20261018.json')
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',choices=['regional_v1','regional_recall_v1'],default='regional_v1')
    main(parser.parse_args().bundle)
