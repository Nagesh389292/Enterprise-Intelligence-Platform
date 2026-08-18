"""
Bronze Layer Immutable Raw Archiver.
Copies raw landing source files into immutable partition structure data/bronze/YYYY/MM/DD/.
"""

import os
import shutil
from datetime import datetime

class BronzeWriter:
    def archive_raw_file(self, source_filepath: str, batch_id: str, base_bronze_dir: str = "data/bronze") -> str:
        now = datetime.utcnow()
        year_str = now.strftime("%Y")
        month_str = now.strftime("%m")
        day_str = now.strftime("%d")
        
        target_dir = os.path.join(base_bronze_dir, year_str, month_str, day_str)
        os.makedirs(target_dir, exist_ok=True)
        
        file_name = os.path.basename(source_filepath)
        target_filepath = os.path.join(target_dir, f"{batch_id}_{file_name}")
        
        shutil.copy2(source_filepath, target_filepath)
        return target_filepath
