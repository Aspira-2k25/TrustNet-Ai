from pathlib import Path
import unittest
from unittest.mock import patch
from models.phishing_url.inference.recall_model import RecallModel
from models.phishing_url.inference.regional_model import RegionalModel


class RecallModelTests(unittest.TestCase):
    def fixture(self):
        m=RecallModel.__new__(RecallModel)
        m.manifest={'rescue':{s:{'expert':'correction','threshold':.95} for s in ('root','query','path')}}
        return m

    def test_no_primary_alert_can_be_removed_or_replaced(self):
        m=self.fixture()
        for p in (0,.1,.69,.7,.9,1):
            for other in (0,.5,.949,.95,1):
                original=(p,.7,{'expert_estimates':{'baseline':p,'correction':other}})
                with patch.object(RegionalModel,'predict_url',return_value=original):
                    new,threshold,meta=m.predict_url('https://unseen.example/',None)
                if p>=.7:
                    self.assertEqual((new,threshold),(p,.7))
                    self.assertFalse(meta['rescue_applied'])
                else:
                    self.assertEqual(new>=threshold,other>=.95)

    def test_rescue_explanation_preserves_primary_estimate(self):
        m=self.fixture();original=(.2,.7,{'expert_estimates':{'baseline':.2,'correction':.98}})
        with patch.object(RegionalModel,'predict_url',return_value=original):
            p,threshold,meta=m.predict_url('https://unseen.example/a?q=1',None)
        self.assertEqual((p,threshold),(.98,.95))
        self.assertEqual(meta['primary_model_probability'],.2)
        self.assertEqual(meta['primary_model_threshold'],.7)
        self.assertEqual(meta['selected_expert'],'rescue_correction')

    def test_invalid_and_same_expert_rules_are_rejected(self):
        def initialize(instance,root,manifest):instance.manifest=manifest
        for expert,threshold in [('baseline',.95),('unknown',.95),('correction',float('nan')),('correction',.8),('correction',1)]:
            manifest={'routing':{s:{'expert':'baseline','threshold':.7} for s in ('root','query','path')},
                      'rescue':{s:{'expert':expert,'threshold':threshold} for s in ('root','query','path')}}
            with patch.object(RegionalModel,'__init__',initialize),self.assertRaises(ValueError):
                RecallModel(Path('.'),manifest)


if __name__=='__main__':unittest.main()
