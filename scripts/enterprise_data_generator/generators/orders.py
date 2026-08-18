"""
Sales Orders & Line Items Entity Generators.
"""

import uuid
import numpy as np
from typing import List, Tuple
from datetime import datetime, timedelta
from .base import BaseGenerator
from ..models import Customer, CustomerAddress, Product, Order, OrderItem

class OrderGenerator(BaseGenerator):
    CHANNELS = [1, 2, 3] # Direct Sales, E-Commerce, Distributor
    STATUSES = ["DELIVERED", "SHIPPED", "PROCESSING", "PENDING", "CANCELLED"]

    def generate_orders(
        self,
        count: int,
        customers: List[Customer],
        addresses: List[CustomerAddress],
        products: List[Product]
    ) -> Tuple[List[Order], List[OrderItem]]:
        orders = []
        order_items = []
        
        # Build address mapping per customer
        cust_address_map = {}
        for addr in addresses:
            if addr.address_type == "SHIPPING":
                cust_address_map[addr.customer_id] = addr.address_id
                
        # Pareto distribution weights for products (80/20 rule)
        n_prods = len(products)
        weights = np.exp(-np.linspace(0, 3, n_prods))
        weights /= weights.sum()
        
        start_date = datetime(2026, 1, 1)
        item_counter = 1
        
        for i in range(count):
            order_id = str(uuid.UUID(int=self.random.getrandbits(128)))
            order_number = f"ORD-2026-{i+10001:06d}"
            
            customer = self.random.choice(customers)
            shipping_addr_id = cust_address_map.get(customer.customer_id, addresses[0].address_id)
            channel_id = self.random.choice(self.CHANNELS)
            
            # Order timestamp over 180 days
            order_dt = start_date + timedelta(days=self.random.randint(0, 180), hours=self.random.randint(0, 23))
            promised_dt = (order_dt + timedelta(days=self.random.randint(3, 10))).date().isoformat()
            
            status = self.np_random.choice(self.STATUSES, p=[0.75, 0.12, 0.05, 0.05, 0.03])
            
            # Number of line items (1 to 6)
            n_items = int(self.np_random.poisson(lam=2.5)) + 1
            n_items = min(n_items, 8)
            
            # Pick products according to Pareto weights
            selected_prod_indices = self.np_random.choice(n_prods, size=n_items, replace=False, p=weights)
            
            total_order_amount = 0.0
            for idx in selected_prod_indices:
                prod = products[idx]
                qty = self.random.randint(1, 10)
                unit_price = prod.unit_price
                
                # Apply discount (0% to 15%)
                discount = round(unit_price * qty * float(self.random.choice([0.0, 0.05, 0.10, 0.15])), 2)
                line_total = round((qty * unit_price) - discount, 2)
                total_order_amount += line_total
                
                item = OrderItem(
                    order_item_id=item_counter,
                    order_id=order_id,
                    product_id=prod.product_id,
                    quantity=qty,
                    unit_price=unit_price,
                    discount_amount=discount,
                    total_price=line_total,
                )
                order_items.append(item)
                item_counter += 1
                
            order = Order(
                order_id=order_id,
                order_number=order_number,
                customer_id=customer.customer_id,
                channel_id=channel_id,
                shipping_address_id=shipping_addr_id,
                order_status=status,
                order_timestamp=order_dt.isoformat(),
                promised_delivery_date=promised_dt,
                total_amount=round(total_order_amount, 2),
            )
            orders.append(order)
            
        return orders, order_items
