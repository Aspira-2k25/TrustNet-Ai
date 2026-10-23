"""Check the selected image runtime; readiness does not establish accuracy."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from models.image_deepfake.inference.efficientnet_detector import EfficientNetDetector
parser=argparse.ArgumentParser();parser.add_argument('--policy',choices=['image-vit-v3','image-screening-v2','image-general-v4'])
args=parser.parse_args();state=EfficientNetDetector(policy=args.policy).readiness()
print(json.dumps(state,indent=2))
print('Runtime readiness is separate from a validated decision policy and accuracy.')
sys.exit(0 if state['ready'] else 1)
