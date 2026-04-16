The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package — **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics — is the evaluation layer of the OpenSTEF library. Where ``openstef_core`` and ``openstef_models`` are concerned with *producing* forecasts, BEAM is concerned with *rigorously testing* them. It orchestrates a complete workflow that takes a forecasting model from raw historical data through to comparative benchmark reports, all while enforcing strict no-lookahead guarantees.

This page covers how BEAM is structured, how its four stages connect, and how to integrate your own models and data into the pipeline.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Why BEAM Exists
---------------

Simple train/test splits are misleading for operational energy forecasting. A model trained on data from 2023 and tested on a held-out slice of 2023 has implicitly seen the future: it was trained knowing the statistical distribution of the full year. In production, a model trained on Monday must forecast Tuesday using only what was known on Monday.

BEAM addresses this with *versioned time-series replay*. The ``RestrictedHorizonVersionedTimeSeries`` object passed to every ``fit`` and ``predict`` call enforces a hard horizon: calling ``data.get_window(start, end, available_before)`` will only return rows that were genuinely available before the specified timestamp. No matter how the forecaster is written, it cannot accidentally access future data.

This design makes BEAM results directly comparable to production performance, which is the primary reason to use it over ad-hoc evaluation scripts.

The Four Stages
---------------

BEAM's pipeline is sequential: each stage consumes the output of the previous one.

**Backtesting** replays history. The runner iterates over time, periodically calling ``fit()`` with recent history and then calling ``predict()`` every few hours to generate forecasts. Each forecast is stamped with an ``available_at`` timestamp — the moment the prediction was generated — which later stages use to compute lead-time-stratified metrics. Results are written to ``predictions.parquet`` files, one per target.

**Evaluation** reads those parquet files and computes metrics. Because every prediction carries an ``available_at`` timestamp, BEAM can evaluate accuracy at any lead time: how good is the 1-hour-ahead forecast compared to the 24-hour-ahead forecast? This lead-time analysis is critical for operational planning, where a grid operator needs to know whether a 36-hour forecast is reliable enough to commit to a maintenance window.

**Analysis** turns evaluation scores into interactive HTML visualisations. Plots are generated globally, per group, and per individual target, giving both a high-level summary and the ability to drill into a specific substation or solar park that is performing poorly.

**Benchmarking** runs the full pipeline for multiple models simultaneously and produces side-by-side comparison reports. The ``BenchmarkRunner`` manages the orchestration: it accepts a *forecaster factory* — a callable that returns a fresh forecaster instance for each target — and handles parallelism, result storage, and report generation automatically.

Package Dependencies
--------------------

``openstef_beam`` sits at the top of the OpenSTEF dependency graph. It imports from both sibling packages:

- ``openstef_core`` provides the ``TimeSeriesDataset`` class (see :doc:`core`) that forecasters must return from ``predict()``, as well as the ``Quantile`` type used to declare which quantiles a model produces.
- ``openstef_models`` provides ready-made model implementations (see :doc:`models`) such as GBLinear that can be wrapped in a ``BacktestForecasterMixin`` and dropped directly into a BEAM pipeline.

Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``. This one-way dependency means you can use the core and models packages in production serving code without pulling in the evaluation framework.

The ``BacktestForecasterMixin`` Interface
-----------------------------------------

Every model that participates in a BEAM backtest must implement ``BacktestForecasterMixin``. The interface is intentionally minimal:

.. code-block:: python

    from openstef_beam.backtesting.backtest_forecaster.mixins import (
        BacktestForecasterConfig,
        BacktestForecasterMixin,
    )
    from openstef_beam.backtesting.restricted_horizon_timeseries import (
        RestrictedHorizonVersionedTimeSeries,
    )
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.types import Q, Quantile


    class MedianHistoryForecaster(BacktestForecasterMixin):
        """Baseline forecaster: predicts the median of the last 7 days."""

        def __init__(self) -> None:
            self.config = BacktestForecasterConfig()
            self._median_profile = None

        @property
        def quantiles(self) -> list[Quantile]:
            # Declare which quantiles this model produces.
            return [Q(0.05), Q(0.50), Q(0.95)]

        def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
            # Called periodically with recent history.
            # data.horizon is the current simulation time — no future data leaks through.
            window = data.get_window(
                start=data.horizon - pd.Timedelta(days=7),
                end=data.horizon,
                available_before=data.horizon,
            )
            self._median_profile = window["load"].groupby(window.index.time).median()

        def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset:
            # Called every few hours to generate a forecast.
            # Return a TimeSeriesDataset with 'load' and one column per quantile.
            forecast_index = pd.date_range(
                start=data.horizon,
                periods=192,  # 48 hours at 15-minute resolution
                freq="15min",
            )
            p50 = forecast_index.time.map(self._median_profile)
            return TimeSeriesDataset(
                {
                    "load": p50,
                    "quantile_P05": p50 * 0.8,
                    "quantile_P50": p50,
                    "quantile_P95": p50 * 1.2,
                },
                index=forecast_index,
            )

