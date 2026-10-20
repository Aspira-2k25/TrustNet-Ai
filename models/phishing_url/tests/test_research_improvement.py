"""Guard statistical operating-point selection; no network or model fitting."""
import unittest
import numpy as np

from models.phishing_url.training import selection as research


class ResearchSelectionTests(unittest.TestCase):
    def test_tied_scores_never_split_a_tie_to_claim_lower_fpr(self):
        y=np.array([1,0,1,0]);p=np.array([.9,.9,.7,.1])
        threshold=research.select_threshold(y,p,max_fpr=0)
        self.assertFalse(np.any(p>=threshold))

    def test_maximum_recall_respects_fpr_constraint(self):
        y=np.array([1,0,1,0,0]);p=np.array([.95,.9,.8,.7,.1])
        threshold=research.select_threshold(y,p,max_fpr=1/3)
        predicted=p>=threshold
        self.assertEqual(int(sum(predicted & (y==1))),2)
        self.assertLessEqual(float(np.mean(predicted[y==0])),1/3)

    def test_domain_grouping_includes_private_suffixes(self):
        self.assertNotEqual(research.identity('https://a.github.io/x')[1],research.identity('https://b.github.io/y')[1])
        self.assertEqual(research.identity('https://www.example.com/a')[1],research.identity('https://login.example.com/b')[1])

    def test_source_class_weights_have_equal_total_mass(self):
        rows=[('x',0,'d','primary')]*3+[('x',1,'d','primary')]+[('x',0,'d','phiusiil')]*2+[('x',1,'d','phiusiil')]*4
        weights=research.balanced_weights(rows)
        totals={key:sum(w for r,w in zip(rows,weights) if (r[3],r[1])==key) for key in {(r[3],r[1]) for r in rows}}
        self.assertLess(max(totals.values())-min(totals.values()),1e-5)

    def test_single_class_challenge_does_not_claim_auc_or_overall_accuracy(self):
        value=research.evaluate_slice(np.array([0,0]),np.array([.1,.8]),.5)
        self.assertNotIn('accuracy',value)
        self.assertNotIn('roc_auc',value)
        self.assertEqual(value['alert_rate'],.5)


if __name__=='__main__':unittest.main()
