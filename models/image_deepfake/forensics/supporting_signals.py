"""Connect bounded classical observations; never feed them into verdict fusion."""
import io
import cv2
import numpy as np
from PIL import Image,ImageOps
from .ela_analyzer import ELAAnalyzer
from .noise_analyzer import NoiseAnalyzer
from .copy_move_analyzer import CopyMoveAnalyzer
from .localization_output import encode_png


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
    values=gray.astype(np.float32)
    residual=np.abs(values-cv2.GaussianBlur(values,(3,3),.8))
    noise_view=cv2.applyColorMap(np.clip(residual*8,0,255).astype(np.uint8),cv2.COLORMAP_INFERNO)
    # This is a frequency-domain display, never an image-coordinate edit map.
    spectrum=np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(values-values.mean()))))
    upper=float(np.percentile(spectrum,99.5))
    display=np.clip(spectrum/max(upper,1e-9)*255,0,255).astype(np.uint8)
    frequency_view=cv2.applyColorMap(display,cv2.COLORMAP_INFERNO)
    # Zero-mean filters avoid presenting flat brightness as texture evidence.
    responses=[]
    for angle in (0,np.pi/4,np.pi/2,3*np.pi/4):
        kernel=cv2.getGaborKernel((21,21),3,angle,8,.5,0,ktype=cv2.CV_32F)
        kernel-=kernel.mean();kernel/=max(float(np.abs(kernel).sum()),1e-9)
        responses.append(np.abs(cv2.filter2D(values,cv2.CV_32F,kernel)))
    energy=np.max(responses,axis=0)
    ceiling=float(np.percentile(energy,99.5))
    gabor_view=cv2.applyColorMap(np.clip(energy/max(ceiling,1e-5)*255,0,255).astype(np.uint8),cv2.COLORMAP_INFERNO)
    repeated=CopyMoveAnalyzer().analyze(gray)
    views={'noise':encode_png(noise_view),'frequency':encode_png(frequency_view),
        'gabor':encode_png(gabor_view),'diagnostic_original':encode_png(cv2.cvtColor(np.asarray(sample),cv2.COLOR_RGB2BGR))}
    if visual:views['ela']=visual
    if repeated['matches']:
        marked=cv2.cvtColor(np.asarray(sample),cv2.COLOR_RGB2BGR)
        for pair in repeated['matches']:
            a=tuple(round(v) for v in pair['from']);b=tuple(round(v) for v in pair['to'])
            cv2.line(marked,a,b,(30,170,240),1,cv2.LINE_AA)
            cv2.circle(marked,a,4,(0,210,180),1,cv2.LINE_AA)
            cv2.circle(marked,b,4,(30,170,240),1,cv2.LINE_AA)
        views['repetition']=encode_png(marked)
    return {'scope':{'x':x,'y':y,'width':w,'height':h,'native_pixels':True,
        'whole_image':(w,h)==(width,height)},'affects_verdict':False,
        'notice':'Supporting observations only. Texture, repeated objects, sharpening and compression can create these patterns in real photos. No calibrated tampering probability is inferred.',
        'ela':ela,'noise':NoiseAnalyzer().analyze(gray),
        'copy_move':repeated,
        'gabor':{'method':'Zero-mean Gabor filter bank, four orientations',
            'orientation_degrees':[0,45,90,135],
            'mean_response':[float(response.mean()) for response in responses],
            'display_normalization':'99.5th percentile of this window',
            'note':'Highlights oriented texture and edges, including natural fabric and buildings. This is not an AI probability or an edited-area mask.'},
        'frequency':{'method':'Centered FFT log magnitude','display_normalization':'99.5th percentile of this window',
            'note':'The centre contains low spatial frequencies; the edges contain higher frequencies. Patterns can come from normal texture and processing. This is not an edit mask or a validated AI score.'},
        'visual_notes':{'noise':'Absolute high-pass detail at fixed 8x gain. Bright areas include natural edges, texture and compression.',
            'repetition':'Lines connect geometrically consistent ORB matches. Repeated objects can match in real photos; these are candidates, not verified copied areas.'},
        'assets':views}
