Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural overhaul. The monolithic ``openstef`` package
has been split into focused sub-packages, the ``PredictionJobDataClass``-centred API has
been replaced with a composable model and pipeline design, and Python 3.12+ is now
required. This page walks through every breaking change and shows concrete before/after
examples so you can migrate an existing V3 codebase with confidence.

.. note::

   This guide covers the library API only. For deployment patterns after migration see
   :doc:`deployment`, and for connecting new data sources see :doc:`data_integration`.

----

What Changed at a Glance
------------------------

- **Package split** — one ``openstef`` package becomes four: ``openstef-core``,
  ``openstef-models``, ``openstef-beam``, and ``openstef-meta``.
- **No more ``PredictionJobDataClass``** — job configuration is replaced by typed
  ``BaseConfig`` / ``ForecastingModel`` objects.
- **Pipeline classes replace pipeline functions** — ``train_model_pipeline()`` and
  ``create_forecast_pipeline()`` are superseded by class-based pipelines in
  ``openstef-beam``.
- **Python version** — V4 requires Python ≥ 3.12. V3 supported Python 3.8+.
- **MLflow coupling removed** — model storage is no longer tied to MLflow by default;
  serialisation is handled through the ``Stateful`` interface.

----

Installation
------------

Before (V3):

.. code-block:: bash

   pip install openstef

After (V4):

.. code-block:: bash

   # Install the meta-package (recommended — pulls all sub-packages)
   pip install openstef

   # Or install only what you need
   pip install openstef-core          # data structures, base classes
   pip install openstef-models        # forecasting model implementations
   pip install openstef-beam          # backtesting, evaluation, analysis, metrics
   pip install "openstef-beam[baselines]"  # beam + bundled baseline models

The top-level ``openstef`` meta-package still exists in V4 and installs all four
sub-packages, so a simple ``pip install --upgrade openstef`` is the fastest starting
point.

----

Package Structure Changes
--------------------------

V3 kept everything under a single namespace. V4 distributes responsibilities across
packages with clear boundaries.

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

The table below maps the most commonly used V3 import paths to their V4 equivalents.

+--------------------------------------------------+--------------------------------------------------+
| V3 import                                        | V4 import                                        |
+==================================================+==================================================+
| ``openstef.data_classes.prediction_job``         | ``openstef_core.base_model.BaseConfig``          |
+--------------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.train_model``                | ``openstef_beam.backtesting.BacktestPipeline``   |
+--------------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.create_forecast``            | ``openstef_models.models.forecasting``           |
+--------------------------------------------------+--------------------------------------------------+
| ``openstef.model.regressors.xgb``                | ``openstef_models`` forecaster classes           |
+--------------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.evaluate_model``             | ``openstef_beam.evaluation.EvaluationPipeline``  |
+--------------------------------------------------+--------------------------------------------------+

----

Defining a Forecasting Job
--------------------------

The ``PredictionJobDataClass`` was a plain dictionary wrapper that bundled model type,
location, horizon, and hyper-parameters into a single object. V4 replaces this with
``BaseConfig``-derived configuration classes and a ``ForecastingModel`` that owns its
own preprocessing and postprocessing steps.

Before (V3):

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
       default_modelspecs=None,
       save_train_forecasts=True,
   )

After (V4):

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from openstef_models.models.forecasting import ForecastingModel

   # Configuration is now a typed Pydantic model — unknown fields raise errors
   # rather than being silently ignored.
   class MyForecastConfig(BaseConfig):
       horizon_minutes: int = 47 * 60
       resolution_minutes: int = 15
       quantiles: list[float] = [0.10, 0.30, 0.50, 0.70, 0.90]
       lat: float = 52.0
       lon: float = 5.0

   config = MyForecastConfig()

   # ForecastingModel composes preprocessing, a forecaster, and postprocessing.
   model = ForecastingModel(
       preprocessing=my_preprocessing_pipeline,
       forecaster=my_forecaster,
       postprocessing=my_postprocessing_pipeline,
   )

.. note::

   Quantiles are now expressed as floats in [0, 1] rather than integers. ``70``
   becomes ``0.70``. Passing integers will raise a ``ValidationError``.

----

Training a Model
----------------

V3 exposed a module-level function. V4 uses a ``BacktestPipeline`` class that
simulates the operational environment — preventing data leakage and respecting
real-time constraints automatically.

Before (V3):

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   train_data = input_data.iloc[:-200, :]  # manual train/test split

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )

   pipeline = BacktestPipeline(
       config=config,
       forecaster=model,   # ForecastingModel from the previous step
   )

   results = pipeline.run(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 1),
       data=input_data,
   )

