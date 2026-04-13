Backtesting Models with Historical Data
========================================

Backtesting lets you measure how well a forecasting model *would have* performed on real historical data — without ever touching future observations. Rather than evaluating a single snapshot, OpenSTEF's ``BacktestPipeline`` replays the operational environment: it generates forecasts at regular intervals, retrains the model on schedule, and respects the data availability constraints that would have existed at each point in time. The result is an honest, leakage-free estimate of model quality.

This tutorial walks through the full backtesting workflow: configuring the pipeline, running it against historical data, computing evaluation metrics, and comparing multiple models side-by-side. If you haven't yet built your first forecast, start with :doc:`first_forecast` before continuing here.

.. note:: [DIAGRAM: Timeline showing the backtesting loop — training window slides forward, model retrained at each interval, predictions collected and compared against ground truth]

How OpenSTEF Backtesting Works
-------------------------------

The ``BacktestPipeline`` simulates production conditions by enforcing two key constraints:

- **No data leakage.** At each prediction step, only data that would have been *available* at that moment is used. The ``VersionedTimeSeriesDataset`` tracks data availability timestamps so the pipeline can reconstruct the exact information state at any historical point.
- **Periodic retraining.** The model is retrained on a configurable schedule, mirroring how a live system would refresh its parameters as new observations accumulate.

This design means backtest results are directly comparable to live performance — there are no optimistic biases from accidentally using future data during training.

Setting Up the Pipeline
------------------------

Start by importing the core backtesting classes and preparing your datasets:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
    from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
    import pandas as pd

    # Load your historical target values (e.g., measured power output)
    ground_truth = VersionedTimeSeriesDataset.from_dataframe(
        df=pd.read_parquet("measurements.parquet"),
        available_at_column="available_at",
    )

    # Load predictor features (weather forecasts, calendar features, etc.)
    predictors = VersionedTimeSeriesDataset.from_dataframe(
        df=pd.read_parquet("predictors.parquet"),
        available_at_column="available_at",
    )

Next, configure the backtest. The two most important parameters are the **prediction sample interval** — how often the model generates a new forecast — and the **training interval** — how often the model is retrained:

.. code-block:: python

    config = BacktestConfig(
        prediction_sample_interval=timedelta(hours=1),
        training_interval=timedelta(days=7),
    )

.. warning::

   The ``prediction_sample_interval`` in ``BacktestConfig`` must exactly match the ``predict_sample_interval`` set on your forecaster. A ``ValueError`` is raised at construction time if these differ, so check both values before running a long backtest.

Running the Backtest
---------------------

Instantiate the pipeline with your config and forecaster, then call ``run()``:

.. code-block:: python

    from my_project.forecasters import MyXGBoostForecaster

    forecaster = MyXGBoostForecaster(
        predict_sample_interval=timedelta(hours=1),
    )

    pipeline = BacktestPipeline(config=config, forecaster=forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,
    )

The ``run()`` method returns a ``VersionedTimeSeriesDataset`` containing every prediction generated during the backtest, tagged with the ``available_at`` timestamp at which each forecast was produced. Passing ``show_progress=True`` prints a progress bar — useful for long date ranges.

If you omit ``start`` or ``end``, the pipeline uses the minimum and maximum timestamps present in the ``ground_truth`` dataset.

Computing Evaluation Metrics
------------------------------

With predictions in hand, use OpenSTEF's evaluation utilities to compute metrics. The ``SubsetMetric`` container organises results by quantile and metric name, making it straightforward to extract the numbers you care about:

.. code-block:: python

    from openstef_beam.evaluation import Evaluator, EvaluatorConfig

    eval_config = EvaluatorConfig(
        quantiles=[10.0, 50.0, 90.0],
        metrics=["MAE", "RMSE", "MAPE"],
    )

    evaluator = Evaluator(config=eval_config)

    report = evaluator.evaluate(
        predictions=predictions,
        ground_truth=ground_truth,
        target_column="load_mw",
    )

    # Access the median (p50) MAE directly
    mae_p50 = report.metrics.get_metric(quantile=50.0, metric_name="MAE")
    print(f"Median forecast MAE: {mae_p50:.3f} MW")

    # Iterate over all quantile–metric combinations
    for quantile, metrics_dict in report.metrics.items():
        for metric_name, value in metrics_dict.items():
            print(f"  Q{quantile:>5} | {metric_name}: {value:.4f}")

Visualising Backtest Results
-----------------------------

OpenSTEF ships with built-in visualisation tools so you don't need to reach for matplotlib. The ``ForecastTimeSeriesPlotter`` produces interactive Plotly figures showing measurements, forecast lines, and uncertainty bands together:

