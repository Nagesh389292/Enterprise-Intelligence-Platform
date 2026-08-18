"""
NULL Value and Missing Attribute Defect Injector.
"""

from .base import BaseCorruptor

class NullCorruptor(BaseCorruptor):
    def corrupt_orders(self, orders: list) -> list:
        for order in orders:
            if self.random.random() < self.corrupt_rate:
                # Inject null order status or delivery date
                setattr(order, "promised_delivery_date", None)
                setattr(order, "_injected_defect", "NULL_DELIVERY_DATE")
        return orders

class DuplicateCorruptor(BaseCorruptor):
    def corrupt_orders(self, orders: list) -> list:
        corrupted = list(orders)
        n_dups = int(len(orders) * self.corrupt_rate)
        if n_dups > 0 and len(orders) > 0:
            sample = self.random.sample(orders, n_dups)
            for item in sample:
                kwargs = {k: v for k, v in item.__dict__.items() if k != "_injected_defect"}
                dup = type(item)(**kwargs)
                setattr(dup, "_injected_defect", "DUPLICATE_RECORD")
                corrupted.append(dup)
        return corrupted

class OutlierCorruptor(BaseCorruptor):
    def corrupt_telemetry(self, telemetry: list) -> list:
        for record in telemetry:
            if self.random.random() < self.corrupt_rate:
                # Inject extreme impossible temperature outlier
                setattr(record, "temperature_c", 999.99)
                setattr(record, "_injected_defect", "EXTREME_TEMP_OUTLIER")
        return telemetry
