"""
Supplier & Warehouse Domain Entity Generators.
"""

import uuid
from typing import List
from .base import BaseGenerator
from ..models import Supplier, Warehouse

class SupplyChainBaseGenerator(BaseGenerator):
    REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America"]
    COUNTRIES = ["US", "DE", "JP", "CN", "GB", "MX"]

    def generate_suppliers(self, count: int) -> List[Supplier]:
        suppliers = []
        for i in range(count):
            sup_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            code = f"SUP-{i+101:03d}"
            name = f"{self.faker.company()} Industrial Supplies"
            rating = round(float(self.np_random.uniform(3.5, 5.0)), 2)
            lead_time = self.random.choice([7, 14, 21, 28])
            country = self.random.choice(self.COUNTRIES)
            
            suppliers.append(Supplier(sup_id, code, name, rating, lead_time, country))
        return suppliers

    def generate_warehouses(self, count: int) -> List[Warehouse]:
        warehouses = []
        locations = [
            ("WH-NA-CHICAGO", "Chicago Logistics Hub", "North America", 250000),
            ("WH-EU-BERLIN", "Berlin Fulfillment Center", "Europe", 200000),
            ("WH-APAC-TOKYO", "Tokyo Distribution Hub", "Asia-Pacific", 180000),
            ("WH-LATAM-MEXICO", "Mexico City Central Hub", "Latin America", 150000),
            ("WH-NA-DALLAS", "Dallas Regional Depot", "North America", 175000),
            ("WH-EU-ROTTERDAM", "Rotterdam Port Facility", "Europe", 220000),
            ("WH-APAC-SINGAPORE", "Singapore Global Gateway", "Asia-Pacific", 160000),
            ("WH-NA-SEATTLE", "Seattle Northwest Facility", "North America", 140000)
        ]
        
        for i in range(min(count, len(locations))):
            wh_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            code, name, region, cap = locations[i]
            warehouses.append(Warehouse(wh_id, code, name, region, cap))
            
        return warehouses
