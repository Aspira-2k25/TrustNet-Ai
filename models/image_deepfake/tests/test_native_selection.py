from benchmark.native_pipeline import development_rank,needs_openclip


def candidate(recall=.8,primary=.9,auc=.5,names=('community','dino')):
    return {'choice':{'selection_recall':recall,'selection_real_fpr':.01},
            'development_primary':{'selection_recall':primary},
            'original_metadata_shortcut_auc':auc,'backbones':names}


def test_more_compute_requires_a_development_need_and_no_known_source_shortcut():
    assert needs_openclip(candidate())
    assert not needs_openclip(candidate(auc=1.))
    assert not needs_openclip(candidate(recall=.95))


def test_candidate_choice_uses_development_not_test_outcomes_and_prefers_cheaper_ties():
    smaller=candidate();larger=candidate(names=('community','dino','openclip'))
    smaller['test_recall']=0.;larger['test_recall']=1.
    assert development_rank(smaller)>development_rank(larger)
    assert development_rank(candidate(recall=.9))>development_rank(smaller)
