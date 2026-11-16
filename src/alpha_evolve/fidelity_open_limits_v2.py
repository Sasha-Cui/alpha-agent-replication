"""Explicit opening-information eligibility sensitivity, not an exact venue model."""

import numpy as np
from alpha_evolve.openrouter_budget import atomic_json

PREVIOUS_CLOSE = "Ref($close, 1)"


def opening_flags(frame, threshold):
    if not 0 < float(threshold) < 1:
        raise ValueError("Expected declared fractional price-limit proxy")
    opening, previous = frame["$open"], frame[PREVIOUS_CLOSE]
    missing = ~np.isfinite(opening) | ~np.isfinite(previous) | (opening <= 0) | (previous <= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        gap = opening / previous - 1
    return (missing | gap.ge(threshold)), (missing | gap.le(-threshold))


def install_opening_limits(exchange_class, output):
    def update(self, limit_threshold):
        if (
            self.buy_price != "$open"
            or self.sell_price != "$open"
            or self._get_limit_type(limit_threshold) != self.LT_FLT
        ):
            raise ValueError("Opening-information sensitivity requires source open fills and a float limit")
        buy, sell = opening_flags(self.quote_df, limit_threshold)
        self.quote_df["limit_buy"] = buy
        self.quote_df["limit_sell"] = sell
        atomic_json(
            output / "opening_limit_audit.json",
            {
                "rows": len(self.quote_df),
                "limit_threshold": float(limit_threshold),
                "buy_blocked": int(buy.sum()),
                "sell_blocked": int(sell.sum()),
                "information_used_for_eligibility": ["current opening price", "previous close"],
                "scope": "Uniform source threshold used as an opening-gap proxy. Missing/nonpositive required quotes are blocked. No claim of exact board-specific limits, opening-auction liquidity, intraday execution, or point-in-time adjustment vintage.",
            },
        )

    exchange_class._update_limit = update
