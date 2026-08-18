"""
Warehouse Inventory Entity Generator.
"""

from typing import List
from datetime import datetime
from .base import BaseGenerator
from ..models import Product, Warehouse, Inventory

class InventoryGenerator(BaseGenerator):
    def generate_inventory(self, warehouses: List[Warehouse], products: List[Product]) -> List[Inventory]:
        inventory_records = []
        counter = 1
        now = datetime(2026, 6, 30).isoformat()
        
        for wh in warehouses:
            for prod in products:
                on_hand = self.random.randint(50, 1000)
                allocated = self.random.randint(0, min(on_hand, 100))
                
                inv = Inventory(
                    inventory_id=counter,
                    warehouse_id=wh.warehouse_id,
                    product_id=prod.product_id,
                    quantity_on_hand=on_hand,
                    quantity_allocated=allocated,
                    last_count_date=now,
                )
                inventory_records.append(inv)
                counter += 1
                
        return inventory_records
