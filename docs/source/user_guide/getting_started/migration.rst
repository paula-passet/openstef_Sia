Migrating from OpenSTEF 3
=========================

This page guides you through migrating an existing OpenSTEF V3 codebase to V4. It covers
the conceptual shifts behind the redesign, maps old APIs to their new equivalents, and
highlights the areas that require the most attention.

.. note::

   If you are starting fresh with OpenSTEF, skip this page and begin with
   :doc:`/user_guide/getting_started/installation`.

Why the Split Happened
----------------------

OpenSTEF V3 shipped as a single ``openstef`` package containing models, pipelines,
evaluation logic, database connectors, and data classes — all tightly coupled. This made
it difficult to:

- Use forecasting models without pulling in database dependencies.
- Evaluate or backtest models independently of the training pipeline.
- Extend the library without understanding the entire codebase.

V4 applies **separation of concerns** by splitting into focused packages:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Package
     - Responsibility
     - V3 Equivalent
   * - ``openstef-core``
     - Data types, interfaces, base classes, shared utilities
     - Parts of ``openstef.data_classes``, internal utilities
   * - ``openstef-models``
     - Forecasting models, preprocessing, energy-specific transforms
     - ``openstef.model``, ``openstef.feature_engineering``
   * - ``openstef-beam``
     - Backtesting, Evaluation, Analysis, Metrics
     - ``openstef.validation``, scattered evaluation code
   * - ``openstef-meta``
     - Ensemble / meta-learning models
     - No direct equivalent (new in V4)

Install the full stack with ``pip install openstef``, or pick individual packages for
lighter deployments.

.. mermaid:: /diagrams/user_guide/getting_started/migration_diagram_1.mmd

Key Conceptual Shifts
---------------------

Configuration: Dicts → Pydantic Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In V3, prediction jobs were plain dictionaries (or a thin dataclass wrapper). Typos in
keys were silent, validation happened at runtime deep in the pipeline, and discoverability
was poor.

V4 uses **typed Pydantic configuration models** (rooted in :class:`openstef_core.base_model.BaseConfig`)
that validate at construction time, support YAML serialization, and provide IDE
autocompletion.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(**{
       "id": 287, "model": "xgb", "forecast_type": "demand",
       "lat": 52.0, "lon": 5.0, "resolution_minutes": 15,
   })

**After (V4):**

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig.read_yaml("workflow.yaml")

The new configs are **declarative** — you describe *what* you want, and the preset
factory builds the workflow. See :ref:`concept_configuration` for the full design
rationale.

Data: DataFrames → TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 passed raw ``pandas.DataFrame`` objects between pipeline stages. Each function had to
re-derive metadata (resolution, target column, forecast start) from the frame — a
frequent source of bugs.

V4 introduces :class:`openstef_core.datasets.timeseries_dataset.TimeSeriesDataset`, a
thin wrapper around a DataFrame that **carries metadata the pipeline needs**: frequency,
target column name, and validated time indexing.

**Before (V3):**

.. code-block:: python

   input_data = pd.read_csv("data.csv", index_col="index", parse_dates=True)
   train_model_pipeline(pj, input_data)

**After (V4):**

.. code-block:: python

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   dataset = TimeSeriesDataset(df, frequency=timedelta(minutes=15))

Specialized subclasses like ``ForecastInputDataset`` add further validation (e.g.,
ensuring the target column exists). See :ref:`concept_datasets` for details.

Orchestration: Pipelines/Tasks → Workflows/Presets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 exposed two layers:

- **Pipelines** (e.g., ``train_model_pipeline``) — stateless functions you call with data.
- **Tasks** (in ``openstef-dbc``) — wrappers that fetch data, call a pipeline, and write results.

V4 replaces this with **Workflows** (composable objects) and **Presets** (factory
functions that assemble a workflow from config):

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   train_model_pipeline(pj, train_data, mlflow_tracking_uri="./models")

**After (V4):**

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow
   workflow = create_forecasting_workflow(config)

Workflows are the **easiest migration path** from V3 pipelines. The preset API handles
model selection, preprocessing, and storage configuration based on your
``ForecastingWorkflowConfig``.

.. mermaid:: /diagrams/user_guide/getting_started/migration_diagram_2.mmd

Migration Paths by Use Case
---------------------------

Pipeline Users (Easiest)
^^^^^^^^^^^^^^^^^^^^^^^^

If you called ``train_model_pipeline`` or ``create_forecast_pipeline`` directly with your
own data:

1. Replace your ``PredictionJobDataClass`` dict with a ``ForecastingWorkflowConfig`` YAML.
2. Wrap your DataFrame in a ``TimeSeriesDataset``.
3. Use ``create_forecasting_workflow(config)`` to get a workflow object.
4. Call ``workflow.train(dataset)`` / ``workflow.predict(dataset)``.

See :doc:`/tutorials/forecasting_workflow` for a complete worked example.

Reference Implementation / DBC Users (Hardest)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you relied on ``openstef-dbc`` tasks for database integration (fetching prediction
jobs, writing forecasts, managing model storage):

.. warning::

   The ``openstef-dbc`` package and its task-based orchestration do not have a direct V4
   equivalent. The tight coupling between database schema and pipeline logic means there
   is **no drop-in migration path** currently.

Options:

- **Write a thin adapter** that reads your existing database into V4 config objects and
  ``TimeSeriesDataset`` instances, then delegates to V4 workflows.
- **Contact the team** for guidance on your specific deployment topology.
- See :doc:`/user_guide/deployment/index` for V4's recommended deployment patterns.

Quick Reference Table
---------------------

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - V3 Import / Concept
     - V4 Equivalent
     - Package
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``ForecastingWorkflowConfig`` (Pydantic)
     - ``openstef-models``
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``create_forecasting_workflow(config).train(...)``
     - ``openstef-models``
   * - ``pd.DataFrame`` (raw input)
     - :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset`
     - ``openstef-core``
   * - ``openstef.validation``
     - ``openstef-beam`` evaluation & metrics
     - ``openstef-beam``
   * - ``openstef.model.regressors``
     - :class:`~openstef_models.models.ForecastingModel`
     - ``openstef-models``
   * - ``openstef-dbc`` tasks
     - No direct equivalent — see Deployment guide
     - —

Next Steps
----------

- :doc:`installation` — set up V4 packages
- :doc:`quickstart` — run your first V4 forecast
- :doc:`/user_guide/concepts/index` — understand the new architecture in depth
- :doc:`/user_guide/deployment/index` — production deployment patterns