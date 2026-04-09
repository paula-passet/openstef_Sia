Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasting goes beyond single-point predictions to quantify uncertainty. Instead of predicting "demand will be 150 MW," OpenSTEF generates quantile forecasts that answer questions like "there's a 90% chance demand will be below 180 MW" or "there's only a 10% chance it will exceed 200 MW." This uncertainty information is critical for operational planning, risk management, and reserve allocation.

This page explains what quantiles are, how to interpret them, and why they matter for energy system operations.

What Are Quantiles?
-------------------

A quantile represents a threshold in a probability distribution. The 10th percentile (P10 or quantile 0.1) means there's a 10% probability the actual value will fall below this threshold. The 90th percentile (P90 or quantile 0.9) means there's a 90% probability the value will be below this threshold—or equivalently, a 10% probability it will exceed it.

OpenSTEF typically generates forecasts for multiple quantiles simultaneously:

- **P10 (0.1)**: Lower bound for conservative planning
- **P50 (0.5)**: Median forecast, often close to the mean
- **P90 (0.9)**: Upper bound for capacity planning

The region between P10 and P90 represents an 80% prediction interval—80% of actual outcomes should fall within this band if the model is well-calibrated.

.. note:: [DIAGRAM: Time series plot showing forecast quantile bands (P10, P50, P90) over 48 hours with actual load outcomes. P50 line in center, shaded bands between P10-P50 and P50-P90. Actual values scatter across bands, with most falling within P10-P90 range.]

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's important to distinguish between two types of uncertainty:

**Prediction intervals** quantify uncertainty about future individual observations. They account for both model uncertainty and the inherent randomness in the system. This is what OpenSTEF's quantile forecasts represent—the range where we expect actual load to fall.

**Confidence intervals** quantify uncertainty about model parameters or population statistics. For example, a confidence interval around a regression coefficient tells us how precisely we've estimated that parameter. This is less relevant for operational forecasting.

For energy forecasting, prediction intervals are what matter. Operators need to know the range of possible outcomes for tomorrow's demand, not the statistical precision of a model coefficient.

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles:

**Reserve allocation**: Grid operators must maintain sufficient reserves to handle unexpected demand spikes. They might use P90 forecasts to ensure reserves cover 90% of scenarios, accepting that 10% of the time they'll need emergency measures.

**Unit commitment**: Power plant scheduling often uses P50 (median) forecasts for base planning, then adjusts based on P10/P90 bounds to ensure flexibility.

**Trading and balancing**: Energy traders use quantile forecasts to assess risk. A narrow P10-P90 band indicates high confidence and lower risk, while a wide band suggests higher uncertainty and the need for more conservative positions.

**Renewable integration**: Solar and wind forecasts have higher uncertainty than load forecasts. Quantile forecasts help system operators understand the range of possible renewable generation and plan accordingly.

Generating Quantile Forecasts
------------------------------

OpenSTEF models generate quantile predictions through quantile regression. Instead of minimizing squared error (which targets the mean), quantile regression minimizes asymmetric loss functions that target specific percentiles.

Here's how to work with quantile forecasts:

.. code-block:: python

    from openstef_core.model.model_factory import ModelFactory
    from openstef_core.types import Quantile
    
    # Configure model with multiple quantiles
    model_config = {
        "model_type": "xgb_quantile",
        "quantiles": [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    }
    
    model = ModelFactory.create_model(model_config)
    model.fit(train_data)
    
    # Generate quantile predictions
    predictions = model.predict(test_features)
    # Returns array with shape (n_samples, n_quantiles)
    # predictions[:, 0] = P10 forecasts
    # predictions[:, 1] = P50 forecasts  
    # predictions[:, 2] = P90 forecasts

The model learns different decision boundaries for each quantile, producing forecasts that span the expected range of outcomes.

Visualizing Quantile Forecasts
-------------------------------

OpenSTEF provides built-in visualization tools for quantile forecasts through the ``ForecastTimeSeriesPlotter``:

.. code-block:: python

    from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter
    import pandas as pd
    
    # Prepare quantile forecast data
    quantile_data = pd.DataFrame({
        'quantile_P10': p10_forecasts,
        'quantile_P50': p50_forecasts,
        'quantile_P90': p90_forecasts
    }, index=forecast_times)
    
    # Create plotter and add model data
    plotter = ForecastTimeSeriesPlotter()
    plotter.add_model(
        model_name="XGBoost",
        quantiles=quantile_data,
        measurements=actual_load
    )
    
    # Generate interactive plot
    fig = plotter.plot(title="Load Forecast with Uncertainty Bands")
    fig.show()

The plotter automatically creates shaded bands between quantile pairs (P10-P50, P50-P90) and overlays actual measurements, making it easy to assess forecast quality visually.

Interpreting Forecast Calibration
----------------------------------

A well-calibrated quantile forecast has the property that X% of actual outcomes fall below the X-th percentile. For example, if your P10 forecasts are well-calibrated, exactly 10% of actual values should fall below the P10 predictions.

You can validate calibration using the ``QuantileProbabilityPlotter``:

.. code-block:: python

    from openstef_beam.analysis.plots import QuantileProbabilityPlotter
    from openstef_core.types import Quantile
    
    plotter = QuantileProbabilityPlotter()
    
    # Compare forecasted vs observed quantile frequencies
    forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
    observed = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]
    
    plotter.add_model("XGBoost", forecasted, observed)
    fig = plotter.plot(title="Forecast Calibration Analysis")

Points near the diagonal line indicate good calibration. Systematic deviations suggest the model is over-confident (points above diagonal) or under-confident (points below diagonal).

Poorly calibrated forecasts can be corrected using isotonic calibration, which learns a monotonic mapping from raw predictions to calibrated values. OpenSTEF includes calibration transforms that can be applied post-training to improve reliability.

Common Pitfalls
---------------

**Crossing quantiles**: Quantile predictions should be monotonic—P10 ≤ P50 ≤ P90 for every forecast. Some models can produce crossing quantiles due to independent training. OpenSTEF's quantile models enforce monotonicity constraints.

**Ignoring calibration**: A model can have good point forecast accuracy (low MAE on P50) but poor calibration (P90 intervals too narrow or too wide). Always validate calibration separately from accuracy.

**Confusing quantiles with standard deviations**: A 90% prediction interval is not the same as ±1.65 standard deviations. Quantile forecasts make no assumptions about the shape of the error distribution and can handle asymmetric uncertainty.

**Using wrong quantiles for decisions**: Match the quantile to the decision's risk tolerance. Conservative decisions (reserve allocation) need high quantiles (P90, P95), while balanced decisions (unit commitment) typically use P50.

Next Steps
----------

- See :doc:`forecasting_basics` for an introduction to short-term forecasting concepts
- Learn about :doc:`model_selection` to choose models that support quantile regression
- Explore :doc:`reliability_and_fallback` for handling forecast failures in production

For more on probabilistic metrics and evaluation, see the metrics documentation in the API reference.