"""Bounded classical observations. These are never verdict inputs or edit masks."""
import io
import cv2
import numpy as np
from PIL import Image,ImageOps
from .localization_output import encode_png


def analyze(data):
    with Image.open(io.BytesIO(data)) as original:
        jpeg=original.format=='JPEG'
        image=ImageOps.exif_transpose(original).convert('RGB')
    width,height=image.size
    # Keep native pixels. Limit diagnostic work to a declared central window,
    # rather than silently downscaling or claiming whole-image coverage.
    w,h=min(width,768),min(height,768);x,y=(width-w)//2,(height-h)//2
    sample=image.crop((x,y,x+w,y+h))
    rgb=np.asarray(sample);gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    values=gray.astype(np.float32)
    residual=values-cv2.GaussianBlur(values,(3,3),.8)
    output={'scope':{'x':x,'y':y,'width':w,'height':h,'native_pixels':True,
        'whole_image':(w,h)==(width,height)},'affects_verdict':False,
        'notice':'Supporting observations only. Texture, repeated objects, sharpening and compression can create these patterns in real photos. No calibrated tampering probability is inferred.',
        'noise':{'residual_rms':round(float(np.sqrt(np.mean(residual**2))),3),
            'unit':'8-bit luminance levels','note':'High-pass residual also contains ordinary edges and texture; it is not a sensor fingerprint or proof of AI.'},
        'assets':{}}
    if jpeg:
        buffer=io.BytesIO();sample.save(buffer,'JPEG',quality=90,subsampling=2)
        with Image.open(io.BytesIO(buffer.getvalue())) as recompressed:
            difference=np.abs(rgb.astype(np.float32)-np.asarray(recompressed.convert('RGB'),dtype=np.float32))
        output['ela']={'status':'APPLIED','reencode_quality':90,'fixed_display_gain':8,
            'mean_absolute_difference':round(float(difference.mean()),3),
            'note':'JPEG recompression difference at fixed 8x display gain. Bright pixels can occur on genuine edges; this is not a localized edit mask.'}
        output['assets']['ela']=encode_png(cv2.cvtColor(np.clip(difference*8,0,255).astype(np.uint8),cv2.COLOR_RGB2BGR))
    else:
        output['ela']={'status':'NOT_APPLICABLE','note':'ELA is limited to JPEG input. Converting PNG or WebP to JPEG would introduce a new compression history.'}
    # Self-matching descriptors find repeated visual patterns, not proven copies.
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
        # Orient pairs consistently before a translation vote. Repeated natural
        # objects can still satisfy RANSAC, which is why this never changes risk.
        votes={}
        for a,b in candidates:
            if tuple(a)>tuple(b):a,b=b,a
            delta=b-a;key=tuple(np.round(delta/8).astype(int))
            votes.setdefault(key,[]).append((a,b))
        group=max(votes.values(),key=len)
        if len(group)>=6:
            _,inliers=cv2.estimateAffinePartial2D(np.float32([p[0] for p in group]),np.float32([p[1] for p in group]),
                method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=500,confidence=.95)
            coherent=int(inliers.sum()) if inliers is not None else 0
    output['copy_move']={'descriptor_pairs':len(candidates),'geometric_inliers':coherent,
        'status':'REPEATED_PATTERN_CANDIDATES' if coherent>=6 else 'NO_COHERENT_PATTERN_FOUND',
        'note':'ORB self-matches with RANSAC are a copy-move diagnostic. Natural repetition can match; missing matches do not exclude copying. No edit regions are asserted.'}
    return output
