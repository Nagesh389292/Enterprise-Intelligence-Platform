"""
Hashing Utilities for SHA-256 File Checkpoints and Record Deduplication.
"""

import hashlib
import os

def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file for identity and checkpoint tracking."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compute_record_hash(*key_values) -> str:
    """Computes SHA-256 hash over concatenated natural business keys."""
    raw_str = "|".join(str(v) if v is not None else "" for v in key_values)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
