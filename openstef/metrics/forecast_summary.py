# SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0
"""Utility to compute a summary of forecast quality metrics in one call."""
from typing import Dict

import pandas as pd

from openstef.metrics.metrics import bias, mae, nsme, rmse


def summarize_forecast(realised: pd.Series, forecast: pd.Series) -> Dict[str, float]:
    """Compute a summary of common forecast quality metrics.

    Args:
        realised: Realised (observed) load values.
        forecast: Forecasted load values.

    Returns:
        Dictionary with metric names as keys and their computed values.
    """
    metrics: Dict[str, float] = {
        "rmse": rmse(realised, forecast),
        "mae": mae(realised, forecast),
        "bias": bias(realised, forecast),
        "nsme": nsme(realised, forecast),
    }

    # MAPE: skip where realised is zero to avoid division by zero
    nonzero_mask = realised != 0
    if nonzero_mask.any():
        metrics["mape"] = (
            ((forecast[nonzero_mask] - realised[nonzero_mask]).abs() / realised[nonzero_mask].abs())
            .mean()
            * 100
        )
    else:
        metrics["mape"] = float("nan")

    return metrics
