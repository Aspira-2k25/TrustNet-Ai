"""Bounded second-expert rescue; never removes a primary model alert."""
import math
from .regional_model import RegionalModel,region


class RecallModel(RegionalModel):
    def __init__(self,root,manifest):
        super().__init__(root,manifest)
        if set(manifest.get('rescue',{}))!={'root','query','path'}:
            raise ValueError('Recall policy must cover every URL shape')
        for shape,rule in manifest['rescue'].items():
            if rule is None:continue
            threshold=rule.get('threshold')
            if rule.get('expert') not in {'baseline','correction'} or rule['expert']==manifest['routing'][shape]['expert']:
                raise ValueError('Rescue must use a different checked expert')
            if not isinstance(threshold,(int,float)) or not math.isfinite(threshold) or not .9<=threshold<1:
                raise ValueError('Invalid high-confidence rescue threshold')

    def predict_url(self,url,unused_features):
        p,threshold,meta=super().predict_url(url,unused_features)
        meta.update(recall_policy='expert-rescue-v1',rescue_applied=False,
                    primary_model_probability=p,primary_model_threshold=threshold)
        rule=self.manifest['rescue'][region(url)]
        if p<threshold and rule is not None:
            other=meta['expert_estimates'][rule['expert']]
            if other>=rule['threshold']:
                p,threshold=other,rule['threshold']
                meta.update(rescue_applied=True,rescue_expert=rule['expert'],
                            selected_expert='rescue_'+rule['expert'],rescue_threshold=threshold)
        return p,threshold,meta
