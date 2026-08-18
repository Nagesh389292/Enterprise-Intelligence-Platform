"""
Abstract Base Generator with Seed Management.
"""

from abc import ABC, abstractmethod
import random
import numpy as np
from faker import Faker

class BaseGenerator(ABC):
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.random = random.Random(seed)
        self.np_random = np.random.default_rng(seed)
        self.faker = Faker()
        Faker.seed(seed)

    def generate(self, *args, **kwargs):
        pass
