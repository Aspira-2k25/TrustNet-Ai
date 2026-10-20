"""Portable linear head and validation-relative two-stream AI warning score."""
import numpy as np


def sigmoid(value):
    return float(1/(1+np.exp(-np.clip(value,-40,40))))


def logit(value):
    p=np.clip(value,1e-9,1-1e-9)
    return float(np.log(p/(1-p)))


def head_score(embedding,head):
    x=np.asarray(embedding,dtype=np.float64)
    mean=np.asarray(head['mean']);scale=np.asarray(head['scale']);coef=np.asarray(head['coef'])
    if x.shape!=mean.shape or mean.shape!=scale.shape or scale.shape!=coef.shape or not np.isfinite(x).all() or not np.isfinite(coef).all() or not np.all(scale>0):
        raise ValueError('Modern image head feature dimensions or values are invalid')
    return sigmoid(float(((x-mean)/scale)@coef+head['intercept']))


def policy_score(primary,modern,config):
    # 0.5 means crossing one of the observed-real guard boundaries. It is
    # a normalized decision coordinate, not a raw classifier probability.
    return sigmoid(max(logit(primary)-logit(config['primary_raw_alert']),
                       logit(modern)-logit(config['modern_raw_alert'])))
