import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from models.phishing_url.inference.regional_model import RegionalModel,region
from models.phishing_url.preprocessing.structural_features import NAMES,VERSION


class RegionalModelTests(unittest.TestCase):
    def test_routing_uses_url_shape_and_never_hostname_identity(self):
        for host in ('google.com','unseen.example','192.0.2.1'):
            self.assertEqual(region('https://'+host+'/'),'root')
            self.assertEqual(region('https://'+host+'/3/'),'path')
            self.assertEqual(region('https://'+host+'/3/?q=1'),'query')
        self.assertEqual(region('https://example.com/#fragment'),'root')

    def test_runtime_requires_complete_routing_before_artifacts_are_loaded(self):
        manifest={'structural_features':list(NAMES),'structural_preprocessing':VERSION,'routing':{'root':{'expert':'baseline','threshold':.7}}}
        with self.assertRaisesRegex(ValueError,'every URL shape'),patch('joblib.load') as load:
            RegionalModel(Path('.'),manifest)
        load.assert_not_called()

    def test_selected_expert_and_region_threshold_are_preserved(self):
        model=RegionalModel.__new__(RegionalModel)
        model.manifest={'routing':{'root':{'expert':'baseline','threshold':.7},'query':{'expert':'baseline','threshold':.6},'path':{'expert':'correction','threshold':.85}}}
        output=({'baseline':np.array([.2]),'correction':np.array([.8])},np.zeros((1,len(NAMES))),np.array([.3]),np.array([.4]))
        with patch.object(model,'expert_predictions',return_value=output):
            root=model.predict_url('https://unseen.example/',None)
            path=model.predict_url('https://unseen.example/3/',None)
            query=model.predict_url('https://unseen.example/?q=1',None)
        self.assertEqual(root[:2],(.2,.7))
        self.assertEqual(path[:2],(.8,.85))
        self.assertEqual(query[:2],(.2,.6))
        self.assertFalse(path[2]['calibrated'])
        self.assertEqual(path[2]['url_region'],'path')


if __name__=='__main__':unittest.main()
