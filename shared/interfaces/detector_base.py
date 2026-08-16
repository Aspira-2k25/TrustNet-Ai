from abc import ABC, abstractmethod
from typing import Any
from shared.schemas.detection_result import DetectionResult

class BaseDetector(ABC):
    """
    Abstract base class for all TrustNet AI detectors.
    
    Model internals, weights, architectures, and inference strategies may change freely 
    within each specific service. However, this interface is the strict, stable contract 
    between the raw model and the service wrapper orchestrating it. This interface may 
    not be changed or extended without a coordinated schema version bump across every 
    consumer and the Trust Score Engine.
    """
    
    @abstractmethod
    def predict(self, input_data: Any) -> DetectionResult:
        """
        Executes the detection logic on the given input and returns a structured DetectionResult.
        
        Args:
            input_data (Any): The payload to analyze. The exact type (e.g., bytes, string, URL, 
                              file path) is determined by the specific concrete detector 
                              implementation for a given modality.
        
        Returns:
            DetectionResult: The standardized result of the detection.
        """
        pass
