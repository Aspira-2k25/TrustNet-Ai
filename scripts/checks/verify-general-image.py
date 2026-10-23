"""Inspect candidate readiness; optional probe uses generated pixels, never user photos."""
import argparse
import io
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv
load_dotenv()
from models.image_deepfake.inference.general_image_client import GeneralImageClient

parser=argparse.ArgumentParser()
parser.add_argument('--probe-synthetic',action='store_true',help='Run a generated gradient through the explicitly configured backend')
args=parser.parse_args()
client=GeneralImageClient()
print(json.dumps(client.readiness(),indent=2))
if args.probe_synthetic:
    from PIL import Image
    image=Image.new('RGB',(64,64));image.putdata([(x*4,y*4,120) for y in range(64) for x in range(64)])
    stream=io.BytesIO();image.save(stream,format='PNG')
    result=client.predict(stream.getvalue())
    print(json.dumps(result,indent=2))
    print('Transport/runtime check only. This generated fixture does not measure accuracy.')
    sys.exit(0 if result['status']=='APPLIED' else 1)
sys.exit(0 if client.readiness()['ready'] else 1)
