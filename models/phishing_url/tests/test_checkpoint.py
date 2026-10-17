import tempfile
from pathlib import Path
import unittest
import torch
from models.phishing_url.training.checkpoint import save,restore

class CheckpointTests(unittest.TestCase):
    def test_optimizer_rng_and_parameters_resume(self):
        torch.manual_seed(42)
        model=torch.nn.Linear(2,1);optimizer=torch.optim.AdamW(model.parameters())
        signature={'dataset':'fixture','batch_size':2}
        def step():
            optimizer.zero_grad();loss=model(torch.randn(2,2)).square().mean();loss.backward();optimizer.step()
        step()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'resume.pt'
            save(path,model,optimizer,signature,{'epoch':0,'next_step':1})
            step();expected={key:value.clone() for key,value in model.state_dict().items()}
            restored=restore(path,model,optimizer,signature,'cpu')
            self.assertEqual(restored['next_step'],1)
            step()
            for key,value in model.state_dict().items():self.assertTrue(torch.equal(value,expected[key]))
            with self.assertRaises(ValueError):restore(path,model,optimizer,{'dataset':'other'},'cpu')
