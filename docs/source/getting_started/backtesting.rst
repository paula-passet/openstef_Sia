Backtesting
===========

Backtesting lets you evaluate how well a forecasting model would have performed on
historical data — without ever touching future observations. Rather than training once
and hoping for the best, you replay the operational environment: the model is retrained
periodically, forecasts are generated at realistic intervals, and predictions are
compared against the ground truth that was withheld at the time.

This page walks through the full backtesting workflow in OpenSTEF: configuring and
running a backtest, computing evaluation metrics, and visualising results to compare
models. If you haven't set up a basic forecast yet, start with :doc:`first_forecast`
first.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

How OpenSTEF Backtesting Works
-------------------------------

OpenSTEF's ``BacktestPipeline`` simulates the real-time operational environment as
faithfully as possible. At each step in the historical period it:

1. Trains (or retrains) the model using only data available up to that point.
2. Generates forecasts for the upcoming horizon.
3. Advances the clock by one prediction interval and repeats.

This design prevents data leakage — the model never sees future observations during
training — and produces a realistic picture of how the model would behave in
production. Retraining frequency is controlled independently from prediction frequency,
so you can model weekly retraining with hourly predictions, for example.

The two key configuration objects are ``BacktestConfig`` (controls the simulation
schedule) and a forecaster that implements ``BacktestForecasterMixin``. Both must agree
on ``prediction_sample_interval``; OpenSTEF raises a ``ValueError`` at construction
time if they don't match, catching misconfiguration early.

Setting Up a Backtest
----------------------

Start by importing the pipeline and its configuration, then build your forecaster as
you normally would:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef.backtesting import BacktestConfig, BacktestPipeline

    # Define the simulation schedule
    config = BacktestConfig(
        prediction_sample_interval=timedelta(hours=1),   # forecast every hour
        training_interval=timedelta(days=7),             # retrain weekly
        prediction_horizon=timedelta(hours=48),          # 48-hour-ahead forecasts
    )

    # Build your forecaster (must implement BacktestForecasterMixin)
    from openstef.forecasting import MyForecaster  # your configured forecaster
    forecaster = MyForecaster(...)

    pipeline = BacktestPipeline(config=config, forecaster=forecaster)

.. note::

   ``prediction_sample_interval`` in ``BacktestConfig`` must equal
   ``forecaster.config.predict_sample_interval``. Mismatches raise a ``ValueError``
   immediately so you catch the problem before running the full simulation.

Running the Simulation
-----------------------

Pass your historical data to ``pipeline.run()``. The method accepts a
``VersionedTimeSeriesDataset`` for the ground truth targets and another for the
predictor features. You can optionally narrow the period with ``start`` and ``end``
arguments; if omitted, the pipeline uses the full extent of the data.

.. code-block:: python

    # ground_truth and predictors are VersionedTimeSeriesDataset objects
    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,   # display a progress bar
    )

The return value is a ``VersionedTimeSeriesDataset`` containing every forecast that
would have been issued during the period, tagged with the timestamp at which it was
available. This versioned structure is what makes it possible to compute metrics at
different forecast horizons (e.g., 1-hour-ahead vs 24-hour-ahead accuracy) from a
single run.

Evaluating Performance
-----------------------

OpenSTEF ships with built-in evaluation utilities so you don't need to reach for
external libraries. Metrics are computed over *subsets* of the prediction dataset,
letting you slice performance by horizon, time-of-day, season, or any other dimension
that matters for your use case.

The library supports both deterministic metrics and probabilistic metrics out of the
box:

- **MAE** — Mean Absolute Error; intuitive unit-level accuracy.
- **RMSE** — Root Mean Squared Error; penalises large errors more heavily.
- **rMAE** — Relative MAE, normalised by the target's mean; useful for comparing
  across substations or assets with different scales.
- **rCRPS** — Relative Continuous Ranked Probability Score; evaluates the full
  predictive distribution, not just the median.
- **Quantile loss** — Per-quantile scoring for probabilistic forecasts.

.. code-block:: python

    from openstef.evaluation import EvaluationConfig, evaluate_predictions

    eval_config = EvaluationConfig(
        metrics=["MAE", "RMSE", "rMAE"],
        quantiles=[0.1, 0.5, 0.9],
    )

    report = evaluate_predictions(
        predictions=predictions,
        ground_truth=ground_truth,
        config=eval_config,
    )

    # Access a specific metric
    mae = report.get_metric(quantile=0.5, metric_name="MAE")
    print(f"Median-forecast MAE: {mae:.3f} MW")

