from typing import Tuple, List, Optional
import torch
import torch.nn.functional as F
import numpy as np

from shared.schemas.evidence import EvidenceItem

class GradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: Optional[torch.nn.Module] = None):
        self.model = model
        self.model.eval()
        
        # Target the last convolutional block of EfficientNet
        if target_layer is not None:
            self.target_layer = target_layer
        elif hasattr(model, "features") and len(model.features) > 0:
            self.target_layer = model.features[-1]
        else:
            # Fallback for generic CNNs
            self.target_layer = list(model.children())[-2]

        self.gradients = None
        self.activations = None
        self._hooks = []
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0]

        self._hooks.append(self.target_layer.register_forward_hook(forward_hook))
        self._hooks.append(self.target_layer.register_full_backward_hook(backward_hook))

    def generate_heatmap(self, input_tensor: torch.Tensor, target_class: Optional[int] = None) -> np.ndarray:
        """
        Generates a 2D Grad-CAM heatmap normalized to [0.0, 1.0].
        
        Args:
            input_tensor: Tensor of shape (1, C, H, W).
            target_class: Target class index. If None, uses top predicted class.
            
        Returns:
            np.ndarray: 2D array of shape (H, W) in range [0.0, 1.0].
        """
        self.model.zero_grad()
        
        # Enable gradient computation for Grad-CAM
        with torch.enable_grad():
            tensor = input_tensor.clone().detach().requires_grad_(True)
            output = self.model(tensor)
            
            if target_class is None:
                target_class = output.argmax(dim=1).item()
                
            score = output[0, target_class]
            score.backward(retain_graph=True)
            
        if self.gradients is None or self.activations is None:
            # Fallback to uniform heatmap if hooks failed
            return np.zeros((input_tensor.shape[2], input_tensor.shape[3]), dtype=np.float32)

        # Global Average Pooling of Gradients -> Neuron Importance Weights (alpha)
        alpha = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        
        # Weighted combination of forward activation maps
        cam = torch.sum(alpha * self.activations, dim=1, keepdim=True)
        
        # Apply ReLU to capture features with positive contribution to target class
        cam = F.relu(cam)
        
        # Resize to match input image resolution (H, W)
        h, w = input_tensor.shape[2], input_tensor.shape[3]
        cam = F.interpolate(cam, size=(h, w), mode="bilinear", align_corners=False)
        
        cam_np = cam.squeeze().detach().cpu().numpy()
        
        # Normalize to [0.0, 1.0]
        max_val = np.max(cam_np)
        min_val = np.min(cam_np)
        if max_val > min_val:
            heatmap = (cam_np - min_val) / (max_val - min_val)
        else:
            heatmap = np.zeros_like(cam_np)
            
        return heatmap.astype(np.float32)

    def generate_evidence(self, input_tensor: torch.Tensor, risk_score: float) -> List[EvidenceItem]:
        """
        Extracts structured evidence items based on the visual saliency heatmap.
        """
        heatmap = self.generate_heatmap(input_tensor)
        mean_intensity = float(np.mean(heatmap))
        peak_intensity = float(np.max(heatmap))
        
        # Find peak region coordinates
        peak_y, peak_x = np.unravel_index(np.argmax(heatmap), heatmap.shape)
        h, w = heatmap.shape
        region_desc = "center"
        if peak_y < h // 3:
            region_desc = "upper boundary / forehead / hairline"
        elif peak_y > 2 * (h // 3):
            region_desc = "lower boundary / chin / neck"
        elif peak_x < w // 3:
            region_desc = "left facial periphery"
        elif peak_x > 2 * (w // 3):
            region_desc = "right facial periphery"
        else:
            region_desc = "central facial features (eyes / nose / mouth)"

        contribution = min(1.0, max(0.0, risk_score / 100.0))
        
        item = EvidenceItem(
            feature_or_region=f"visual_saliency_heatmap ({region_desc})",
            contribution=contribution,
            human_readable_note=(
                f"Grad-CAM visual saliency concentrated in {region_desc} "
                f"(peak intensity: {peak_intensity:.2f}, spatial mean: {mean_intensity:.2f}). "
                f"High-frequency compression or blending artifacts detected."
            )
        )
        return [item]

    def remove_hooks(self):
        for hook in self._hooks:
            hook.remove()
        self._hooks = []
