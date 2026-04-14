Reliability and Fallback Strategies
====================================

In production energy forecasting, things go wrong: sensors fail, data pipelines stall,
models grow stale, and edge cases surface that were never seen during training. This page
covers the mechanisms OpenSTEF provides to detect these situations and respond gracefully,
so that your forecasting system continues to deliver useful output even when individual
components are degraded.

For background on what a forecast is and how it is produced, see :doc:`forecasting_basics`.
For details on probabilistic output and confidence intervals, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

----

Why Reliability Matters in Production
--------------------------------------

A short-term energy forecast is only valuable if it is available on time and based on
trustworthy inputs. Grid operators and energy traders act on these forecasts; a silent
failure — where a model produces numbers that look plausible but are based on corrupted
or stale data — is often more dangerous than an obvious error. OpenSTEF addresses this
through a layered approach:

1. **Input validation** — reject or flag bad data before it reaches the model.
2. **Model health checks** — detect when a trained model is too old or underperforming.
3. **Fallback forecasting** — produce a reasonable naive forecast when the primary model cannot be used.
4. **Graceful degradation** — surface errors explicitly rather than silently propagating bad values.

----

Input Validation: Catching Bad Data Early
------------------------------------------

OpenSTEF ships several transform classes that sit in the preprocessing pipeline and raise
structured exceptions when the data does not meet minimum quality requirements. These are
applied automatically when you use the built-in workflow configurations, but you can also
compose them manually.

**Flatline detection**

A common failure mode in energy metering is a *flatliner*: a sensor or data feed that
stops updating and simply repeats the last known value. The ``FlatlineChecker`` transform
detects this pattern:

.. code-block:: python

   from openstef_models.transforms.validation.flatline_checker import FlatlineChecker
   from datetime import timedelta

   checker = FlatlineChecker(
       load_column="load",
       flatliner_threshold=timedelta(hours=2),  # flag if constant for 2+ hours
       detect_non_zero_flatliner=True,
       error_on_flatliner=False,  # warn rather than raise
   )

   # Applied as part of a pipeline transform
   validated_data = checker.transform(data)

Setting ``error_on_flatliner=True`` causes the transform to raise a
``FlatlinerDetectedError``, which you can catch at the workflow level to trigger a
fallback. Setting it to ``False`` logs a warning and passes the data through, which is
appropriate when you want to continue forecasting with a caveat rather than halt entirely.

**Completeness checks**

Missing intervals are another common problem. The ``CompletenessChecker`` transform
computes what fraction of expected timestamps are present and raises
``InsufficientlyCompleteError`` if the dataset falls below a configurable threshold:

.. code-block:: python

   from openstef_models.transforms.validation.completeness_checker import CompletenessChecker

   completeness_check = CompletenessChecker(min_completeness=0.8)
   # Raises InsufficientlyCompleteError if < 80% of intervals are present
   validated_data = completeness_check.transform(data)

**Input consistency**

The ``InputConsistencyChecker`` validates structural properties of the dataset — column
presence, index regularity, and type consistency — before any model logic runs:

.. code-block:: python

   from openstef_models.transforms.validation.input_consistency_checker import InputConsistencyChecker

   checker = InputConsistencyChecker()
   checker.fit(training_data)
   checker.transform(inference_data)  # raises if inference data is structurally inconsistent

These three validators are included by default in the ``EnsembleForecastingWorkflowConfig``
preprocessing pipeline, so you get them for free when using the standard workflows.

----

Model Staleness Detection
--------------------------

A trained model that was accurate six months ago may no longer reflect current load
patterns — tariff changes, new large consumers, or seasonal drift can all erode
performance. OpenSTEF's workflow layer tracks model age and can automatically decide
whether to reuse an existing model or retrain.

The relevant configuration lives in ``EnsembleForecastingWorkflowConfig`` (and the
equivalent ``ForecastingWorkflowConfig`` for single-model workflows):

.. code-block:: python

   from openstef_beam.workflows.ensemble_forecasting_workflow import EnsembleForecastingWorkflowConfig
   from datetime import timedelta

   config = EnsembleForecastingWorkflowConfig(
       model_id="substation_42",
       # ...other config...
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),   # retrain if model is older than 7 days
       model_selection_enable=True,
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,   # bias towards newer models
   )

When ``model_reuse_enable=True``, the workflow checks the age of the stored model at
training time. If the model is younger than ``model_reuse_max_age``, it is reused without
retraining. If it is older, a new model is trained and compared against the stored one
using ``model_selection_metric``. The ``model_selection_old_model_penalty`` multiplies
the old model's metric score, creating a bias towards deploying the freshly trained
model unless the old one is substantially better — guarding against regressions from
noisy retraining runs.

