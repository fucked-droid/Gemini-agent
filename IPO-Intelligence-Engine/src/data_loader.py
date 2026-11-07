import json
import os
from typing import List, Dict, Any, Optional
from src.models.ipo_schema import IPOProfile


def load_ipo_from_json(file_path: str) -> IPOProfile:
    """Loads and parses an IPO profile from a JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IPO JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return IPOProfile.from_dict(data)


def load_all_sample_ipos(data_dir: str) -> List[IPOProfile]:
    """Loads all JSON IPO files from a given directory."""
    if not os.path.exists(data_dir):
        return []

    profiles = []
    for fname in sorted(os.listdir(data_dir)):
        if fname.endswith(".json"):
            try:
                p = load_ipo_from_json(os.path.join(data_dir, fname))
                profiles.append(p)
            except Exception as e:
                print(f"[DataLoader] Warning: Failed to load {fname}: {e}")
    return profiles
