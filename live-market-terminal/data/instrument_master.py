"""
Instrument & Security Master Manager for DhanHQ.
Downloads, caches, and parses Dhan's official api-scrip-master.csv.
Resolves Security IDs for indices (NIFTY 50, BANKNIFTY, INDIA VIX) and equities.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Any
import pandas as pd
import requests

from config import (
    DHAN_SCRIP_MASTER_URL,
    SCRIP_MASTER_CACHE_FILE,
    MONITORED_INSTRUMENTS,
    TOP_NIFTY_CONSTITUENTS,
)

logger = logging.getLogger("InstrumentMaster")

class InstrumentMaster:
    """
    Manages DhanHQ security master data.
    Provides verified resolution of security IDs and exchange segments.
    """

    def __init__(self, cache_file: Optional[Path] = None, max_cache_age_hours: int = 24):
        self.cache_file = cache_file or SCRIP_MASTER_CACHE_FILE
        self.max_cache_age_hours = max_cache_age_hours
        self.df: Optional[pd.DataFrame] = None
        self._canonical_indices = MONITORED_INSTRUMENTS.copy()

    def load_master(self, force_download: bool = False) -> bool:
        """
        Loads the scrip master into memory, downloading if missing or expired.
        Returns True if successful, False if using fallback mappings.
        """
        if not force_download and self._is_cache_valid():
            try:
                logger.info(f"Loading cached scrip master from {self.cache_file}")
                self.df = pd.read_csv(self.cache_file, low_memory=False)
                return True
            except Exception as e:
                logger.warning(f"Failed to read cached scrip master: {e}. Re-downloading...")

        return self.download_master()

    def download_master(self) -> bool:
        """
        Downloads latest api-scrip-master.csv from Dhan's CDN.
        """
        try:
            logger.info(f"Downloading Dhan scrip master from {DHAN_SCRIP_MASTER_URL}...")
            response = requests.get(DHAN_SCRIP_MASTER_URL, timeout=15)
            response.raise_for_status()

            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "wb") as f:
                f.write(response.content)

            self.df = pd.read_csv(self.cache_file, low_memory=False)
            logger.info(f"Scrip master successfully loaded with {len(self.df)} instruments.")
            return True
        except Exception as e:
            logger.warning(
                f"Could not download Dhan scrip master ({e}). "
                "Using verified canonical fallback instrument definitions."
            )
            return False

    def _is_cache_valid(self) -> bool:
        """Checks if the local scrip master cache exists and is fresh."""
        if not self.cache_file.exists():
            return False
        file_age_hours = (time.time() - os.path.getmtime(self.cache_file)) / 3600.0
        return file_age_hours < self.max_cache_age_hours

    def resolve_instrument(self, symbol_or_name: str) -> Dict[str, Any]:
        """
        Resolves instrument metadata (symbol, name, exchange, segment, security_id).
        Uses DataFrame lookup when available, falling back to canonical index dictionary.
        """
        key = symbol_or_name.upper().strip()

        # Check canonical monitored instruments first
        for sym, meta in self._canonical_indices.items():
            if key in (sym.upper(), meta["name"].upper(), meta["symbol"].upper()):
                return meta.copy()

        # Check constituents
        for stock in TOP_NIFTY_CONSTITUENTS:
            if key in (stock["symbol"].upper(), stock["name"].upper()):
                return {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "exchange": "NSE_EQ",
                    "segment": "E",
                    "security_id": stock["security_id"],
                    "lot_size": 1,
                    "tick_size": 0.05,
                }

        # Dynamic DataFrame lookup if master is loaded
        if self.df is not None and not self.df.empty:
            match = self._find_in_dataframe(key)
            if match:
                return match

        raise ValueError(
            f"Unable to resolve security ID for instrument '{symbol_or_name}'. "
            "Please check symbol name or refresh Dhan scrip master."
        )

    def _find_in_dataframe(self, key: str) -> Optional[Dict[str, Any]]:
        """Searches dataframe for symbol or description match."""
        # Common Dhan scrip master columns:
        # SEM_EXM_EXCH_ID / SEM_SMST_SECURITY_ID, SM_SYMBOL_NAME / SEM_TRADING_SYMBOL, SEM_SEGMENT
        sec_id_col = None
        for col in ["SEM_SMST_SECURITY_ID", "SEM_EXM_EXCH_ID", "SECURITY_ID", "SEM_SECURITY_ID"]:
            if col in self.df.columns:
                sec_id_col = col
                break

        sym_col = None
        for col in ["SM_SYMBOL_NAME", "SEM_TRADING_SYMBOL", "SYMBOL", "TRADING_SYMBOL"]:
            if col in self.df.columns:
                sym_col = col
                break

        if not sec_id_col or not sym_col:
            return None

        # Filter by symbol
        matched = self.df[self.df[sym_col].astype(str).str.upper() == key]
        if not matched.empty:
            row = matched.iloc[0]
            sec_id = str(row[sec_id_col])
            seg = str(row.get("SEM_SEGMENT", "E"))
            return {
                "symbol": key,
                "name": str(row.get("SEM_CUSTOM_SYMBOL", key)),
                "exchange": "NSE_EQ" if seg == "E" else "NSE_INDEX",
                "segment": seg,
                "security_id": sec_id,
                "lot_size": int(row.get("SEM_LOT_UNITS", 1)),
                "tick_size": float(row.get("SEM_TICK_SIZE", 0.05)),
            }

        return None
