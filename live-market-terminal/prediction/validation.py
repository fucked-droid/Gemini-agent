"""
Walk-Forward Validation & Out-of-Sample Statistical Verification.
Computes Brier score, Expected Calibration Error (ECE), directional hit rate,
and transaction-cost-aware accuracy.
"""

import logging
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger("WalkForwardValidator")

class WalkForwardValidator:
    """
    Evaluates predictive models using strict walk-forward cross-validation.
    """

    MIN_SAMPLE_SIZE = 30
    FRICTION_COST_PCT = 0.0005  # 0.05% slippage + STT friction roundtrip

    @classmethod
    def evaluate_predictions(
        cls, y_true_returns: np.ndarray, y_pred_probs: np.ndarray, y_pred_directions: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluates predictions against realized forward returns.
        """
        n = len(y_true_returns)
        if n < cls.MIN_SAMPLE_SIZE:
            return {
                "status": "INSUFFICIENT_SAMPLE_SIZE",
                "sample_size": n,
                "min_required": cls.MIN_SAMPLE_SIZE,
                "brier_score": None,
                "hit_rate_pct": None,
                "ece": None,
                "cost_adjusted_pnl_bps": None,
                "is_validated": False,
                "message": f"Insufficient sample size (N={n} < {cls.MIN_SAMPLE_SIZE}). Model reliability not yet established.",
            }

        # True directional outcome (1 for UP, 0 for DOWN)
        # We filter out small chop below transaction friction
        actionable_mask = np.abs(y_true_returns) >= cls.FRICTION_COST_PCT
        y_true_binary = (y_true_returns > 0).astype(int)

        # Brier Score: Mean squared error between predicted probability and binary outcome
        brier = float(np.mean((y_pred_probs - y_true_binary) ** 2))

        # Directional Hit Rate on actionable moves
        correct = 0
        total_actionable = 0
        for i in range(n):
            if actionable_mask[i]:
                pred = y_pred_directions[i]
                actual = "UP" if y_true_returns[i] > 0 else "DOWN"
                if pred == actual:
                    correct += 1
                total_actionable += 1

        hit_rate = (correct / total_actionable * 100.0) if total_actionable > 0 else 50.0

        # Expected Calibration Error (ECE) across 5 probability bins
        bins = np.linspace(0.0, 1.0, 6)
        ece = 0.0
        for b in range(len(bins) - 1):
            bin_mask = (y_pred_probs >= bins[b]) & (y_pred_probs < bins[b + 1])
            if np.sum(bin_mask) > 0:
                bin_acc = np.mean(y_true_binary[bin_mask])
                bin_conf = np.mean(y_pred_probs[bin_mask])
                ece += (np.sum(bin_mask) / n) * abs(bin_acc - bin_conf)

        return {
            "status": "VALIDATED" if hit_rate >= 55.0 and brier <= 0.25 else "DEGRADED",
            "sample_size": n,
            "brier_score": round(brier, 4),
            "hit_rate_pct": round(hit_rate, 1),
            "ece": round(float(ece), 4),
            "actionable_trades": total_actionable,
            "is_validated": bool(hit_rate >= 55.0),
            "message": f"Walk-forward hit rate {hit_rate:.1f}% across {n} observations (Brier: {brier:.3f}).",
        }
