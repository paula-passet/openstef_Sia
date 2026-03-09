# SPDX-FileCopyrightText: 2017-2023 Contributors to the OpenSTEF project <openstef@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0
"""Utility to compute forecast quality metrics broken down by time period."""
from typing import Dict

import pandas as pd

from openstef.metrics.metrics import mae, rmse


def breakdown_forecast(
    realised: pd.Series, forecast: pd.Series
) -> Dict[str, Dict[str, float]]:
    """Compute forecast quality metrics broken down by time period.

    Splits the data into day/night and weekday/weekend segments and computes
    RMSE and MAE for each segment.

    Args:
        realised: Realised (observed) load values with a DatetimeIndex.
        forecast: Forecasted load values with a DatetimeIndex.

    Returns:
        Nested dictionary with segment names as keys and metric dicts as values.
        Example::

            {
                "day": {"rmse": ..., "mae": ...},
                "night": {"rmse": ..., "mae": ...},
                "weekday": {"rmse": ..., "mae": ...},
                "weekend": {"rmse": ..., "mae": ...},
            }

    Raises:
        TypeError: If realised or forecast do not have a DatetimeIndex.
    """
    if not isinstance(realised.index, pd.DatetimeIndex):
        raise TypeError("realised must have a DatetimeIndex")
    if not isinstance(forecast.index, pd.DatetimeIndex):
        raise TypeError("forecast must have a DatetimeIndex")

    def _metrics(r: pd.Series, f: pd.Series) -> Dict[str, float]:
        if r.empty:
            return {"rmse": float("nan"), "mae": float("nan")}
        return {"rmse": rmse(r, f), "mae": mae(r, f)}

    hour = realised.index.hour
    weekday = realised.index.dayofweek  # 0=Monday … 6=Sunday

    day_mask = (hour >= 6) & (hour < 22)
    weekday_mask = weekday < 5

    return {
        "day": _metrics(realised[day_mask], forecast[day_mask]),
        "night": _metrics(realised[~day_mask], forecast[~day_mask]),
        "weekday": _metrics(realised[weekday_mask], forecast[weekday_mask]),
        "weekend": _metrics(realised[~weekday_mask], forecast[~weekday_mask]),
    }
