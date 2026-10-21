"""ORB self-matching plus geometric consistency. Natural repetition can match."""
import cv2
import numpy as np


class CopyMoveAnalyzer:
    def analyze(self,gray):
        detector=cv2.ORB_create(nfeatures=800)
        points,descriptors=detector.detectAndCompute(gray,None)
        candidates=[]
        if descriptors is not None and len(descriptors)>=4:
            matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(descriptors,descriptors,k=4)
            seen=set()
            for neighbors in matches:
                for match in neighbors:
                    i,j=sorted((match.queryIdx,match.trainIdx))
                    if i==j or (i,j) in seen or match.distance>32:continue
                    a=np.asarray(points[i].pt);b=np.asarray(points[j].pt)
                    if np.linalg.norm(a-b)<32:continue
                    seen.add((i,j));candidates.append((a,b))
        coherent=0
        if len(candidates)>=6:
            votes={}
            for a,b in candidates:
                if tuple(a)>tuple(b):a,b=b,a
                key=tuple(np.round((b-a)/8).astype(int))
                votes.setdefault(key,[]).append((a,b))
            group=max(votes.values(),key=len)
            if len(group)>=6:
                _,inliers=cv2.estimateAffinePartial2D(np.float32([p[0] for p in group]),np.float32([p[1] for p in group]),
                    method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=500,confidence=.95)
                coherent=int(inliers.sum()) if inliers is not None else 0
        return {'descriptor_pairs':len(candidates),'geometric_inliers':coherent,
            'status':'REPEATED_PATTERN_CANDIDATES' if coherent>=6 else 'NO_COHERENT_PATTERN_FOUND',
            'note':'ORB self-matches with RANSAC are a copy-move diagnostic. Natural repetition can match; missing matches do not exclude copying. No edit regions are asserted.'}
