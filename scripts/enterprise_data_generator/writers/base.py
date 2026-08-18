"""
Abstract Base Writer Interface for Persisting Generated Entities.
"""

from abc import ABC, abstractmethod
from typing import List, Dict

class BaseWriter(ABC):
    @abstractmethod
    def write(self, dataset: Dict[str, List], output_dir: str):
        pass
