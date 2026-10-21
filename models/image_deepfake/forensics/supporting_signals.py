"""Connect bounded classical observations; never feed them into verdict fusion."""
import io
import cv2
import numpy as np
from PIL import Image,ImageOps
from .ela_analyzer import ELAAnalyzer
from .noise_analyzer import NoiseAnalyzer
from .copy_move_analyzer import CopyMoveAnalyzer


def analyze(data):
    with Image.open(io.BytesIO(data)) as original:
        jpeg=original.format=='JPEG'
        image=ImageOps.exif_transpose(original).convert('RGB')
    width,height=image.size
    # Preserve native pixels and declare the central window's coverage.
    w,h=min(width,768),min(height,768);x,y=(width-w)//2,(height-h)//2
    sample=image.crop((x,y,x+w,y+h))
    gray=cv2.cvtColor(np.asarray(sample),cv2.COLOR_RGB2GRAY)
    ela,visual=ELAAnalyzer().analyze(sample,jpeg)
    return {'scope':{'x':x,'y':y,'width':w,'height':h,'native_pixels':True,
        'whole_image':(w,h)==(width,height)},'affects_verdict':False,
        'notice':'Supporting observations only. Texture, repeated objects, sharpening and compression can create these patterns in real photos. No calibrated tampering probability is inferred.',
        'ela':ela,'noise':NoiseAnalyzer().analyze(gray),
        'copy_move':CopyMoveAnalyzer().analyze(gray),
        'assets':{'ela':visual} if visual else {}}
