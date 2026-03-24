Concepts Reference
==================

This page explains key forecasting concepts used in OpenSTEF, from interpreting output to understanding model behavior.

.. note::
   OpenSTEF is a Python library for building forecasting applications. These concepts apply to forecasts generated using OpenSTEF's models and workflows.

.. [DIAGRAM: Conceptual overview showing relationships between forecasts, quantiles, models, and features in OpenSTEF]

Interpreting Forecast Results
-----------------------------

OpenSTEF generates probabilistic forecasts that provide uncertainty estimates alongside point predictions. Understanding how to read and use these results is crucial for effective decision-making.

Forecast Output Structure
^^^^^^^^^^^^^^^^^^^^^^^^^

Every OpenSTEF forecast contains:

- **Timestamp**: When the forecast was made and for what time period
- **Point forecast**: The most likely predicted value (typically P50/median)
- **Quantile forecasts**: Multiple probability levels (e.g., P10, P25, P75, P90)
- **Forecast horizon**: How far into the future the prediction extends

The output format depends on your use case:

- **Congestion forecasts**: Load values with probability of exceeding capacity
- **Free space estimation**: Available capacity with confidence intervals
- **Grid loss forecasts**: Technical loss percentages with uncertainty bounds

Forecast Horizons and Resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF specializes in "short-term" forecasting:

- **Typical horizons**: 24-48 hours ahead
- **Resolution**: 15-minute intervals (configurable)
- **Update frequency**: Usually updated every 15 minutes with new observations

The forecast quality typically decreases with longer horizons due to increasing weather uncertainty and changing load patterns.

Quantiles and Confidence Intervals
-----------------------------------

OpenSTEF's probabilistic approach provides uncertainty quantification through quantiles rather than simple point estimates.

Understanding Quantiles
^^^^^^^^^^^^^^^^^^^^^^^^

A quantile represents the probability that the actual value will be below the forecast:

- **P10 (10th percentile)**: 10% chance actual value is below this level
- **P50 (50th percentile/median)**: Most likely value, 50% chance of being above or below
- **P90 (90th percentile)**: Only 10% chance actual value exceeds this level

For energy forecasting, this translates to operational insights:

- Use **P90** for conservative capacity planning (low risk of exceeding)
- Use **P50** for typical operational planning
- Use **P10** for optimistic scenarios or cost-sensitive decisions

Confidence Intervals in Practice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The spread between quantiles indicates forecast confidence:

- **Narrow spread** (P90 close to P10): High confidence forecast
- **Wide spread** (P90 much higher than P10): High uncertainty, perhaps due to weather variability or limited training data

Grid operators often use P90 for congestion management to maintain reliability with a 90% confidence level.

Model Choice and Use Cases
---------------------------

OpenSTEF supports multiple machine learning algorithms, with automatic selection based on data characteristics and use case requirements.

Model Types and Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**XGBoost (Extreme Gradient Boosting)**
- Best for: Medium to high aggregation levels with complex feature interactions
- Strengths: Handles non-linear patterns, robust to outliers, good feature importance
- Typical use: Substation-level load forecasting, congestion prediction

**LightGBM (Light Gradient Boosting Machine)**
- Best for: Large datasets requiring faster training
- Strengths: Memory efficient, handles categorical features well
- Typical use: High-frequency updates, district heating applications

**Linear Models**
- Best for: High aggregation levels with clear linear trends
- Strengths: Fast, interpretable, stable predictions
- Typical use: Regional transport forecasts, grid loss estimation at transmission level

Automatic Model Selection
^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's model selection considers:

- **Data volume**: More data enables complex models like XGBoost
- **Aggregation level**: Higher aggregation often benefits from simpler models
- **Feature types**: Categorical features favor LightGBM
- **Update frequency**: Faster updates may require lighter models

The system automatically backtests multiple models and selects based on historical performance metrics.

Important Predictors and Weather Dependency
--------------------------------------------

Energy forecasting relies heavily on weather data and temporal patterns. OpenSTEF automatically engineers features from these inputs.

Weather Features
^^^^^^^^^^^^^^^^

**Temperature**
- Most critical for heating/cooling loads
- Non-linear relationship captured through heating/cooling degree days
- Different lag effects for thermal vs electrical systems

**Solar Irradiance**
- Essential for solar generation and cooling loads
- Cloud forecasts impact uncertainty
- Seasonal angle adjustments built-in

**Wind Speed**
- Affects wind generation and heating loads
- Regional wind patterns matter for aggregated forecasts

Temporal Features
^^^^^^^^^^^^^^^^^

**Calendar Effects**
- Hour of day, day of week patterns
- Holiday detection and adjustment
- Seasonal trends and yearly cycles

**Lag Features**
- Recent load history (autoregressive terms)
- Weather persistence effects
- Weekly and seasonal lag patterns

The feature engineering process in OpenSTEF handles:

- Missing weather data interpolation
- Feature scaling and normalization
- Automatic lag selection based on use case
- Holiday calendar integration

Fallback Strategies
-------------------

Production forecasting systems must handle various failure modes. OpenSTEF includes several resilience mechanisms.

Model Failure Handling
^^^^^^^^^^^^^^^^^^^^^^^

When primary models fail:

1. **Recent model fallback**: Use last successfully trained model
2. **Simpler model fallback**: Fall back from XGBoost to Linear model
3. **Statistical fallback**: Use seasonal naive forecasts or moving averages

Missing Data Handling
^^^^^^^^^^^^^^^^^^^^^^

**Weather Data Issues**
- Use last available weather forecast
- Fall back to climatological averages
- Interpolate short gaps using nearby stations

**Load Data Issues**
- Use statistical imputation for training data gaps
- Require minimum data quality thresholds
- Flag forecasts with degraded input quality

Degraded Mode Operation
^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF can operate with reduced functionality:

- **No weather data**: Use load-only models with temporal features
- **Limited history**: Use transfer learning from similar assets
- **Real-time failures**: Serve cached forecasts with uncertainty inflation

The system provides quality indicators so users understand when forecasts are running in degraded modes.

.. note::
   For implementation details on any of these concepts, see the :doc:`../api/index` or explore the practical tutorials in :doc:`../user_guide/tutorials`.