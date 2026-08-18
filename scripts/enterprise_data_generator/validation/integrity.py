"""
Post-Generation Relational Integrity & Data Contract Validation Engine.
"""

from typing import Dict, List, Tuple

class IntegrityValidator:
    def validate_dataset(self, dataset: Dict[str, List]) -> Tuple[bool, List[str]]:
        errors = []
        
        # Extract ID sets for referential integrity checks
        cust_ids = {c.customer_id for c in dataset.get("customers", [])}
        prod_ids = {p.product_id for p in dataset.get("products", [])}
        wh_ids = {w.warehouse_id for w in dataset.get("warehouses", [])}
        order_ids = {o.order_id for o in dataset.get("orders", [])}
        machine_ids = {m.machine_id for m in dataset.get("machines", [])}
        ticket_ids = {t.ticket_id for t in dataset.get("support_tickets", [])}
        
        # 1. Validate Customer Address FKs
        for addr in dataset.get("customer_addresses", []):
            if addr.customer_id not in cust_ids:
                errors.append(f"CustomerAddress '{addr.address_id}' references non-existent Customer '{addr.customer_id}'")
                
        # 2. Validate Order FKs & Totals
        for order in dataset.get("orders", []):
            if order.customer_id not in cust_ids:
                errors.append(f"Order '{order.order_id}' references non-existent Customer '{order.customer_id}'")
            if order.total_amount < 0:
                errors.append(f"Order '{order.order_id}' has negative total_amount: {order.total_amount}")
                
        # 3. Validate OrderItem FKs & Quantities
        for item in dataset.get("order_items", []):
            if item.order_id not in order_ids:
                errors.append(f"OrderItem '{item.order_item_id}' references non-existent Order '{item.order_id}'")
            if item.product_id not in prod_ids:
                errors.append(f"OrderItem '{item.order_item_id}' references non-existent Product '{item.product_id}'")
            if item.quantity <= 0:
                errors.append(f"OrderItem '{item.order_item_id}' has non-positive quantity: {item.quantity}")
                
        # 4. Validate Inventory FKs
        for inv in dataset.get("inventory", []):
            if inv.warehouse_id not in wh_ids:
                errors.append(f"Inventory '{inv.inventory_id}' references non-existent Warehouse '{inv.warehouse_id}'")
            if inv.product_id not in prod_ids:
                errors.append(f"Inventory '{inv.inventory_id}' references non-existent Product '{inv.product_id}'")
                
        # 5. Validate Machine Telemetry FKs
        for telem in dataset.get("machine_telemetry", []):
            if telem.machine_id not in machine_ids:
                errors.append(f"MachineTelemetry '{telem.telemetry_id}' references non-existent Machine '{telem.machine_id}'")
                
        # 6. Validate CSAT FKs
        for csat in dataset.get("customer_satisfaction", []):
            if csat.ticket_id not in ticket_ids:
                errors.append(f"CSAT '{csat.survey_id}' references non-existent Ticket '{csat.ticket_id}'")
            if not (1 <= csat.score <= 5):
                errors.append(f"CSAT '{csat.survey_id}' score out of range [1-5]: {csat.score}")
                
        is_valid = (len(errors) == 0)
        return is_valid, errors
