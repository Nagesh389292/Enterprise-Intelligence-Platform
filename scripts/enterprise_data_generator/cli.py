"""
Enterprise Data Generation Engine CLI Entrypoint.
"""

import os
import time
import yaml
import argparse
from typing import Dict, List

from .generators import (
    CustomerGenerator, ProductGenerator, SupplyChainBaseGenerator,
    OrderGenerator, InventoryGenerator, OperationsGenerator, SupportGenerator
)
from .corruption import NullCorruptor, DuplicateCorruptor, OutlierCorruptor
from .writers import ParquetWriter, CSVWriter
from .validation import IntegrityValidator

def load_config(profile_name: str) -> dict:
    base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, "config", f"{profile_name}.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Profile config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_dataset(profile: str = "development", seed: int = 42, corrupt_rate: float = 0.0) -> Dict[str, List]:
    config = load_config(profile)
    counts = config["counts"]
    
    # 1. Initialize domain generators with seed
    cust_gen = CustomerGenerator(seed=seed)
    prod_gen = ProductGenerator(seed=seed)
    sc_gen = SupplyChainBaseGenerator(seed=seed)
    ord_gen = OrderGenerator(seed=seed)
    inv_gen = InventoryGenerator(seed=seed)
    ops_gen = OperationsGenerator(seed=seed)
    supp_gen = SupportGenerator(seed=seed)
    
    # 2. Level 0 & Level 1: Base Dimensions & Customers / Products / Suppliers / Warehouses
    segments = cust_gen.generate_segments()
    customers, addresses = cust_gen.generate_customers(counts["customers"], segments)
    
    categories = prod_gen.generate_categories()
    products = prod_gen.generate_products(counts["products"], categories)
    
    suppliers = sc_gen.generate_suppliers(counts["suppliers"])
    warehouses = sc_gen.generate_warehouses(counts["warehouses"])
    
    # 3. Level 3 & Level 4: Orders, OrderItems, Inventory
    orders, order_items = ord_gen.generate_orders(counts["orders"], customers, addresses, products)
    inventory = inv_gen.generate_inventory(warehouses, products)
    
    # 4. Level 3 & Level 4: Machines, Telemetry, Maintenance, Failures
    m_types = ops_gen.generate_machine_types()
    machines = ops_gen.generate_machines(counts["machines"], m_types, warehouses)
    telemetry, maintenance, failures = ops_gen.generate_telemetry_and_events(
        machines, counts["telemetry_readings_per_machine"]
    )
    
    # 5. Level 5 & Level 6: Support Tickets & CSAT
    tickets, csat = supp_gen.generate_support(counts["support_tickets"], customers, orders)
    
    dataset = {
        "customer_segments": segments,
        "customers": customers,
        "customer_addresses": addresses,
        "product_categories": categories,
        "products": products,
        "suppliers": suppliers,
        "warehouses": warehouses,
        "orders": orders,
        "order_items": order_items,
        "inventory": inventory,
        "machine_types": m_types,
        "machines": machines,
        "machine_telemetry": telemetry,
        "maintenance_events": maintenance,
        "failure_events": failures,
        "support_tickets": tickets,
        "customer_satisfaction": csat,
    }
    
    # Apply post-generation raw corruption if requested
    if corrupt_rate > 0.0:
        null_c = NullCorruptor(corrupt_rate=corrupt_rate, seed=seed)
        dup_c = DuplicateCorruptor(corrupt_rate=corrupt_rate, seed=seed)
        out_c = OutlierCorruptor(corrupt_rate=corrupt_rate, seed=seed)
        
        dataset["orders"] = null_c.corrupt_orders(dataset["orders"])
        dataset["orders"] = dup_c.corrupt_orders(dataset["orders"])
        dataset["machine_telemetry"] = out_c.corrupt_telemetry(dataset["machine_telemetry"])
        
    return dataset

def main():
    parser = argparse.ArgumentParser(description="Enterprise Data Generation Engine CLI")
    parser.add_argument("command", choices=["generate"], help="Command to execute")
    parser.add_argument("--profile", default="development", choices=["development", "integration", "scale"], help="Dataset sizing profile")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--format", default="parquet", choices=["parquet", "csv"], help="Output format")
    parser.add_argument("--output", default="data/raw/generated", help="Output directory path")
    parser.add_argument("--corrupt-rate", type=float, default=0.0, help="Raw data quality corruption probability")
    
    args = parser.parse_args()
    
    print("==================================================")
    print("Enterprise Data Generation Engine")
    print("==================================================")
    print(f"Profile:       {args.profile}")
    print(f"Random Seed:   {args.seed}")
    print(f"Output Format: {args.format}")
    print(f"Output Path:   {args.output}")
    print(f"Corrupt Rate:  {args.corrupt_rate}")
    print("--------------------------------------------------")
    
    t0 = time.time()
    dataset = generate_dataset(profile=args.profile, seed=args.seed, corrupt_rate=args.corrupt_rate)
    gen_time = time.time() - t0
    
    print(f"[OK] Generation completed in {gen_time:.2f} seconds.")
    
    # Validate clean relational integrity
    validator = IntegrityValidator()
    is_valid, errors = validator.validate_dataset(dataset)
    if is_valid:
        print("[OK] Post-Generation Relational Integrity Validation: PASSED!")
    else:
        print(f"[WARNING] Integrity Validation Found {len(errors)} issues (expected if corruption applied):")
        for err in errors[:5]:
            print(f"  - {err}")
            
    # Persist dataset using selected writer
    if args.format == "parquet":
        writer = ParquetWriter()
    else:
        writer = CSVWriter()
        
    summary = writer.write(dataset, args.output)
    
    print("\n--------------------------------------------------")
    print("Entity Record Counts & Disk Output Summary:")
    print("--------------------------------------------------")
    total_records = 0
    total_kb = 0.0
    for entity, meta in summary.items():
        print(f"  {entity:<25}: {meta['records']:>8,d} records | {meta['size_kb']:>8.1f} KB")
        total_records += meta["records"]
        total_kb += meta["size_kb"]
        
    print("--------------------------------------------------")
    print(f"TOTAL ENTITY RECORDS GENERATED: {total_records:,}")
    print(f"TOTAL PARQUET DISK FOOTPRINT:   {total_kb/1024:.2f} MB")
    print("==================================================")

if __name__ == "__main__":
    main()
