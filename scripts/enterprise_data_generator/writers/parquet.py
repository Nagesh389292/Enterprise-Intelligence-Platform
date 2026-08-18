"""
Parquet File Persistence Writer for Raw Data Lake Storage.
"""

import os
import pandas as pd
from typing import Dict, List
from dataclasses import asdict
from .base import BaseWriter

class ParquetWriter(BaseWriter):
    def write(self, dataset: Dict[str, List], output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        summary = {}
        
        for entity_name, records in dataset.items():
            if not records:
                continue
                
            # Convert dataclass list to pandas DataFrame
            dict_list = [asdict(r) if hasattr(r, "__dataclass_fields__") else r.__dict__ for r in records]
            df = pd.DataFrame(dict_list)
            
            # Remove metadata tag if present before saving clean parquet
            if "_injected_defect" in df.columns:
                df = df.drop(columns=["_injected_defect"])
                
            file_path = os.path.join(output_dir, f"{entity_name}.parquet")
            df.to_parquet(file_path, engine="pyarrow", index=False)
            
            file_size_bytes = os.path.getsize(file_path)
            summary[entity_name] = {
                "records": len(df),
                "path": file_path,
                "size_kb": round(file_size_bytes / 1024, 2)
            }
            
        return summary