Key differences:

- The train/test split is no longer manual — ``BacktestPipeline`` handles temporal
  windowing internally.
- MLflow is not a required argument. Model persistence uses the ``Stateful`` interface;
  plug in your own storage backend.
- ``train_interval`` controls periodic retraining, mirroring production behaviour.

----

Creating Forecasts
------------------

Before (V3):

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(pj, input_data, mlflow_tracking_uri="./mlflow_trained_models")

After (V4):

.. code-block:: python

   # After fitting, call predict directly on the ForecastingModel.
   forecast = model.predict(input_data, forecast_start=forecast_start)

   # For contribution/explainability output:
   contributions = model.predict_contributions(input_data)

The ``predict_contributions`` method raises ``NotImplementedError`` on models that do
not support it, so check your forecaster's documentation before calling it.

----

Evaluating Models
-----------------

V3 bundled evaluation inside the training pipeline return values. V4 provides a
dedicated ``EvaluationPipeline`` in ``openstef-beam`` that segments results across
availability times, lead times, and rolling windows.

Before (V3):

.. code-block:: python

   # Evaluation metrics came back as part of train_model_pipeline output
   train, val, test = train_model_pipeline(pj, train_data, ...)
   # metrics were inspected manually from val/test DataFrames

After (V4):

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.evaluation import AvailableAt, LeadTime, Window
   from datetime import timedelta

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       window_metric_providers=my_window_metrics,
       global_metric_providers=my_global_metrics,
   )

   metrics = eval_pipeline.run(predictions=results)

.. note::

   ``EvaluationPipeline`` always appends ``ObservedProbabilityProvider`` to global
   metrics automatically, ensuring calibration is evaluated on every run.

----

Model Serialisation
-------------------

V3 relied on MLflow for model storage. V4 models implement the ``Stateful`` interface,
which decouples serialisation from any particular backend.

Before (V3):

.. code-block:: python

   # Storage was implicit — mlflow_tracking_uri controlled everything
   train_model_pipeline(pj, data, mlflow_tracking_uri="./mlflow_trained_models", ...)

After (V4):

.. code-block:: python

   from openstef_core.mixins.stateful import Stateful

   # Save state to a dict (then write to your preferred backend)
   state = model.get_state()

   # Restore from state
   model.set_state(state)

You can wrap ``get_state`` / ``set_state`` around any storage layer — local disk,
S3, a database — without changing the model code. See :doc:`data_integration` for
patterns that connect to S3 and Databricks.

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate a V3 project.

1. **Upgrade Python** to 3.12 or later if you have not already done so.

2. **Upgrade the package**:

   .. code-block:: bash

      pip install --upgrade openstef

3. **Replace ``PredictionJobDataClass`` definitions** with ``BaseConfig`` subclasses.
   Pay attention to quantile format (integers → floats).

4. **Replace pipeline function calls** — swap ``train_model_pipeline()`` for
   ``BacktestPipeline`` and ``create_forecast_pipeline()`` for ``model.predict()``.

5. **Update import paths** using the mapping table in `Package Structure Changes`_.

6. **Remove MLflow arguments** from pipeline calls. Implement ``Stateful``-based
   persistence if you need to save and reload models.

7. **Migrate evaluation code** to ``EvaluationPipeline``. Replace any manual metric
   computation against ``val``/``test`` DataFrames.

8. **Run your test suite.** Focus first on data shape assertions — several pipeline
   outputs changed from tuples of DataFrames to structured result objects.

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_2.mmd

----

Common Errors After Migration
------------------------------

``ValidationError: quantiles — value is not a valid float``
   You passed integer quantiles (e.g. ``70``) instead of floats (``0.70``).

``ImportError: cannot import name 'train_model_pipeline' from 'openstef'``
   The function no longer exists at the top-level. Use ``BacktestPipeline`` from
   ``openstef_beam.backtesting``.

``NotImplementedError: <MyModel> does not support predict_contributions``
   Your forecaster does not implement ``ContributionsMixin``. Either switch to a model
   that does, or remove the ``predict_contributions`` call.

``TypeError: unexpected keyword argument 'mlflow_tracking_uri'``
   MLflow arguments have been removed from all pipeline constructors. See
   `Model Serialisation`_ above.

----

Further Reading
---------------

- :doc:`use_cases` — end-to-end examples using the V4 API for congestion forecasting
  and other common scenarios.
- :doc:`deployment` — production deployment patterns including containerisation and
  scheduling with the new pipeline classes.
- :doc:`data_integration` — connecting ``openstef-beam`` pipelines to S3, Databricks,
  and InfluxDB data sources.