The ``data.get_window()`` call is the key pattern. Passing ``available_before=data.horizon`` is what prevents lookahead: BEAM will raise an error if you attempt to read data beyond the current simulation horizon.

Running a Benchmark
-------------------

The ``BenchmarkRunner`` is the main entry point for orchestrating a full evaluation. The built-in Liander 2024 dataset (auto-downloaded from HuggingFace) provides a convenient starting point:

.. code-block:: python

    from openstef_beam.benchmarking import create_liander2024_benchmark_runner

    # Create a runner pre-configured with the Liander 2024 dataset,
    # standard metrics, and default analysis plots.
    runner = create_liander2024_benchmark_runner()

    # A forecaster factory is a callable (context, target) -> forecaster.
    # BEAM calls it once per target so each target gets a fresh model instance.
    def my_forecaster_factory(context, target):
        return MedianHistoryForecaster()

    runner.run(
        forecaster_factory=my_forecaster_factory,
        run_name="median_baseline",
        n_processes=4,          # Parallel targets; set to 1 for debugging.
        filter_args=["solar"],  # Optional: restrict to a subset of target groups.
    )

Results are written under ``./benchmark_results/median_baseline/``. The directory layout is:

.. code-block:: text

    benchmark_results/
    └── median_baseline/
        ├── backtest/
        │   └── solar/
        │       └── <target_name>/
        │           └── predictions.parquet
        ├── evaluation/
        │   └── scores.parquet
        └── analysis/
            ├── global_overview.html
            ├── per_group/
            └── per_target/

.. note::

   BEAM automatically skips the backtesting stage for any target that already has a ``predictions.parquet`` on disk. This means you can interrupt and resume a long benchmark run, or re-run only the evaluation and analysis stages after changing a metric, without repeating expensive model training.

Bringing Your Own Data
----------------------

If you have your own measurement data rather than the Liander 2024 dataset, subclass ``SimpleTargetProvider`` and override two path methods:

.. code-block:: python

    from pathlib import Path
    from openstef_beam.benchmarking.target_provider import SimpleTargetProvider, BenchmarkTarget


    class MyGridTargetProvider(SimpleTargetProvider):
        """Serves measurement and weather data from a local parquet store."""

        BASE_PATH = Path("/data/grid_measurements")

        def _get_measurements_path_for_target(self, target: BenchmarkTarget) -> Path:
            return self.BASE_PATH / target.group_name / target.name / "load.parquet"

        def _get_weather_path_for_target(self, target: BenchmarkTarget) -> Path:
            return self.BASE_PATH / target.group_name / target.name / "weather.parquet"

The targets themselves are typically declared in a YAML file that lists group names, target names, and any metadata the forecaster needs. Pass your provider to ``create_custom_benchmark_runner()`` alongside your chosen metrics and the pipeline assembles itself.

Evaluating Pre-existing Forecasts
----------------------------------

BEAM does not require you to run backtesting through its own loop. If you already have forecast outputs — from a production system, a third-party model, or a previous experiment — you can point the pipeline at existing ``predictions.parquet`` files and run only evaluation and analysis:

.. code-block:: python

    from openstef_beam.benchmarking.storage import LocalBenchmarkStorage
    from openstef_beam.backtesting.backtest_forecaster.dummy_forecaster import DummyForecaster
    from openstef_core.types import Q

    QUANTILES = [Q(0.05), Q(0.50), Q(0.95)]

    storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))
    runner = create_custom_benchmark_runner(storage=storage)

    # DummyForecaster satisfies the interface but never calls fit() or predict().
    # BEAM detects the existing predictions.parquet and skips backtesting entirely.
    runner.run(
        forecaster_factory=lambda ctx, tgt: DummyForecaster(predict_quantiles=QUANTILES),
        run_name="my_external_forecasts",
        n_processes=1,
    )

The parquet files must follow the expected schema: a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column, and one column per quantile named using ``Quantile.format()`` (e.g. ``quantile_P50``).

Comparing Multiple Models
--------------------------

After running two or more models, BEAM can generate side-by-side comparison reports:

.. code-block:: python

    from openstef_beam.benchmarking.comparison import compare_benchmark_runs

    compare_benchmark_runs(
        run_names=["median_baseline", "gblinear_v1", "gblinear_v2"],
        results_path=Path("./benchmark_results"),
        output_path=Path("./benchmark_results_comparison"),
    )

The comparison script auto-detects which targets are present in *all* runs before computing differences, so partial runs do not skew the comparison. Output is a set of HTML plots saved to the output path: one global overview, one per target group, and one per individual target.

.. note::

   For ensemble model evaluation and advanced probabilistic metrics, see :doc:`meta`. For details on the ``TimeSeriesDataset`` type that forecasters must return, see :doc:`core`. For the model implementations available to wrap in a ``BacktestForecasterMixin``, see :doc:`models`.