.. code-block:: python

    from openstef_core.visualization import ForecastTimeSeriesPlotter

    # Select the point-in-time view of predictions (latest available version)
    pred_series = predictions.select_version()

    plotter = ForecastTimeSeriesPlotter()
    plotter.add_measurements(ground_truth.select_version()["load_mw"])
    plotter.add_model("XGBoost", forecast=pred_series["load_mw_p50"])

    fig = plotter.plot(title="Backtest: XGBoost vs Actuals (H1 2024)")
    fig.show()

For tracking how accuracy evolves over time, use ``WindowedMetricVisualization``. This plots a sliding-window metric (e.g., weekly MAE) as a time series, making it easy to spot performance degradation or seasonal effects:

.. code-block:: python

    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import WindowedMetricVisualization
    from datetime import timedelta

    analysis_config = AnalysisConfig(
        visualization_providers=[
            WindowedMetricVisualization(
                name="mae_over_time",
                metric="MAE",
                window=timedelta(days=7),
            ),
        ]
    )

Comparing Multiple Models
--------------------------

The real power of backtesting comes from running the same historical period through several model configurations and comparing the results objectively. The workflow is straightforward: run the pipeline once per model, collect the metric reports, and compare:

.. code-block:: python

    from my_project.forecasters import MyXGBoostForecaster, MyLightGBMForecaster

    model_configs = {
        "XGBoost": MyXGBoostForecaster(predict_sample_interval=timedelta(hours=1)),
        "LightGBM": MyLightGBMForecaster(predict_sample_interval=timedelta(hours=1)),
    }

    results = {}
    for name, forecaster in model_configs.items():
        pipeline = BacktestPipeline(config=config, forecaster=forecaster)
        preds = pipeline.run(
            ground_truth=ground_truth,
            predictors=predictors,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 6, 30),
        )
        report = evaluator.evaluate(
            predictions=preds,
            ground_truth=ground_truth,
            target_column="load_mw",
        )
        results[name] = report.metrics

    # Print a comparison table
    print(f"{'Model':<12} {'MAE':>8} {'RMSE':>8}")
    print("-" * 30)
    for name, metrics in results.items():
        mae = metrics.get_metric(quantile=50.0, metric_name="MAE")
        rmse = metrics.get_metric(quantile=50.0, metric_name="RMSE")
        print(f"{name:<12} {mae:>8.3f} {rmse:>8.3f}")

To visualise both models together, add each one to the same plotter instance:

.. code-block:: python

    plotter = ForecastTimeSeriesPlotter()
    plotter.add_measurements(ground_truth.select_version()["load_mw"])

    for name, forecaster in model_configs.items():
        # Re-run or cache predictions as needed
        plotter.add_model(name, forecast=cached_predictions[name]["load_mw_p50"])

    fig = plotter.plot(title="Model Comparison: H1 2024 Backtest")
    fig.show()

The plotter colour-codes each model automatically and supports interactive hover, zoom, and pan — no additional configuration required.

Automated Model Selection
--------------------------

If you want the pipeline itself to decide which model is better, OpenSTEF's internal ``_check_is_new_model_better`` logic compares ``SubsetMetric`` objects using a configurable ``model_selection_metric``. You specify a ``(quantile, metric_name, direction)`` triple — for example ``(50.0, "MAE", "minimize")`` — and the pipeline returns ``True`` when the new model improves on the old one:

.. code-block:: python

    # model_selection_metric is typically set on the forecaster or evaluator config
    eval_config = EvaluatorConfig(
        quantiles=[50.0],
        metrics=["MAE"],
        model_selection_metric=(50.0, "MAE", "minimize"),
    )

This is particularly useful in automated retraining pipelines where you want to promote a newly trained model only when it demonstrably outperforms the incumbent.

Tips for Reliable Backtests
-----------------------------

- **Use a warm-up period.** The first few training windows may produce poor forecasts simply because the model hasn't seen enough data yet. Exclude the first ``training_interval`` worth of predictions from your metric calculations.
- **Match intervals to production.** Set ``prediction_sample_interval`` and ``training_interval`` to the values your live system uses. Mismatched intervals produce metrics that don't reflect real-world performance.
- **Check data availability timestamps.** If your ``VersionedTimeSeriesDataset`` has incorrect ``available_at`` values, the pipeline may inadvertently use future data. Validate these timestamps before running a long backtest.
- **Evaluate across multiple quantiles.** A model with a low median MAE may still have poorly calibrated uncertainty bands. Always inspect the p10 and p90 metrics alongside the median.

Next Steps
-----------

- To customise the forecaster itself — feature engineering, hyperparameter tuning, or swapping the underlying algorithm — see :doc:`advanced_customization`.
- For a quick end-to-end example without the backtest machinery, revisit :doc:`quickstart`.
- To understand how OpenSTEF structures its datasets and pipelines more broadly, the :doc:`index` page links to the full getting-started series.