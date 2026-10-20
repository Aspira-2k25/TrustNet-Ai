"""Abstentions must not inflate the headline recall or F1."""
import pytest
from benchmark.run import metrics


def test_abstained_positives_count_as_misses_in_headline_f1():
    rows=[{'positive':True,'prediction':True,'score':.9} for _ in range(6)]
    rows += [{'positive':True,'prediction':None,'score':.5} for _ in range(10)]
    rows += [{'positive':False,'prediction':None,'score':.1} for _ in range(16)]
    result=metrics(rows)
    assert result['recall']==.375
    assert result['f1']==pytest.approx(12/22)
    assert result['inconclusive_share']==26/32
    assert result['selective_f1']==1
