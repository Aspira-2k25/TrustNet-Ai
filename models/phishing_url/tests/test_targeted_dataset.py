import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timezone
import joblib
from models.phishing_url.datasets.targeted import normalize,tags,campaign_signature,Groups,private_or_tokenized,development_rows

ROOT=Path(__file__).resolve().parents[3]


class TargetedDataTests(unittest.TestCase):
    def test_url_identity_preserves_paths_and_query_case(self):
        self.assertEqual(normalize('https://EXAMPLE.com:443/A%2Fb?Key=VaL')[0],'https://example.com/A%2Fb?Key=VaL')
        self.assertNotEqual(normalize('https://example.com/A')[1],normalize('https://example.com/a')[1])
        self.assertNotEqual(normalize('https://example.com/?a=1')[1],normalize('https://example.com/?a=2')[1])

    def test_no_truncated_identity_or_credential_leak(self):
        with self.assertRaises(ValueError):normalize('https://example.com/'+'a'*2050)
        with self.assertRaises(ValueError):normalize('https://user:password@example.com/')
        self.assertTrue(private_or_tokenized('https://example.com/login?access_token=secret'))

    def test_domains_respect_private_hosting_tenants(self):
        self.assertNotEqual(normalize('https://a.github.io/')[2],normalize('https://b.github.io/')[2])
        self.assertEqual(normalize('https://login.example.co.uk/')[2],'example.co.uk')

    def test_slice_tags_are_observations_not_labels(self):
        self.assertIn('authentication_account_payment',tags('https://example.com/account/login'))
        self.assertNotIn('authentication_account_payment',tags('https://example.com/authors/alice'))
        self.assertIn('long_path',tags('https://example.com/'+'documentation/'*4))

    def test_campaign_grouping_handles_clones_but_not_generic_login(self):
        a=campaign_signature('https://a.example/campaign/invoicepayment/verificationportal/customer12345')
        b=campaign_signature('https://b.example/campaign/invoicepayment/verificationportal/customer67890')
        self.assertTrue(a);self.assertEqual(a,b)
        self.assertEqual(campaign_signature('https://a.example/login'),'')

    def test_union_is_deterministic(self):
        a=Groups();a.union('b','c');a.union('a','c')
        b=Groups();b.union('a','c');b.union('b','c')
        self.assertEqual(a.find('b'),b.find('b'))

    def test_build_reserves_unseen_domains_and_keeps_provenance(self):
        spec=importlib.util.spec_from_file_location('targeted_builder',ROOT/'scripts/research/build-targeted-phishing-dataset.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'new';old=root/'old';out.mkdir();old.mkdir()
            (root/'models/phishing_url/research').mkdir(parents=True)
            (root/'models/phishing_url/research/masked_candidate.json').write_text(json.dumps({'challenge_domains_excluded_from_fit':[]}))
            records={'train':[('https://prior-train.example/',0,'prior-train.example','primary')],
                     'calibration':[('https://prior-cal.example/',0,'prior-cal.example','primary')],
                     'validation':[('https://prior-val.example/',1,'prior-val.example','phiusiil')],
                     'test':[('https://prior-test.example/',1,'prior-test.example','phiusiil')]}
            joblib.dump({'groups':records,'fresh':[],'audit':{'source_hashes':{}}},old/'prepared.joblib')
            (old/'dataset_manifest.json').write_text('{}')
            stamp=datetime.now(timezone.utc).isoformat();rows=[]
            for label in (0,1):
                for n in range(30):
                    origin=f'https://class{label}-domain{n}.example/'
                    for k in range(4):
                        url=origin+('account/login' if k==0 else f'reference/page{k}')
                        evidence={'http_status':200,'tls_validated':True,'final_url':url,'provider_score':9}
                        rows.append({'url':url,'label':label,'source':'curated_official_page' if label==0 else 'phishstats_report','source_url':origin,
                                     'collected_at':stamp,'verified_at':stamp,'label_basis':'test_fixture','label_quality':'test_fixture','evidence':evidence})
            # Conflicting historical label must quarantine both records.
            rows.append({'url':'https://prior-train.example/','label':1,'source':'phishstats_report','source_url':'https://provider.example/',
                         'collected_at':stamp,'verified_at':stamp,'label_basis':'fixture','evidence':{'provider_score':9}})
            for bad_source,bad_label,evidence in [('model_prediction',1,{'provider_score':99}),('curated_official_page',0,{'http_status':200,'tls_validated':False}),('phishstats_report',1,{'provider_score':float('nan')})]:
                rows.append({'url':f'https://invalid-{bad_source}-{bad_label}.example/','label':bad_label,'source':bad_source,'source_url':'https://provider.example/',
                             'collected_at':stamp,'verified_at':stamp,'label_basis':'invalid_fixture','evidence':evidence})
            path=out/'new_evidence.jsonl';path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (out/'collection_manifest.json').write_text(json.dumps({'new_evidence_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
            supplement=out/'supplemental_evidence.jsonl';supplement.write_text('')
            (out/'supplemental_manifest.json').write_text(json.dumps({'new_evidence_sha256':hashlib.sha256(b'').hexdigest()}))
            builder.ROOT=root;builder.OUT=out;builder.OLD=old;builder.PUBLIC=root/'report.json'
            with contextlib.redirect_stdout(io.StringIO()):builder.main()
            manifest=json.loads((out/'dataset_manifest.json').read_text())
            self.assertEqual(manifest['test_status'],'sealed_not_evaluated')
            self.assertEqual(manifest['previously_seen_test_domains'],0)
            self.assertFalse(any(manifest['domain_overlap'].values()))
            self.assertEqual(manifest['new_label_conflicts_quarantined'],1)
            self.assertGreaterEqual(manifest['quarantine_rows'],4)
            self.assertFalse(manifest['retraining_started'])
            self.assertEqual(manifest['split_counts']['sealed_test'],{'0':60,'1':60})
            with (out/'sealed_test/url_labels.csv').open() as f:self.assertEqual(next(csv.reader(f)),['url','label'])
            self.assertTrue((out/'sealed_test/provenance.jsonl').exists())
            (out/'verification.json').write_text(json.dumps({'file_hashes_verified':True,'dataset_manifest_sha256':hashlib.sha256((out/'dataset_manifest.json').read_bytes()).hexdigest()}))
            (out/'normalization_label_audit.json').write_text(json.dumps({'normalized_label_conflicts':0}))
            with self.assertRaises(ValueError):list(development_rows(out,'sealed_test'))
            with self.assertRaises(ValueError):list(development_rows(out,'historical_regression'))
            self.assertTrue(list(development_rows(out,'train')))
            with (out/'train.csv').open('a') as f:f.write('https://tampered.example/,0\n')
            with self.assertRaises(ValueError):list(development_rows(out,'train'))
            with self.assertRaises(SystemExit):builder.main()


if __name__=='__main__':unittest.main()
