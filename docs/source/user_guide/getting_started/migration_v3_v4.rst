Migrating from V3 to V4
=======================

This guide helps you migrate existing OpenSTEF V3 code to the V4 architecture. OpenSTEF 4.0 is a major refactor that introduces a modular package structure, decouples external dependencies, and improves type safety and extensibility.

If you are installing OpenSTEF for the first time, see the :doc:`installation` page instead.

Overview of Changes
-------------------

The V4 release restructures OpenSTEF from a single monolithic package into a set of composable, independently usable packages:

- **Package split**: The single ``openstef`` package is now split into focused packages (e.g., ``openstef_models``, and others for pipelines, integrations, and data handling).
- **Decoupled dependencies**: External systems like MLflow, openstef-dbc, and specific model backends (xgboost/gblinear) are no longer hard requirements.
- **Modular design**: Components work in isolation and are composable into larger systems.
- **Flexible configuration**: Hard-coded assumptions are replaced with configurable options.
- **Full type safety**: Comprehensive type annotations throughout the codebase.

.. mermaid:: /diagrams/user_guide/getting_started/migration_v3_v4_diagram_1.mmd

Breaking Changes Summary
------------------------

.. warning::

   V4 is not backwards-compatible with V3. You will need to update imports, configuration, and potentially pipeline orchestration code.

The key breaking changes are:

- **Import paths have changed** — the ``openstef`` top-level package is reorganized into sub-packages.
- **PredictionJobDataClass** — configuration and instantiation may differ.
- **Pipeline functions** — signatures and return types have been updated.
- **MLflow integration** — now optional and accessed through an integrations sub-package.
- **External dependencies** — previously implicit dependencies must now be explicitly installed.

Step-by-Step Migration Workflow
-------------------------------

Follow these steps to migrate your V3 codebase:

1. **Audit your imports** — identify all ``from openstef.*`` imports in your code.
2. **Install V4 packages** — install the new package(s) that correspond to your usage.
3. **Update import paths** — rewrite imports to use the new module structure.
4. **Update PredictionJob configuration** — adjust field names and types as needed.
5. **Update pipeline calls** — adapt to new function signatures.
6. **Configure integrations explicitly** — set up MLflow or other integrations as optional add-ons.
7. **Run tests** — verify your forecasting workflows produce expected results.

Package Structure Changes
-------------------------

Before (V3):
^^^^^^^^^^^^^

In V3, everything lived under a single ``openstef`` namespace:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

After (V4):
^^^^^^^^^^^^

In V4, functionality is organized into dedicated packages. Models, integrations, and explainability are separated:

.. code-block:: python

   from openstef_models.integrations import mlflow, optuna, joblib

The ``openstef_models`` package contains core model logic, while integrations with external systems (MLflow, Optuna, Joblib) are isolated in ``openstef_models.integrations`` and only loaded when needed.

.. note::

   The exact import paths for pipeline functions in V4 may differ from V3. Consult the V4 API reference for the canonical import locations.

Prediction Job Configuration
-----------------------------

Before (V3):
^^^^^^^^^^^^^

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = dict(
       id=287,
       model='xgb',
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
   pj = PredictionJobDataClass(**pj)

Note that in V3, quantiles were specified as integers (percentiles: 10, 30, 50, ...) in some examples and as floats (0.05, 0.1, 0.3, ...) in others, leading to inconsistency.

After (V4):
^^^^^^^^^^^^

In V4, prediction job configuration uses standardized types and consistent quantile specification:

.. code-block:: python

   # V4 uses consistent float quantiles (0.0 to 1.0)
   # and removes deprecated fields like default_modelspecs
   pj = dict(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
   )

**What changed:**

- Quantiles are always specified as floats between 0.0 and 1.0.
- Deprecated fields (``default_modelspecs``, ``save_train_forecasts``) are removed from the core configuration.
- Storage and artifact configuration is handled separately through integration modules.

Training Pipeline
-----------------

Before (V3):
^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

In V3, MLflow configuration was passed directly to pipeline functions, tightly coupling the training logic to a specific experiment tracking backend.

After (V4):
^^^^^^^^^^^^

.. code-block:: python

   # V4: MLflow is configured separately through the integrations module
   from openstef_models.integrations import mlflow

   # Configure tracking independently of the pipeline
   mlflow.configure(tracking_uri="./mlflow_trained_models")

   # Pipeline functions focus on ML logic, not infrastructure
   # (exact V4 pipeline API — consult API reference for current signatures)

**What changed:**

- MLflow is no longer a required dependency — it is an optional integration.
- Pipeline functions no longer accept infrastructure parameters like ``mlflow_tracking_uri``.
- Separation of concerns: training logic is decoupled from artifact storage.

Forecast Pipeline
-----------------

Before (V3):
^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(
       pj,
       forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

After (V4):
^^^^^^^^^^^^

.. code-block:: python

   # V4: Model loading and forecasting are decoupled
   # Integration setup happens once, not per-call
   from openstef_models.integrations import mlflow

   mlflow.configure(tracking_uri="./mlflow_trained_models")

   # Forecast pipeline uses configured integrations automatically

**What changed:**

- Model loading is handled by the configured integration backend.
- The forecast pipeline no longer requires you to pass tracking URIs on every call.
- This enables swapping storage backends (local files, cloud, databases) without changing pipeline code.

Dependency Management
---------------------

V3 installed all dependencies (including MLflow, specific model backends) as hard requirements. V4 uses optional dependency groups:

.. code-block:: bash

   # Install core library only
   pip install openstef-models

   # Install with MLflow integration
   pip install openstef-models[mlflow]

   # Install with Optuna for hyperparameter tuning
   pip install openstef-models[optuna]

   # Install all optional integrations
   pip install openstef-models[all]

This reduces the base installation size and avoids dependency conflicts in environments that don't need every integration.

Common Migration Issues
-----------------------

**ImportError after upgrading**
   The most common issue. Search your codebase for ``from openstef.`` and update to the new package paths. Use the V4 API reference as the canonical source.

**Quantile format errors**
   If you used integer percentiles (e.g., ``[10, 50, 90]``), convert them to floats (``[0.1, 0.5, 0.9]``).

**MLflow not found**
   Install the optional MLflow integration: ``pip install openstef-models[mlflow]``.

**Missing ``default_modelspecs`` field**
   This field is removed in V4. Model specifications are handled through the new configuration system.

**Pipeline return type changes**
   Check that your code handles the updated return types from pipeline functions. V4 may return richer result objects instead of plain tuples.

Further Reading
---------------

- See the :doc:`installation` page for V4 installation instructions.
- Consult the API Reference for complete V4 module documentation.
- Review the changelog for a full list of changes between releases.