Comparing Two Models
---------------------

The most common use of backtesting is comparing a candidate model against a baseline.
Run the pipeline twice — once per model — and pass both result sets to the analysis
layer:

.. code-block:: python

    from openstef.backtesting import BacktestPipeline, BacktestConfig

    # Baseline model
    baseline_pipeline = BacktestPipeline(config=config, forecaster=baseline_forecaster)
    baseline_predictions = baseline_pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
    )

    # Candidate model
    candidate_pipeline = BacktestPipeline(config=config, forecaster=candidate_forecaster)
    candidate_predictions = candidate_pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
    )

Both pipelines must share the same ``ground_truth`` and date range so that metrics are
computed on identical data. The ``BacktestConfig`` can differ between models if you
want to test different retraining schedules, but ``prediction_sample_interval`` must
remain consistent.

Visualising Results
--------------------

OpenSTEF provides interactive visualisation tools built on Plotly. Three visualisation
types are particularly useful for backtest analysis.

**Forecast time series comparison**

``ForecastTimeSeriesPlotter`` overlays actual measurements with forecasts from one or
more models, including shaded uncertainty bands from quantile predictions:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef.analysis.plots import ForecastTimeSeriesPlotter

    plotter = ForecastTimeSeriesPlotter()
    plotter.add_measurements(ground_truth.to_series())
    plotter.add_model("Baseline", forecast=baseline_predictions.median())
    plotter.add_model("Candidate", forecast=candidate_predictions.median())

    fig = plotter.plot(title="Baseline vs Candidate — Jan–Jun 2024")
    fig.show()   # opens an interactive Plotly figure

The resulting chart is interactive: you can zoom into specific periods, hover for exact
values, and toggle individual model traces on and off.

**Windowed metric evolution**

Rather than a single summary number, ``WindowedMetricVisualization`` shows how a
metric changes over time using a rolling evaluation window. This is invaluable for
spotting seasonal degradation or identifying when a model needs retraining:

.. code-block:: python

    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import WindowedMetricVisualization
    from openstef_beam.evaluation import Window
    from datetime import timedelta

    analysis_config = AnalysisConfig(
        visualization_providers=[
            WindowedMetricVisualization(
                name="mae_over_time",
                metric="MAE",
                window=Window(size=timedelta(days=7), step=timedelta(days=1)),
                quantile=0.5,
            ),
        ]
    )

**Grouped target metric comparison**

When you have multiple substations or assets, ``GroupedTargetMetricVisualization``
produces bar or box charts that rank targets by accuracy, making it easy to identify
which locations are hardest to forecast:

.. code-block:: python

    from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
    from openstef_core.types import Quantile

    analysis_config = AnalysisConfig(
        visualization_providers=[
            GroupedTargetMetricVisualization(
                name="rmae_by_substation",
                metric="rMAE",
                quantile=Quantile(0.5),
            ),
            GroupedTargetMetricVisualization(
                name="probabilistic_accuracy",
                metric="rCRPS",
            ),
        ]
    )

.. mermaid:: /diagrams/getting_started/backtesting_diagram_2.mmd

Practical Tips
---------------

**Keep the evaluation window honest.** Always ensure the backtest period starts after
enough historical data exists to train a meaningful initial model. A common mistake is
starting the simulation at the very beginning of the dataset, where the first training
window is too short to be representative.

**Match retraining frequency to your operational reality.** If your production system
retrains daily, configure ``training_interval=timedelta(days=1)`` in the backtest.
Overly infrequent retraining in the simulation will make the model look worse than it
actually is in production.

**Use rMAE or rCRPS for cross-asset comparisons.** Absolute metrics like MAE are
scale-dependent — a substation with twice the load will naturally show a higher MAE
even if the relative accuracy is identical. Relative metrics normalise this away.

**Separate the evaluation period from the training period.** If you tuned any
hyperparameters on the same historical window you're backtesting over, your results
will be optimistic. Reserve a held-out period for final evaluation.

Next Steps
-----------

- :doc:`advanced_customization` — learn how to plug in custom models and feature
  engineering pipelines that work with ``BacktestForecasterMixin``.
- :doc:`first_forecast` — if you haven't built a basic forecast yet, start there
  before running a full backtest.
- :doc:`quickstart` — a minimal end-to-end example to orient yourself in the library.