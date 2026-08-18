"""
Customer Domain Entity Generators.
"""

import uuid
from typing import List, Tuple
from datetime import datetime, timedelta
from .base import BaseGenerator
from ..models import CustomerSegment, Customer, CustomerAddress

class CustomerGenerator(BaseGenerator):
    INDUSTRIES = [
        "Automotive", "Aerospace", "Industrial Manufacturing", "Energy & Utilities",
        "Electronics", "Medical Devices", "Heavy Equipment", "Logistics"
    ]
    
    ADDRESS_TYPES = ["BILLING", "SHIPPING"]
    COUNTRY_CODES = ["US", "DE", "JP", "GB", "FR", "CA", "AU"]

    def generate_segments(self) -> List[CustomerSegment]:
        now = datetime(2026, 1, 1).isoformat()
        return [
            CustomerSegment(1, "ENTERPRISE", "Enterprise Clients", 1000000.00, now),
            CustomerSegment(2, "MID_MARKET", "Mid-Market Corporate", 250000.00, now),
            CustomerSegment(3, "SMB", "Small & Medium Business", 5000.00, now),
        ]

    def generate_customers(self, count: int, segments: List[CustomerSegment]) -> Tuple[List[Customer], List[CustomerAddress]]:
        customers = []
        addresses = []
        
        start_date = datetime(2024, 1, 1)
        
        for i in range(count):
            cust_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            company_name = f"{self.faker.company()} {self.faker.company_suffix()}"
            industry = self.random.choice(self.INDUSTRIES)
            
            # Segment probabilities: 10% Enterprise, 30% Mid Market, 60% SMB
            seg_idx = self.np_random.choice([0, 1, 2], p=[0.10, 0.30, 0.60])
            segment = segments[seg_idx]
            
            if segment.segment_code == "ENTERPRISE":
                credit_limit = float(self.random.randint(500, 2000) * 1000)
            elif segment.segment_code == "MID_MARKET":
                credit_limit = float(self.random.randint(50, 250) * 1000)
            else:
                credit_limit = float(self.random.randint(10, 50) * 1000)
                
            status = self.np_random.choice(["ACTIVE", "INACTIVE", "CHURNED"], p=[0.80, 0.12, 0.08])
            
            created_days = self.random.randint(0, 730)
            created_dt = start_date + timedelta(days=created_days)
            created_str = created_dt.isoformat()
            
            email = f"contact@{self.faker.domain_name()}"
            phone = self.faker.phone_number()[:20]
            
            customer = Customer(
                customer_id=cust_id,
                company_name=company_name,
                industry=industry,
                segment_id=segment.segment_id,
                account_status=status,
                contact_email=email,
                contact_phone=phone,
                credit_limit=credit_limit,
                created_at=created_str,
                updated_at=created_str,
            )
            customers.append(customer)
            
            # Primary Billing Address
            billing_addr = CustomerAddress(
                address_id=str(uuid.UUID(int=self.random.getrandbits(128))),
                customer_id=cust_id,
                address_type="BILLING",
                street_address=self.faker.street_address(),
                city=self.faker.city(),
                state_province=self.faker.state(),
                postal_code=self.faker.postcode(),
                country_code=self.random.choice(self.COUNTRY_CODES),
                is_primary=True,
                created_at=created_str,
            )
            addresses.append(billing_addr)
            
            # Shipping Address
            shipping_addr = CustomerAddress(
                address_id=str(uuid.UUID(int=self.random.getrandbits(128))),
                customer_id=cust_id,
                address_type="SHIPPING",
                street_address=self.faker.street_address(),
                city=self.faker.city(),
                state_province=self.faker.state(),
                postal_code=self.faker.postcode(),
                country_code=billing_addr.country_code,
                is_primary=True,
                created_at=created_str,
            )
            addresses.append(shipping_addr)
            
        return customers, addresses
