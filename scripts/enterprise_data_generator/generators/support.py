"""
Customer Support Domain Entity Generators.
"""

import uuid
from typing import List, Tuple
from datetime import datetime, timedelta
from .base import BaseGenerator
from ..models import Customer, Order, SupportTicket, CustomerSatisfaction

class SupportGenerator(BaseGenerator):
    CATEGORIES = ["DEFECT", "DELAY", "BILLING", "INQUIRY", "DAMAGE"]
    PRIORITIES = ["LOW", "MEDIUM", "HIGH", "URGENT"]

    def generate_support(
        self,
        count: int,
        customers: List[Customer],
        orders: List[Order]
    ) -> Tuple[List[SupportTicket], List[CustomerSatisfaction]]:
        tickets = []
        surveys = []
        
        start_date = datetime(2026, 1, 1)
        
        for i in range(count):
            t_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            t_num = f"TCK-2026-{i+10001:05d}"
            
            customer = self.random.choice(customers)
            # 60% of tickets linked to orders
            order_id = self.random.choice(orders).order_id if self.random.random() < 0.60 else None
            
            category = self.random.choice(self.CATEGORIES)
            priority = self.np_random.choice(self.PRIORITIES, p=[0.40, 0.35, 0.20, 0.05])
            
            created_dt = start_date + timedelta(days=self.random.randint(0, 180))
            status = self.np_random.choice(["CLOSED", "RESOLVED", "OPEN"], p=[0.70, 0.20, 0.10])
            
            resolved_dt = None
            if status in ["CLOSED", "RESOLVED"]:
                hours = self.random.randint(2, 72)
                resolved_dt = (created_dt + timedelta(hours=hours)).isoformat()
                
            ticket = SupportTicket(
                ticket_id=t_id,
                ticket_number=t_num,
                customer_id=customer.customer_id,
                order_id=order_id,
                issue_category=category,
                priority=priority,
                status=status,
                created_at=created_dt.isoformat(),
                resolved_at=resolved_dt
            )
            tickets.append(ticket)
            
            # CSAT Survey for resolved tickets
            if status == "CLOSED" and self.random.random() < 0.80:
                s_id = str(uuid.UUID(int=self.random.getrandbits(128)))
                
                # Delayed or High priority tickets get lower CSAT mean
                if priority in ["HIGH", "URGENT"] or category == "DELAY":
                    score = int(self.np_random.choice([1, 2, 3, 4, 5], p=[0.30, 0.30, 0.20, 0.10, 0.10]))
                else:
                    score = int(self.np_random.choice([1, 2, 3, 4, 5], p=[0.05, 0.05, 0.10, 0.30, 0.50]))
                    
                feedback = self.faker.sentence() if score <= 3 else "Satisfactory service."
                
                surveys.append(CustomerSatisfaction(
                    survey_id=s_id,
                    ticket_id=t_id,
                    score=score,
                    feedback_text=feedback,
                    submitted_at=resolved_dt
                ))
                
        return tickets, surveys
