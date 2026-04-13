Backtesting
===========

Backtesting is the process of evaluating a forecasting model against historical data
by simulating how it would have performed in real operational conditions. Rather than
simply fitting a model and measuring in-sample accuracy, OpenSTEF's backtesting
infrastructure replays the past: it generates predictions at regular intervals, retrains
the model periodically, and carefully prevents any future data from leaking into earlier
forecasts. This page walks through the full workflow — configuring a backtest,
running it, computing evaluation metrics, and comparing multiple models.

If you haven't produced your first forecast yet, start with :doc:`first_forecast` before
continuing here. For customising the underlying forecaster, see
:doc:`advanced_customization`.

.. note:: [DIAGRAM: Timeline showing backtesting simulation — predict events and retrain events interleaved across a historical window, with an arrow indicating chronological order and a "no data leakage" boundary.]


How OpenSTEF Backtesting Works
------------------------------

The ``BacktestPipeline`` class in ``openstef_beam`` simulates the operational
environment as faithfully as possible. At each *predict event* it generates a forecast
using only the data that would have been available at that moment. At each *retrain
event* it fits a fresh model on the history available up to that point. The two
schedules are independent, so you can, for example, retrain weekly while producing
new predictions every six hours.

Three parameters in ``BacktestConfig`` control the simulation cadence:

- ``prediction_sample_interval`` — the resolution of each individual forecast
  (e.g. 15-minute samples). **Must match** the forecaster's own
  ``predict_sample_interval``.
- ``predict_interval`` — how often a new prediction run is triggered (default: 6 hours).
- ``train_interval`` — how often the model is retrained from scratch (default: 7 days).

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

The ``align_time`` field anchors both schedules to a fixed reference point so that
prediction and training events always fall on consistent clock times regardless of
where the backtest window starts.


Running a Backtest
------------------

``BacktestPipeline`` takes a ``BacktestConfig`` and any forecaster that implements
``BacktestForecasterMixin``. Calling ``run()`` returns a ``VersionedTimeSeriesDataset``
containing every prediction produced during the simulation, tagged with the timestamp
at which it was generated.

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

    # Assume `forecaster` is already constructed and `ground_truth` /
    # `predictors` are VersionedTimeSeriesDataset objects loaded from your
    # historical archive.

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
    )

    pipeline = BacktestPipeline(config=config, forecaster=forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
        show_progress=True,   # prints a progress bar
    )

Passing ``start=None`` or ``end=None`` tells the pipeline to use the earliest or latest
timestamp present in the data, which is convenient during exploratory work.

.. note::

   ``BacktestPipeline`` enforces that ``config.prediction_sample_interval`` equals
   ``forecaster.config.predict_sample_interval``. A ``ValueError`` is raised at
   construction time if they differ, so mismatches are caught before any computation
   begins.


Evaluation Metrics
------------------

Once you have backtest predictions, the ``EvaluationPipeline`` computes metrics by
comparing them against the ground truth. OpenSTEF ships a rich set of metrics in
``openstef_beam.metrics`` covering both deterministic and probabilistic forecasts:

**Deterministic metrics**

- ``mae`` — Mean Absolute Error
- ``rmae`` — Relative MAE (normalised by load magnitude)
- ``mape`` — Mean Absolute Percentage Error
- ``r2`` — Coefficient of determination
- ``fbeta``, ``precision_recall``, ``confusion_matrix`` — peak/congestion detection

**Probabilistic metrics**

- ``crps`` / ``rcrps`` — (Relative) Continuous Ranked Probability Score
- ``relative_pinball_loss`` — quantile-specific sharpness
- ``riqd`` — Relative Inter-Quantile Distance (spread)
- ``mean_absolute_calibration_error`` — reliability of confidence intervals
- ``observed_probability`` — always included automatically as a calibration check

You configure which metrics to compute and over which time dimensions to slice them
through ``EvaluationConfig``:

.. code-block:: python

    from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
    from openstef_beam.evaluation.models import AvailableAt, LeadTime, Window
    from openstef_beam.metrics import mae, rmae, crps, relative_pinball_loss
    from openstef_beam.metrics.providers import MaeProvider, RmaeProvider, CrpsProvider

    eval_config = EvaluationConfig(
        available_ats=[AvailableAt.from_string("D-1T06:00")],
        lead_times=[LeadTime.from_string("PT6H"), LeadTime.from_string("PT24H")],
        windows=[Window(lag=timedelta(hours=0), size=timedelta(days=30))],
    )

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],   # 0.5 (median) is required
        window_metric_providers=[MaeProvider(), RmaeProvider()],
        global_metric_providers=[MaeProvider(), RmaeProvider(), CrpsProvider()],
    )

    report = eval_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth,
        target_column="load_mw",
    )

