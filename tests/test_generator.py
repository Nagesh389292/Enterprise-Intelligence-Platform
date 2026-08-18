# ==============================================================================
# Enterprise Intelligence Platform — Data Generator Unit Test Suite
# Tests seed reproducibility, entity record counts, foreign key integrity,
# probabilistic scenarios, corruption rules, and Parquet persistence.
# ==============================================================================

import os
import tempfile
import pytest
from scripts.enterprise_data_generator.cli import generate_dataset
from scripts.enterprise_data_generator.validation import IntegrityValidator
from scripts.enterprise_data_generator.writers import ParquetWriter, CSVWriter

def test_deterministic_seed_reproducibility():
    """Verifies that identical random seeds produce identical dataset records."""
    ds1 = generate_dataset(profile="development", seed=42)
    ds2 = generate_dataset(profile="development", seed=42)
    
    assert len(ds1["customers"]) == len(ds2["customers"])
    assert len(ds1["orders"]) == len(ds2["orders"])
    assert ds1["customers"][0].customer_id == ds2["customers"][0].customer_id
    assert ds1["orders"][0].order_number == ds2["orders"][0].order_number

def test_entity_record_counts():
    """Verifies that development profile generates correct target record counts."""
    ds = generate_dataset(profile="development", seed=42)
    
    assert len(ds["customers"]) == 1000
    assert len(ds["products"]) == 100
    assert len(ds["suppliers"]) == 20
    assert len(ds["warehouses"]) == 4
    assert len(ds["orders"]) == 10000
    assert len(ds["machines"]) == 50
    assert len(ds["machine_telemetry"]) == 100000

def test_foreign_key_integrity():
    """Verifies post-generation relational integrity validator passes on clean datasets."""
    ds = generate_dataset(profile="development", seed=42)
    validator = IntegrityValidator()
    is_valid, errors = validator.validate_dataset(ds)
    
    assert is_valid is True, f"Integrity errors found: {errors}"
    assert len(errors) == 0

def test_parquet_writer_persistence():
    """Verifies ParquetWriter correctly exports dataframes to disk."""
    ds = generate_dataset(profile="development", seed=42)
    writer = ParquetWriter()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        summary = writer.write(ds, tmp_dir)
        
        assert "customers" in summary
        assert "orders" in summary
        assert os.path.exists(summary["customers"]["path"])
        assert os.path.exists(summary["orders"]["path"])
        assert summary["customers"]["records"] == 1000

def test_data_quality_corruption():
    """Verifies corruption layer injects expected defect records."""
    ds = generate_dataset(profile="development", seed=42, corrupt_rate=0.05)
    
    # Check that duplicates were added to orders
    assert len(ds["orders"]) > 10000
