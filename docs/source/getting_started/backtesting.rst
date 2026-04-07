Backtesting and Model Comparison
================================

Backtesting is the process of evaluating a forecasting model against historical data to understand how it would have performed in a real operational setting. OpenSTEF's backtesting framework simulates the production environment — generating forecasts at regular intervals, retraining models periodically, and preventing data leakage — so that evaluation results reflect realistic performance.

This page walks through setting up a backtest, evaluating results with metrics, and comparing multiple models side by side. If you haven't built your first forecast yet, start with :doc:`first_forecast` before diving into backtesting.

.. note::

   Backtesting in OpenSTEF lives in the ``openstef_beam.backtesting`` module, while evaluation metrics are in ``openstef_beam.evaluation`` and ``openstef_beam.metrics``.


Why Backtest?
-------------

Training a model and checking its in-sample fit tells you very little about real-world performance. Backtesting answers the questions that matter:

- **How accurate are forecasts at different lead times?** A 1-hour-ahead forecast is typically much better than a 48-hour-ahead forecast. Backtesting quantifies this degradation.
- **How does the model handle regime changes?** Seasonal shifts, unusual weather, and load pattern changes all stress-test a model differently.
- **Which model is best for your use case?** Comparing two models on the same historical period gives an apples-to-apples comparison.

OpenSTEF's ``BacktestPipeline`` ensures temporal consistency throughout this process. At each simulated prediction point, the model only sees data that would have been available at that moment — no future information leaks into training or prediction.


Setting Up a Backtest
---------------------

A backtest requires three ingredients: a ``BacktestConfig`` that defines the simulation schedule, a forecaster that implements the ``BacktestForecasterMixin`` interface, and historical data in ``VersionedTimeSeriesDataset`` format.

Configuring the Backtest
^^^^^^^^^^^^^^^^^^^^^^^^

The ``BacktestConfig`` controls how the simulation unfolds over time:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=1),
       train_interval=timedelta(days=7),
       align_time=time(0, 0),
   )

The key parameters are:

- ``prediction_sample_interval`` — The resolution of forecast output (e.g., 15-minute intervals). Must match the forecaster's ``predict_sample_interval``.
- ``predict_interval`` — How often the model generates a new forecast (e.g., every hour).
- ``train_interval`` — How often the model is retrained (e.g., every 7 days).
- ``align_time`` — The time of day to align prediction and training schedules to.

.. note::

   The ``prediction_sample_interval`` in the config must exactly match the forecaster's ``predict_sample_interval``. A ``ValueError`` is raised if they differ.


Preparing Historical Data
^^^^^^^^^^^^^^^^^^^^^^^^^

Backtesting uses ``VersionedTimeSeriesDataset`` to represent data that tracks *when* each observation became available. This is critical for realistic evaluation — in production, weather forecasts are revised, meter data arrives with delays, and not all features are available at the same time.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
   import pandas as pd

   # Load your historical ground truth and predictor features
   # Each TimeSeriesDataset includes an 'available_at' timestamp
   ground_truth = VersionedTimeSeriesDataset(data_parts=[
       TimeSeriesDataset(ground_truth_df_part1),
       TimeSeriesDataset(ground_truth_df_part2),
   ])

   predictors = VersionedTimeSeriesDataset(data_parts=[
       TimeSeriesDataset(predictor_df_part1),
       TimeSeriesDataset(predictor_df_part2),
   ])

The ``VersionedTimeSeriesDataset`` uses lazy composition internally, which avoids the O(n²) memory cost of concatenating many DataFrames with misaligned timestamp/availability pairs.


Running the Backtest
^^^^^^^^^^^^^^^^^^^^

With config, forecaster, and data ready, create and run the pipeline:

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestPipeline

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 6, 30),
       show_progress=True,
   )

The ``run`` method returns a ``VersionedTimeSeriesDataset`` containing all predictions with their timestamps and availability information. Setting ``start`` or ``end`` to ``None`` uses the data's minimum or maximum datetime respectively.


Evaluating Forecast Performance
-------------------------------

Once you have predictions, the ``EvaluationPipeline`` computes metrics across multiple dimensions: lead times, time windows, and data subsets.

Available Metrics
^^^^^^^^^^^^^^^^^

OpenSTEF provides a range of metric providers in ``openstef_beam.metrics``:

