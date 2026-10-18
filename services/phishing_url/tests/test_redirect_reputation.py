import unittest
from unittest.mock import patch
from models.phishing_url.inference.navigation import inspect_path
from models.phishing_url.inference.forensics import analyze
from services.phishing_url.app.services.metadata_collector import collect


class RedirectReputationTests(unittest.TestCase):
    def observation(self, hops, reputation, addresses=None):
        first,final=hops[0],hops[-1]
        def fetch(url, **kwargs):
            if 'rdap.org' in url:return {'status':200,'body':b'{"events":[]}'}
            return {'status':200,'certificate':{},'body':b'','content_type':'text/html',
                    'redirects':len(hops)-1,'final_url':final,
                    'navigation':[{'url':u} for u in hops]}
        resolver=addresses or (lambda *args:['8.8.8.8'])
        with patch('services.phishing_url.app.services.metadata_collector.fetch',side_effect=fetch),patch('services.phishing_url.app.services.metadata_collector.public_addresses',side_effect=resolver),patch('services.phishing_url.app.services.metadata_collector.lookup',side_effect=reputation) as lookup:
            return collect(first,True),lookup

    def test_fresh_intermediate_report_survives_clean_final_destination(self):
        hops=['https://start.example/','https://middle.example/login','https://final.example/']
        def reputation(url):
            return {'status':'OBSERVED','matched':url==hops[1],'fresh_match':url==hops[1],'provider':'fixture'}
        observation,lookup=self.observation(hops,reputation)
        rep=observation['signals']['reputation']
        self.assertEqual(rep['match_scope'],'redirect_hop')
        self.assertEqual(rep['matched_url'],hops[1])
        self.assertEqual(lookup.call_count,3)
        findings=analyze(hops[0],observation)['findings']
        finding=next(f for f in findings if f['code']=='REPUTATION_MATCH')
        self.assertIn('intermediate',finding['reason'])

    def test_intermediate_requests_are_bounded_and_stop_on_rate_limit(self):
        hops=['https://start.example/','https://one.example/','https://two.example/','https://three.example/','https://final.example/']
        obs,lookup=self.observation(hops,lambda url:{'status':'OBSERVED','matched':False})
        self.assertEqual(lookup.call_count,4)  # initial + final + at most two hops
        self.assertFalse(obs['signals']['reputation']['matched'])
        def limited(url):
            return {'status':'RATE_LIMITED' if url==hops[1] else 'OBSERVED','matched':False}
        _,lookup=self.observation(hops,limited)
        self.assertEqual(lookup.call_count,3)
        _,lookup=self.observation(hops,lambda url:{'status':'RATE_LIMITED' if url==hops[-1] else 'OBSERVED','matched':False})
        self.assertEqual(lookup.call_count,2)

    def test_embedded_destination_is_inspected_without_fetch_or_phishing_claim(self):
        url='https://start.example/?dn=other.example&target=%2F%2Fcdn.example%2Fx&arbitrary=https%3A%2F%2Fthird.example%2F'
        with patch('socket.getaddrinfo') as resolve:
            targets=inspect_path(url)['navigation_parameters']
            report=analyze(url)
        resolve.assert_not_called()
        self.assertEqual([t['hostname'] for t in targets],['other.example','cdn.example','third.example'])
        self.assertIsNone(targets[0]['scheme'])
        self.assertEqual(report['outcome'],'NO_STRONG_INDICATORS')

    def test_non_url_values_and_credentials_are_not_reported_as_destinations(self):
        url='https://start.example/?version=1.2.3&dn=hello%20world&next=https%3A%2F%2Fuser%3Apass%40other.example%2F'
        self.assertEqual(inspect_path(url)['navigation_parameters'],[])

    def test_guessed_query_target_is_never_looked_up(self):
        url='https://start.example/?dn=unobserved.example'
        _,lookup=self.observation([url],lambda url:{'status':'OBSERVED','matched':False})
        self.assertEqual(lookup.call_count,1)
        self.assertEqual(lookup.call_args.args,(url,))

    def test_private_intermediate_host_is_not_sent_to_provider(self):
        def addresses(host,port):
            if host=='127.0.0.1':raise ValueError('Non-public destination')
            return ['8.8.8.8']
        hops=['https://start.example/','http://127.0.0.1/','https://final.example/']
        _,lookup=self.observation(hops,lambda url:{'status':'OBSERVED','matched':False},addresses)
        self.assertEqual(lookup.call_count,2)
        self.assertNotIn('127.0.0.1',str(lookup.call_args_list))

    def test_optional_enrichment_skips_when_collection_has_used_time_budget(self):
        hops=['https://start.example/','https://middle.example/','https://final.example/']
        with patch('services.phishing_url.app.services.metadata_collector.monotonic',side_effect=[0,20]):
            _,lookup=self.observation(hops,lambda url:{'status':'OBSERVED','matched':False})
        self.assertEqual(lookup.call_count,2)


if __name__=='__main__':unittest.main()