The returned ``EvaluationReport`` organises results by ``available_at``, ``lead_time``,
and rolling ``window``, making it straightforward to ask questions like *"how does
accuracy degrade as the forecast horizon grows?"* or *"does performance drop in winter
months?"*.

.. note::

   ``quantiles`` must always include ``0.5``. The pipeline raises a ``ValueError``
   immediately if the median quantile is missing.


Comparing Multiple Models
-------------------------

The real power of backtesting emerges when you run the same historical window against
several model configurations and compare the results side by side. OpenSTEF provides
``BenchmarkPipeline`` and ``BenchmarkComparisonPipeline`` for exactly this purpose.

**Step 1 — Run a named benchmark for each model**

.. code-block:: python

    from openstef_beam.benchmarking import BenchmarkPipeline

    # Run benchmark for the baseline model
    benchmark = BenchmarkPipeline(
        backtest_config=config,
        evaluation_config=eval_config,
        storage=storage,           # BenchmarkStorage implementation
        target_provider=targets,   # BenchmarkTarget provider
    )

    benchmark.run(
        forecaster_factory=baseline_factory,
        run_name="baseline_xgb",
    )

    # Run benchmark for the challenger model
    benchmark.run(
        forecaster_factory=challenger_factory,
        run_name="challenger_lgbm",
    )

Each run stores its predictions and ``EvaluationReport`` objects via the ``storage``
object, keyed by ``run_name``. This means expensive backtests only need to be computed
once; you can re-analyse the stored results at any time without re-running the
simulation.

**Step 2 — Compare the stored runs**

.. code-block:: python

    from openstef_beam.benchmarking import BenchmarkComparisonPipeline

    comparison = BenchmarkComparisonPipeline(
        storage=storage,
        target_provider=targets,
        analysis_config=analysis_config,
    )

    comparison.run(run_names=["baseline_xgb", "challenger_lgbm"])

``BenchmarkComparisonPipeline`` aggregates results at three levels:

- **Global** — single summary metrics across all targets and time.
- **Group** — metrics per logical target group (e.g. by region or asset type).
- **Target** — per-asset breakdown for diagnosing where one model beats another.

.. note:: [DIAGRAM: Three-level aggregation hierarchy — Global → Group → Target — with arrows showing how BenchmarkComparisonPipeline rolls up EvaluationReport objects from individual targets.]


Performance Visualisation
--------------------------

Analysis and visualisation are handled by ``AnalysisPipeline``, which consumes
``EvaluationReport`` objects and produces structured visualisation outputs. It is
invoked automatically inside ``BenchmarkPipeline`` after each evaluation step, but
you can also call it directly on stored reports:

.. code-block:: python

    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig
    from openstef_beam.analysis.models import AnalysisScope, AnalysisAggregation

    analysis = AnalysisPipeline(config=AnalysisConfig())

    visualizations = analysis.run_for_reports(
        reports=[(target_metadata, report)],
        scope=AnalysisScope(
            aggregation=AnalysisAggregation.NONE,
            target_name="substation_42",
            group_name="north_region",
            run_name="challenger_lgbm",
        ),
    )

    storage.save_analysis_output(output=visualizations)

The outputs include metric-over-lead-time curves, calibration plots, and rolling-window
performance traces — all generated by OpenSTEF's built-in analysis tooling without
requiring any manual plotting code.


Tips for Reliable Backtests
----------------------------

- **Use a representative window.** A backtest spanning at least one full year captures
  seasonal variation. Shorter windows may produce optimistic results that don't
  generalise.
- **Match operational cadence.** Set ``predict_interval`` and ``train_interval`` to
  match how you intend to run the model in production. A mismatch can make backtest
  results misleading.
- **Check completeness.** The ``completeness`` metric in ``openstef_beam.metrics``
  reports what fraction of expected forecast timestamps were actually produced. Low
  completeness often signals data gaps in the historical archive.
- **Parallelise large benchmarks.** ``BenchmarkPipeline.run()`` accepts an
  ``n_processes`` argument to distribute target-level backtests across CPU cores,
  which is important when evaluating dozens of substations or assets simultaneously.


Next Steps
----------

- :doc:`advanced_customization` — plug in custom model architectures and feature
  engineering pipelines.
- :doc:`first_forecast` — revisit the end-to-end single-forecast workflow if you need
  a refresher on how ``BacktestForecasterMixin`` fits into the broader library.
- :doc:`quickstart` — the minimal working example if you want a fast sanity check
  before committing to a full backtest run.