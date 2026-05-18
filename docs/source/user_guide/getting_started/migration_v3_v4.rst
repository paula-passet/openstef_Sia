Migrating from V3 to V4
=======================

This guide helps you migrate existing OpenSTEF V3 code to V4. It covers breaking changes in package structure, updated APIs, and provides step-by-step instructions with before/after code examples.

If you are starting fresh with OpenSTEF, see :doc:`installation` instead.

Overview of Changes
-------------------

OpenSTEF V4 introduces a significant restructuring of the library to improve modularity, maintainability, and extensibility. The key changes are:

- **Package split**: The monolithic ``openstef`` package has been split into focused sub-packages (e.g., ``openstef_models``)
- **Integration layer**: External system integrations (MLflow, Optuna, Joblib) are now isolated in ``openstef_models.integrations``
- **Quantile specification**: Quantiles are now specified as floats (0.0–1.0) consistently, rather than mixed integer/float formats
- **Optional dependencies**: Heavy dependencies are no longer imported at package level—they load only when needed

.. mermaid:: /diagrams/user_guide/getting_started/migration_v3_v4_diagram_1.mmd

Package Structure Changes
-------------------------

The most visible change is the reorganization of imports.

Before (V3):

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

After (V4):

.. code-block:: python

   from openstef_models.data_classes.prediction_job import PredictionJobDataClass
   from openstef_models.pipeline.train_model import train_model_pipeline
   from openstef_models.pipeline.create_forecast import create_forecast_pipeline

The general rule: replace the ``openstef`` prefix with the appropriate sub-package name. The primary sub-packages in V4 are:

- ``openstef_models`` — Core ML models, pipelines, data classes, and feature engineering
- ``openstef_models.integrations`` — MLflow, Optuna, and Joblib integrations
- ``openstef_models.explainability`` — Model explainability utilities

Integrations Module
^^^^^^^^^^^^^^^^^^^

External system integrations are now isolated and lazily loaded to avoid import errors when optional dependencies are not installed.

Before (V3):

.. code-block:: python

   # MLflow tracking was tightly coupled
   from openstef.pipeline.train_model import train_model_pipeline

   train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):

.. code-block:: python

   from openstef_models.pipeline.train_model import train_model_pipeline
   from openstef_models.integrations.mlflow import MLFlowStorageCallback

   mlflow_callback = MLFlowStorageCallback(
       tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   train_model_pipeline(
       pj,
       train_data,
       callbacks=[mlflow_callback],
   )

Quantile Specification
----------------------

V3 allowed quantiles to be specified as either integers (percentages) or floats (fractions), which caused confusion. V4 standardizes on float fractions (0.0–1.0).

Before (V3):

.. code-block:: python

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],  # Integer percentages
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

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],  # Float fractions (0-1)
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
   )

.. warning::

   Passing integer quantiles (e.g., ``50`` instead of ``0.5``) in V4 will raise a ``ValueError``. Update all prediction job definitions before migrating.

Note that ``default_modelspecs`` and ``save_train_forecasts`` fields have been removed from the ``PredictionJobDataClass`` in V4. Model specifications are now handled through dedicated configuration objects.

Removed and Renamed Parameters
-------------------------------

Several parameters have been removed or renamed across the pipeline functions:

+-------------------------------+-----------------------------------+-------------------------------------------+
| V3 Parameter                  | V4 Equivalent                     | Notes                                     |
+===============================+===================================+===========================================+
| ``check_old_model_age``       | ``model_age_check``               | Renamed for clarity                       |
+-------------------------------+-----------------------------------+-------------------------------------------+
| ``mlflow_tracking_uri``       | ``MLFlowStorageCallback``         | Moved to callback object                  |
+-------------------------------+-----------------------------------+-------------------------------------------+
| ``artifact_folder``           | ``MLFlowStorageCallback``         | Moved to callback object                  |
+-------------------------------+-----------------------------------+-------------------------------------------+
| ``default_modelspecs``        | Removed                           | Use model configuration instead           |
+-------------------------------+-----------------------------------+-------------------------------------------+
| ``save_train_forecasts``      | Removed                           | Controlled via callbacks                  |
+-------------------------------+-----------------------------------+-------------------------------------------+

Step-by-Step Migration Workflow
-------------------------------

Follow these steps to migrate your V3 codebase:

1. **Update package installation**

   .. code-block:: bash

      pip uninstall openstef
      pip install openstef-models

   If you use integrations, install with extras:

   .. code-block:: bash

      pip install openstef-models[mlflow,optuna]

2. **Update imports**

   Search and replace across your codebase:

   .. code-block:: bash

      # Find all V3 imports
      grep -r "from openstef\." --include="*.py" .

   Replace ``from openstef.`` with ``from openstef_models.`` for most modules.

3. **Update quantile definitions**

   Convert integer quantiles to float fractions:

   .. code-block:: python

      # Quick conversion helper
      v3_quantiles = [10, 30, 50, 70, 90]
      v4_quantiles = [q / 100.0 for q in v3_quantiles]
      # Result: [0.1, 0.3, 0.5, 0.7, 0.9]

4. **Refactor integration parameters**

   Move MLflow and storage parameters from pipeline function arguments into dedicated callback objects.

5. **Remove deprecated fields from PredictionJobDataClass**

   Remove ``default_modelspecs`` and ``save_train_forecasts`` from your prediction job definitions.

6. **Run tests**

   Execute your test suite and fix any remaining import or parameter errors.

Complete Before/After Example
-----------------------------

Here is a full training and forecasting workflow in both versions:

Before (V3):

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Define prediction job
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

   # Load and split data
   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   # Train
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   # Forecast
   forecast_data = input_data.iloc[-200:, :]
   forecast = create_forecast_pipeline(
       pj,
       forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

After (V4):

.. code-block:: python

   import pandas as pd
   from openstef_models.data_classes.prediction_job import PredictionJobDataClass
   from openstef_models.pipeline.train_model import train_model_pipeline
   from openstef_models.pipeline.create_forecast import create_forecast_pipeline
   from openstef_models.integrations.mlflow import MLFlowStorageCallback

   # Define prediction job
   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
   )

   # Configure integrations separately
   mlflow_callback = MLFlowStorageCallback(
       tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   # Load and split data
   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   # Train
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       model_age_check=False,
       callbacks=[mlflow_callback],
   )

   # Forecast
   forecast_data = input_data.iloc[-200:, :]
   forecast = create_forecast_pipeline(
       pj,
       forecast_data,
       callbacks=[mlflow_callback],
   )

.. mermaid:: /diagrams/user_guide/getting_started/migration_v3_v4_diagram_2.mmd

Troubleshooting Common Issues
-----------------------------

**ImportError: No module named 'openstef'**
   You have uninstalled V3 but haven't updated your imports yet. Replace ``openstef`` with ``openstef_models`` in your import statements.

**ValueError: Quantiles must be between 0 and 1**
   You are passing integer quantiles (V3 style). Divide by 100 to convert to float fractions.

**ModuleNotFoundError: No module named 'mlflow'**
   Install the MLflow extra: ``pip install openstef-models[mlflow]``. V4 does not import optional dependencies unless explicitly installed.

**TypeError: unexpected keyword argument 'check_old_model_age'**
   This parameter was renamed to ``model_age_check`` in V4.

Next Steps
----------

- See :doc:`installation` for detailed V4 installation instructions
- See :doc:`first_forecast` for a complete V4 forecasting tutorial
- Consult the API reference for full details on the new package structure