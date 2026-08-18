"""
Product & Catalog Domain Entity Generators.
"""

import uuid
from typing import List, Tuple
from datetime import datetime
from .base import BaseGenerator
from ..models import ProductCategory, Product

class ProductGenerator(BaseGenerator):
    CATEGORIES = [
        "Hydraulics & Pneumatics", "Industrial Fasteners", "Bearings & Power Transmission",
        "Electrical & Automation", "Raw Metals & Alloys", "Cutting Tools & Abrasives",
        "Pumps & Valves", "Sensors & Instrumentation", "Safety & Environmental", "Pipes & Fittings"
    ]

    def generate_categories(self) -> List[ProductCategory]:
        now = datetime(2026, 1, 1).isoformat()
        categories = []
        for i, name in enumerate(self.CATEGORIES, 1):
            categories.append(ProductCategory(i, name, None, now))
        return categories

    def generate_products(self, count: int, categories: List[ProductCategory]) -> List[Product]:
        products = []
        now = datetime(2026, 1, 1).isoformat()
        
        for i in range(count):
            prod_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            sku = f"SKU-{self.random.randint(100,999)}-{i+1000:04d}"
            category = self.random.choice(categories)
            
            unit_cost = round(float(self.np_random.uniform(10.0, 500.0)), 2)
            margin = float(self.np_random.uniform(1.25, 2.10))
            unit_price = round(unit_cost * margin, 2)
            reorder_point = self.random.choice([50, 100, 200, 500])
            
            product = Product(
                product_id=prod_id,
                sku=sku,
                product_name=f"{category.category_name[:-1]} Component Grade-{self.random.choice(['A','B','C'])}",
                category_id=category.category_id,
                unit_cost=unit_cost,
                unit_price=unit_price,
                reorder_point=reorder_point,
                is_active=True,
                created_at=now,
            )
            products.append(product)
            
        return products
