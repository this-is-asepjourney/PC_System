from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseCollector(ABC):
    """Base class for all system resource collectors"""
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Collect and return metric data as a dictionary"""
        pass
