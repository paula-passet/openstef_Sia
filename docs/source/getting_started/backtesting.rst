Backtesting Models
==================

Backtesting allows you to evaluate forecasting model performance using historical data. OpenSTEF provides a realistic backtesting framework that simulates operational conditions, preventing data leakage and respecting the constraints of real-time forecasting systems.

This tutorial shows you how to run backtests, compare different models, and evaluate performance using standard metrics.

What is Backtesting?
--------------------

Backtesting simulates how a forecasting model would have performed in production by:

- Generating predictions at regular intervals using only data available at that time
- Periodically retraining models as new data becomes available
- Preventing data leakage by strictly enforcing temporal boundaries
- Mimicking operational constraints like data availability delays

This approach provides a realistic assessment of model performance before deployment.

Setting Up a Backtest
---------------------

The backtesting process uses two main components: ``BacktestConfig`` to define parameters and ``BacktestPipeline`` to execute the simulation.

Basic Configuration
^^^^^^^^^^^^^^^^^^^

Start by configuring the backtesting parameters:

.. code-block:: python

    from datetime import timedelta
    from openstef.model.backtesting import BacktestConfig, BacktestPipeline
    from openstef.model.forecaster import Forecaster
    
    # Define backtesting parameters
    config = BacktestConfig(
        prediction_sample_interval=timedelta(hours=1),  # Generate predictions hourly
        training_sample_interval=timedelta(days=7),     # Retrain weekly
        training_horizon=timedelta(days=90),            # Use 90 days of training data
    )

The configuration controls:

- **prediction_sample_interval**: How often to generate forecasts
- **training_sample_interval**: How often to retrain the model
- **training_horizon**: How much historical data to use for training

Running a Backtest
^^^^^^^^^^^^^^^^^^

Execute the backtest by providing historical data and a forecaster:

.. code-block:: python

    from datetime import datetime
    from openstef.data.dataset import VersionedTimeSeriesDataset
    
    # Initialize your forecaster
    forecaster = Forecaster(
        predict_sample_interval=timedelta(hours=1),
        horizon=timedelta(hours=47),
    )
    
    # Create the backtest pipeline
    pipeline = BacktestPipeline(config=config, forecaster=forecaster)
    
    # Run the backtest
    predictions = pipeline.run(
        ground_truth=historical_targets,
        predictors=historical_features,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 12, 31),
        show_progress=True,
    )

The ``run`` method returns a ``VersionedTimeSeriesDataset`` containing all predictions with timestamps and availability information.

.. note::
   The prediction sample interval in ``BacktestConfig`` must match the forecaster's ``predict_sample_interval``, or a ``ValueError`` will be raised.

Evaluating Model Performance
-----------------------------

After generating predictions, evaluate performance using OpenSTEF's built-in metrics.

Computing Metrics
^^^^^^^^^^^^^^^^^

OpenSTEF provides several standard metrics for forecast evaluation:

.. code-block:: python

    from openstef.metrics.metrics import mae, rmae, mape
    import numpy as np
    
    # Extract actual and predicted values
    y_true = ground_truth_array
    y_pred = predictions_array
    
    # Calculate metrics
    mae_score = mae(y_true, y_pred)
    rmae_score = rmae(y_true, y_pred, lower_quantile=0.05, upper_quantile=0.95)
    mape_score = mape(y_true, y_pred)
    
    print(f"MAE: {mae_score:.2f}")
    print(f"rMAE: {rmae_score:.2%}")
    print(f"MAPE: {mape_score:.2%}")

Available metrics include:

- **MAE** (Mean Absolute Error): Average absolute difference between predictions and actuals
- **rMAE** (Relative MAE): MAE normalized by the data range (using percentiles)
- **MAPE** (Mean Absolute Percentage Error): Average percentage error
- **R²**: Coefficient of determination

Using Metric Providers
^^^^^^^^^^^^^^^^^^^^^^

For more structured metric computation, use metric providers:

