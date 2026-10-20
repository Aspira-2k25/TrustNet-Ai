"""Validation operating points and source balancing, independent of experiment paths."""
from collections import Counter
from urllib.parse import urlsplit
import numpy as np
from models.phishing_url.inference.forensics import suffix_parser
from models.phishing_url.evaluation.metrics import metrics

def domain(host):return suffix_parser()(host).top_domain_under_public_suffix or host

def identity(url):
    p=urlsplit(url)
    host=(p.hostname or '').rstrip('.').encode('idna').decode('ascii').lower()
    if not host or p.scheme not in {'http','https'}:raise ValueError('Invalid URL')
    return (p.netloc.lower()+(p.path or '/')+('?' + p.query if p.query else ''))[:2048],domain(host)

def balanced_weights(rows):
    counts=Counter((r[3],r[1]) for r in rows)
    return np.asarray([len(rows)/(len(counts)*counts[r[3],r[1]]) for r in rows],dtype=np.float32)

def select_threshold(y,p,max_fpr=.01):
    # Exact validation-only operating points; choose maximum recall within FPR budget.
    order=np.argsort(-p,kind='stable'); sorted_p=p[order]; sorted_y=y[order]
    tp=np.cumsum(sorted_y);fp=np.cumsum(1-sorted_y)
    ends=np.r_[np.flatnonzero(sorted_p[:-1]!=sorted_p[1:]),len(p)-1]
    eligible=ends[fp[ends]/max(1,int(sum(y==0)))<=max_fpr]
    if not len(eligible):return float(np.nextafter(max(p),np.inf))
    best=max(eligible,key=lambda i:(int(tp[i]),-int(fp[i]),float(sorted_p[i])))
    return float(sorted_p[best])

def evaluate_slice(y,p,threshold):
    return metrics(y,p,threshold) if len(y) and len(np.unique(y))==2 else {'rows':len(y),'positive_rows':int(sum(y==1)),
        'alert_rate':float(np.mean(p>=threshold)) if len(y) else None,'note':'Single-class slice; no overall accuracy/AUC claim.'}
