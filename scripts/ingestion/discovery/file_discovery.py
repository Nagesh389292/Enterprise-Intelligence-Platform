"""
File Discovery Engine.
Scans source data landing directories and computes SHA-256 file checksums.
"""

import os
import glob
from typing import List, Dict
from ..utils.hashing import compute_file_sha256

class FileDiscoveryEngine:
    def discover_files(self, input_dir: str, file_format: str = "parquet") -> List[Dict]:
        pattern = os.path.join(input_dir, f"*.{file_format}")
        matched_files = glob.glob(pattern)
        
        discovered = []
        for filepath in matched_files:
            file_name = os.path.basename(filepath)
            entity_name = file_name.replace(f".{file_format}", "")
            sha256 = compute_file_sha256(filepath)
            size_bytes = os.path.getsize(filepath)
            
            discovered.append({
                "entity_name": entity_name,
                "file_name": file_name,
                "file_path": filepath,
                "file_checksum": sha256,
                "file_size_bytes": size_bytes,
                "file_format": file_format
            })
            
        return discovered
