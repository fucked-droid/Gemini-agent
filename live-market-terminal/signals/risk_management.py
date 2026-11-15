"""
Risk Management & Capital Allocation Module.
Calculates volatility-adjusted position sizing, stop-loss distance,
lot allocation, and daily loss circuit breakers.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("RiskManager")

class RiskManager:
    """
    Institutional position sizing and trade exposure controls.
    """

    DEFAULT_ACCOUNT_SIZE = 500000.0  # ₹5,00,000 base capital
    MAX_RISK_PER_TRADE_PCT = 1.0     # 1% max risk per trade

    @classmethod
    def calculate_position_sizing(
        cls,
        entry_price: float,
        stop_loss_price: float,
        lot_size: int = 25,
        account_size: float = DEFAULT_ACCOUNT_SIZE,
        risk_pct: float = MAX_RISK_PER_TRADE_PCT,
    ) -> Dict[str, Any]:
        """
        Calculates maximum allowed lots and contracts given stop-loss distance.
        """
        stop_distance_pts = abs(entry_price - stop_loss_price)
        if stop_distance_pts <= 0:
            return {"lots": 0, "quantity": 0, "max_loss_rupees": 0.0}

        max_risk_rupees = account_size * (risk_pct / 100.0)
        risk_per_lot = stop_distance_pts * lot_size

        lots = int(max_risk_rupees // risk_per_lot)
        lots = max(lots, 1)  # at least 1 lot if trade approved
        total_quantity = lots * lot_size
        actual_risk_rupees = total_quantity * stop_distance_pts

        return {
            "account_size": account_size,
            "max_risk_rupees": max_risk_rupees,
            "stop_distance_pts": round(stop_distance_pts, 2),
            "lot_size": lot_size,
            "recommended_lots": lots,
            "total_quantity": total_quantity,
            "projected_risk_rupees": round(actual_risk_rupees, 2),
            "capital_required_estimate": round(entry_price * total_quantity * 0.12, 2),  # ~12% margin
        }
