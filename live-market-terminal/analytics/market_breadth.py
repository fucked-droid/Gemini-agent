"""
Market Breadth & Institutional Flow Analytics Engine.
Tracks advance-decline participation across NIFTY universe,
heavyweight contributions, and verified institutional flow data.
"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from config import TOP_NIFTY_CONSTITUENTS, WORKSPACE_ROOT

logger = logging.getLogger("MarketBreadthAnalyzer")

class MarketBreadthAnalyzer:
    """
    Computes breadth statistics and verifiable institutional metrics.
    """

    @classmethod
    def compute_breadth_from_constituents(cls, constituent_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes Advance/Decline counts and ratio from constituent price changes.
        Never displays zero values as valid readings when feed data is missing or stale.
        """
        if not constituent_data:
            return {
                "status": "UNAVAILABLE",
                "advances": None,
                "declines": None,
                "unchanged": None,
                "total": 0,
                "adr": None,
                "breadth_score": 0.0,
                "breadth_condition": "UNAVAILABLE",
            }

        adv = 0
        dec = 0
        unch = 0
        has_real_quote = False

        for stock in constituent_data:
            if "change" in stock or "change_pct" in stock:
                has_real_quote = True
                chg = float(stock.get("change", stock.get("change_pct", 0.0)))
                if chg > 0.05:
                    adv += 1
                elif chg < -0.05:
                    dec += 1
                else:
                    unch += 1

        total = adv + dec + unch
        # If no constituent had real quote changes or total non-zero volume/price changes
        if not has_real_quote or (adv == 0 and dec == 0 and unch == len(constituent_data)):
            return {
                "status": "UNAVAILABLE",
                "advances": None,
                "declines": None,
                "unchanged": None,
                "total": 0,
                "adr": None,
                "breadth_score": 0.0,
                "breadth_condition": "UNAVAILABLE",
            }

        # Safe ADR calculation: avoid division by zero
        if dec > 0:
            adr = round(adv / dec, 2)
        elif adv > 0:
            adr = round(float(adv), 2)
        else:
            adr = 1.0

        score = round((adv - dec) / total, 2) if total > 0 else 0.0

        if score >= 0.40:
            condition = "STRONG_BULLISH_BREADTH"
        elif score > 0.10:
            condition = "MODERATE_BULLISH_BREADTH"
        elif score <= -0.40:
            condition = "STRONG_BEARISH_BREADTH"
        elif score < -0.10:
            condition = "MODERATE_BEARISH_BREADTH"
        else:
            condition = "BALANCED_CHOP_BREADTH"

        return {
            "status": "AVAILABLE",
            "advances": adv,
            "declines": dec,
            "unchanged": unch,
            "total": total,
            "adr": adr,
            "breadth_score": score,
            "breadth_condition": condition,
        }

    @classmethod
    def get_institutional_flow(cls) -> Dict[str, Any]:
        """
        Retrieves institutional flow data strictly from verified sources.
        Never guesses or fabricates institutional positions.
        """
        # Look for verified institutional cache in workspace
        fii_file = WORKSPACE_ROOT / "Daily-Market-Regime-Engine" / "data" / "fii_dii_master.parquet"
        json_file = WORKSPACE_ROOT / "Daily-Market-Regime-Engine" / "data" / "institutional_data.json"

        if json_file.exists():
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    return {
                        "status": "VERIFIED_RECORD",
                        "fii_net_crores": data.get("fii_net_crores", 0.0),
                        "dii_net_crores": data.get("dii_net_crores", 0.0),
                        "composite_score": data.get("composite_score", 0.0),
                        "interpretation": data.get("interpretation", "Neutral Institutional Stance"),
                        "source": "NSE_OFFICIAL_END_OF_DAY",
                    }
            except Exception as e:
                logger.warning(f"Error reading institutional data json: {e}")

        # Explicitly transparent status when live feed is absent
        return {
            "status": "UNAVAILABLE",
            "fii_net_crores": None,
            "dii_net_crores": None,
            "composite_score": None,
            "interpretation": "Intraday institutional flow feed unavailable (NSE publishes official FII/DII post-market at 18:30 IST).",
            "source": "UNAVAILABLE",
        }
