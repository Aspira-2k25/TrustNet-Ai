"""Atomic, trusted local training-state checkpoints. Never load untrusted files."""
import os
from pathlib import Path
import torch

def save(path, model, optimizer, signature, progress):
    path=Path(path);temporary=path.with_suffix('.tmp')
    state={'signature':signature,'progress':progress,'model':model.state_dict(),'optimizer':optimizer.state_dict(),'rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}
    torch.save(state,temporary);os.replace(temporary,path)

def restore(path, model, optimizer, signature, device):
    state=torch.load(path,map_location='cpu',weights_only=True)
    if state['signature']!=signature:raise ValueError('Resume dataset/configuration mismatch')
    model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer'])
    for values in optimizer.state.values():
        for name,value in values.items():
            if torch.is_tensor(value):values[name]=value.to(device)
    torch.set_rng_state(state['rng'])
    if torch.cuda.is_available() and state['cuda_rng']:torch.cuda.set_rng_state_all(state['cuda_rng'])
    return state['progress']
