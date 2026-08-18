"""
Abstract Base Corruptor Class for Data Quality Defect Injection.
Defects are injected ONLY over raw dataset records prior to ingestion.
"""

from abc import ABC, abstractmethod
import random

class BaseCorruptor(ABC):
    def __init__(self, corrupt_rate: float = 0.05, seed: int = 42):
        self.corrupt_rate = corrupt_rate
        self.random = random.Random(seed)

    def corrupt(self, records: list) -> list:
        return records