- ``MAEProvider`` — Mean Absolute Error
- ``RMSEProvider`` — Root Mean Squared Error
- ``MAPEProvider`` — Mean Absolute Percentage Error
- ``R2Provider`` — R² coefficient of determination
- ``RMAEProvider`` — Relative Mean Absolute Error
- ``RMAEPeakHoursProvider`` — RMAE for peak hours only (8:00–20:00)
- ``ObservedProbabilityProvider`` — Calibration metric for probabilistic forecasts
- ``MeanAbsoluteCalibrationErrorProvider`` — Measures reliability of prediction intervals

Running the Evaluation
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import MAEProvider, RMSEProvider, RMAEProvider

   eval_config = EvaluationConfig(
       available_ats=[],
       lead_times=[
           timedelta(hours=1),
           timedelta(hours=6),
           timedelta(hours=24),
           timedelta(hours=48),
       ],
   )

   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
       window_metric_providers=[MAEProvider()],
       global_metric_providers=[MAEProvider(), RMSEProvider(), RMAEProvider()],
   )

   report = eval_pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth,
       target_column="load",
   )

.. warning::

   The ``quantiles`` list **must** include ``0.5`` (the median). The pipeline raises a ``ValueError`` otherwise, since median evaluation is always required.

The ``EvaluationReport`` returned by ``run`` contains structured results organized by data subset. You can access global metrics and windowed metrics separately:

.. code-block:: python

   # Access global metrics across the entire evaluation period
   for subset_report in report.subset_reports:
       global_metric = subset_report.get_global_metric()
       if global_metric:
           print(f"Subset: {subset_report.filtering}")
           print(f"  Metrics: {global_metric.metrics}")


Comparing Multiple Models
-------------------------

The real power of backtesting emerges when you compare models. The workflow is straightforward: run the same backtest with different forecasters, then evaluate each set of predictions with identical settings.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline

   # Define models to compare
   models = {
       "xgboost": xgboost_forecaster,
       "linear": linear_forecaster,
       "custom": custom_forecaster,
   }

   # Run backtests with identical config and data
   results = {}
   for name, forecaster in models.items():
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       results[name] = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=datetime(2024, 1, 1),
           end=datetime(2024, 6, 30),
       )

   # Evaluate each model with the same metrics
   comparison = {}
   for name, preds in results.items():
       report = eval_pipeline.run(
           predictions=preds,
           ground_truth=ground_truth,
           target_column="load",
       )
       comparison[name] = report

Building a Comparison Table
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract metrics from each report to build a side-by-side comparison:

.. code-block:: python

   import pandas as pd

   rows = []
   for model_name, report in comparison.items():
       for subset_report in report.subset_reports:
           global_metric = subset_report.get_global_metric()
           if global_metric:
               row = {"model": model_name, "lead_time": str(subset_report.filtering)}
               row.update(global_metric.metrics)
               rows.append(row)

   comparison_df = pd.DataFrame(rows)
   print(comparison_df.pivot(index="lead_time", columns="model"))

This produces a table showing how each model performs at each lead time — making it easy to identify which model is best for short-term versus day-ahead forecasting.

.. note:: [DIAGRAM: Bar chart comparing MAE across models at different lead times (1h, 6h, 24h, 48h)]


Best Practices
--------------

**Use a sufficiently long evaluation period.** Short backtests can be misleading. Aim for at least several months to capture seasonal patterns and varying conditions.

**Match the backtest schedule to production.** Set ``predict_interval`` and ``train_interval`` to match your actual operational cadence. A model that retrains daily in backtesting but weekly in production will show optimistic results.

**Evaluate at multiple lead times.** A model might excel at short-term forecasting but degrade rapidly at longer horizons. Always check performance across the full range of lead times you care about.

**Watch for data leakage.** OpenSTEF's ``BacktestPipeline`` prevents leakage by design, but ensure your input data's ``available_at`` timestamps are correct. If availability timestamps are wrong, the temporal guarantees break down.

**Compare fairly.** When comparing models, use identical data, time periods, and evaluation metrics. The workflow shown above ensures this by sharing the same ``config``, ``ground_truth``, ``predictors``, and ``eval_pipeline`` across all models.


Next Steps
----------

- For customizing forecasters and feature engineering, see :doc:`advanced_customization`
- To understand the data structures used in backtesting, explore the :doc:`/api/index` for ``openstef_core.datasets`` and ``openstef_beam.backtesting``