.. note::

   Setting ``model_reuse_max_age`` too aggressively (e.g., ``timedelta(hours=6)``) will
   trigger frequent retraining and increase compute costs. A value of 7 days is a
   reasonable starting point for most substations; adjust based on observed performance
   drift in your specific context.

----

The BaseCaseForecaster: A Principled Fallback
----------------------------------------------

When the primary model cannot produce a forecast — because training data is insufficient,
the model is too stale, or an upstream error has occurred — OpenSTEF provides the
``BaseCaseForecaster`` as a drop-in fallback. This model implements the observation that
energy load patterns are strongly weekly-periodic: it takes the load profile from the
same weekday one week ago and repeats it as the forecast.

.. code-block:: python

   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   fallback_model = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # use last week's profile
           fallback_lag=timedelta(days=14),  # fall back to two weeks ago if needed
       ),
   )

The two-tier lag design is important: if the primary lag window (7 days ago) itself
contains missing data — for example, because last week also had a sensor outage — the
forecaster automatically reaches back to the fallback lag (14 days ago). This means the
``BaseCaseForecaster`` is robust to single-week data gaps, which are common in real
metering infrastructure.

Confidence intervals are derived from the hourly standard deviation of the repeated base
case data, so the probabilistic output remains meaningful even in fallback mode.

**Integrating the fallback into your workflow**

A typical production pattern wraps the primary forecasting call and falls back on any
``InsufficientlyCompleteError`` or model-related exception:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError, FlatlinerDetectedError
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   import logging

   logger = logging.getLogger(__name__)

   def produce_forecast(primary_model, dataset, quantiles, horizons):
       """Attempt primary forecast; fall back to base case on failure."""
       try:
           return primary_model.predict(dataset)
       except (InsufficientlyCompleteError, FlatlinerDetectedError) as exc:
           logger.warning(
               "Primary forecast failed (%s); switching to base case fallback.",
               type(exc).__name__,
           )
           fallback = BaseCaseForecaster(
               quantiles=quantiles,
               horizons=horizons,
               hyperparams=BaseCaseForecasterHyperParams(
                   primary_lag=timedelta(days=7),
                   fallback_lag=timedelta(days=14),
               ),
           )
           fallback.fit(dataset)
           return fallback.predict(dataset)

.. warning::

   The ``BaseCaseForecaster`` does not learn from recent trends, price signals, or
   weather. It is a safety net, not a substitute for a well-maintained primary model.
   Monitor how often your system falls back — a high fallback rate is a signal that
   something upstream needs attention.

----

Monitoring Model Performance Over Time
----------------------------------------

Detecting staleness by age alone is a blunt instrument. A model trained last week may
already be performing poorly if there was an unusual event (a public holiday, a grid
topology change, a large new industrial load). OpenSTEF's analysis tooling supports
windowed metric evaluation to surface these degradations:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from datetime import timedelta

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=7), step=timedelta(days=1)),
           )
       ]
   )

The resulting plot shows how MAE evolves over a rolling window, making it straightforward
to identify the onset of performance degradation and correlate it with known events. Use
this in combination with the ``model_reuse_max_age`` setting: if you observe that
performance typically degrades after 3–4 days for a particular substation, tighten the
max age accordingly.

----

Practical Recommendations
--------------------------

Drawing from production experience with OpenSTEF deployments:

- **Always enable flatline detection** with ``error_on_flatliner=False`` in inference
  pipelines. Silent flatliners are among the most common causes of forecast degradation
  in real metering systems.

- **Set ``model_reuse_max_age`` based on observed drift**, not a fixed calendar. Use
  windowed metric plots to calibrate this per substation or asset type.

- **Log every fallback invocation** with the reason. A dashboard showing fallback rate
  per asset over time is one of the most useful operational signals you can build.

- **Test your fallback path explicitly**. Inject synthetic data gaps and flatliners in
  a staging environment to verify that the fallback activates and produces sensible output.

- **Keep the ``BaseCaseForecaster`` fitted on recent data** even when the primary model
  is healthy, so it is ready to serve immediately if the primary fails mid-day.

----

Related Topics
--------------

- :doc:`forecasting_basics` — how the primary forecasting pipeline works end-to-end
- :doc:`model_selection` — choosing and comparing model types, including when to use
  ensemble approaches that are inherently more robust than single models
- :doc:`feature_engineering` — how missing weather or price features affect forecast
  quality, and strategies for handling feature gaps
- :doc:`quantiles_and_confidence` — understanding the probabilistic output produced by
  both primary models and the ``BaseCaseForecaster``