.. code-block:: python

    from openstef.metrics.provider import (
        MAEProvider,
        RMAEProvider,
        MAPEProvider,
        R2Provider,
    )
    
    # Initialize providers
    providers = [
        MAEProvider(),
        RMAEProvider(),
        MAPEProvider(),
        R2Provider(),
    ]
    
    # Compute all metrics
    results = {}
    for provider in providers:
        metrics = provider.compute_deterministic(
            y_true=y_true,
            y_pred=y_pred,
            quantile=0.5,  # For deterministic forecasts
        )
        results.update(metrics)

Metric providers return dictionaries that can be easily aggregated and compared across models.

Comparing Multiple Models
-------------------------

Backtesting is particularly useful for comparing different modeling approaches.

Running Multiple Backtests
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compare models by running separate backtests with different configurations:

.. code-block:: python

    from openstef.model.regressors import XGBQuantileOpenstfRegressor, LinearQuantileOpenstfRegressor
    
    # Define models to compare
    models = {
        "XGBoost": XGBQuantileOpenstfRegressor(),
        "Linear": LinearQuantileOpenstfRegressor(),
    }
    
    # Run backtests for each model
    results = {}
    for name, regressor in models.items():
        forecaster = Forecaster(
            predict_sample_interval=timedelta(hours=1),
            horizon=timedelta(hours=47),
            model=regressor,
        )
        
        pipeline = BacktestPipeline(config=config, forecaster=forecaster)
        predictions = pipeline.run(
            ground_truth=historical_targets,
            predictors=historical_features,
            start=start_date,
            end=end_date,
        )
        
        results[name] = predictions

Aggregating Comparison Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After running multiple backtests, compute metrics for each model:

.. code-block:: python

    import pandas as pd
    
    # Compute metrics for all models
    comparison = []
    for model_name, predictions in results.items():
        mae_score = mae(y_true, predictions)
        rmae_score = rmae(y_true, predictions)
        
        comparison.append({
            "Model": model_name,
            "MAE": mae_score,
            "rMAE": rmae_score,
        })
    
    # Create comparison table
    comparison_df = pd.DataFrame(comparison)
    comparison_df = comparison_df.sort_values("MAE")
    print(comparison_df)

This produces a table showing which model performs best on each metric.

Understanding Backtest Results
------------------------------

Interpreting Metrics
^^^^^^^^^^^^^^^^^^^^

When evaluating backtest results:

- **MAE** provides absolute error in the same units as your target (e.g., MW for power forecasts)
- **rMAE** normalizes error by data range, making it easier to compare across different scales
- **MAPE** shows percentage error but can be misleading when actual values are near zero
- **R²** indicates how much variance is explained, with 1.0 being perfect and 0.0 being no better than mean prediction

For energy forecasting, rMAE is often preferred because it handles varying load levels well.

Peak Hour Performance
^^^^^^^^^^^^^^^^^^^^^

Energy systems often care most about peak hour accuracy. Use specialized metrics:

.. code-block:: python

    from openstef.metrics.provider import RMAEPeakHoursProvider
    
    # Evaluate performance during peak hours (8:00-20:00)
    peak_provider = RMAEPeakHoursProvider()
    peak_metrics = peak_provider.compute_deterministic(
        y_true=y_true,
        y_pred=y_pred,
        quantile=0.5,
    )

This focuses evaluation on the hours when forecast accuracy matters most for grid operations.

Temporal Consistency
^^^^^^^^^^^^^^^^^^^^

The ``BacktestPipeline`` ensures temporal consistency by:

- Only using data available at prediction time
- Respecting training horizons and retraining schedules
- Preventing lookahead bias in feature engineering

This means backtest performance should closely match production performance, assuming data quality remains consistent.

Next Steps
----------

Now that you understand backtesting, you can:

- Explore :doc:`advanced_customization` to customize model behavior and feature engineering
- Review the API documentation for detailed parameter descriptions
- Experiment with different training horizons and retraining frequencies to optimize performance

For questions about specific metrics or backtesting strategies, consult the metrics API reference.