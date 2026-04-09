Migrating from V3 to V4
=======================

OpenSTEF V4 represents a major architectural overhaul that modernizes the codebase, improves modularity, and enhances type safety. This guide walks you through the breaking changes and provides practical migration steps with before/after code examples.

Overview of Changes
-------------------

V4 introduces several fundamental changes:

- **Package restructure**: Monolithic package split into specialized modules (``openstef-core``, ``openstef-models``, ``openstef-beam``)
- **API modernization**: Simplified pipeline interfaces with stronger typing
- **Data classes**: Dictionary-based configurations replaced with typed data classes
- **Pipeline consolidation**: Tasks removed in favor of direct pipeline usage
- **Type safety**: Comprehensive type hints throughout the codebase

The migration requires code changes but provides clearer APIs, better IDE support, and improved maintainability.

Package Structure Changes
-------------------------

V3 used a single ``openstef`` package containing all functionality. V4 splits this into specialized packages:

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.tasks import train_model_task

**After (V4):**

.. code-block:: python

   # Core utilities and types
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile
   
   # Models and pipelines
   from openstef_models.pipelines.training import TrainingPipeline
   from openstef_models.pipelines.backtest import BacktestPipeline
   
   # Evaluation and metrics
   from openstef_beam.pipelines.evaluation import EvaluationPipeline
   from openstef_beam.metrics import MetricProvider

For most users, installing the ``openstef`` meta-package provides all core components:

.. code-block:: bash

   pip install openstef

This installs ``openstef-core`` and ``openstef-models`` by default. Install ``openstef-beam`` separately if you need backtesting and evaluation:

.. code-block:: bash

   pip install openstef-beam

Prediction Job Configuration
-----------------------------

V3 used dictionary-based prediction jobs that were converted to ``PredictionJobDataClass``. V4 uses strongly-typed configuration classes with validation.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Define prediction job as dictionary
   pj = dict(
       id=287,
       model='xgb',
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
       default_modelspecs=None,
       save_train_forecasts=True,
   )
   pj = PredictionJobDataClass(**pj)

**After (V4):**

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.configs import ModelConfig
   
   # Use typed configuration directly
   config = ModelConfig(
       model_type="xgb",
       quantiles=[Quantile(q) for q in [0.1, 0.3, 0.5, 0.7, 0.9]],
       horizon=timedelta(hours=47),
       resolution=timedelta(minutes=15),
       hyperparameters={},
   )

Key changes:

- Quantiles now use ``Quantile`` type (0.0-1.0 range) instead of percentages
- Time durations use ``timedelta`` objects instead of minutes
- Configuration separated from job metadata (ID, name, location)
- Explicit type validation at construction time

Training Pipeline
-----------------

The training pipeline interface has been simplified and modernized in V4.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Load data
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = input_data.iloc[:-200, :]
   
   # Define prediction job
   pj = PredictionJobDataClass(**{
       'id': 287,
       'model': 'xgb',
       'quantiles': [10, 30, 50, 70, 90],
       'forecast_type': 'demand',
       'horizon_minutes': 2820,
       'resolution_minutes': 15,
   })
   
   # Train model
   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts"
   )

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile
   from openstef_models.pipelines.training import TrainingPipeline
   from openstef_models.configs import ModelConfig
   
   # Load data into TimeSeriesDataset
   dataset = TimeSeriesDataset.from_dataframe(
       df=pd.read_csv('data.csv', index_col='index', parse_dates=True),
       target_column='load',
   )
   
   # Configure model
   config = ModelConfig(
       model_type="xgb",
       quantiles=[Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.7), Quantile(0.9)],
       horizon=timedelta(hours=47),
       resolution=timedelta(minutes=15),
   )
   
   # Train model
   pipeline = TrainingPipeline(config=config)
   result = pipeline.run(data=dataset)
   
   # Access trained forecaster
   forecaster = result.forecaster

Key changes:

- Data passed as ``TimeSeriesDataset`` instead of raw DataFrame
- Configuration uses ``ModelConfig`` instead of ``PredictionJobDataClass``
- Pipeline instantiated as object with ``run()`` method
- Returns structured ``TrainingResult`` instead of tuple
- MLflow integration handled separately (see deployment guide)

Forecasting Pipeline
--------------------

Creating forecasts follows a similar pattern to training.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Create forecast using prediction job
   forecast = create_forecast_pipeline(
       pj,
       input_data=forecast_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models"
   )

**After (V4):**

.. code-block:: python

   from openstef_models.forecasters import load_forecaster
   
   # Load trained forecaster
   forecaster = load_forecaster(path="./models/forecaster.pkl")
   
   # Create forecast
   forecast = forecaster.predict(
       predictors=forecast_dataset,
       horizon=timedelta(hours=47),
   )

The V4 approach separates model persistence from prediction. Train and save models explicitly, then load them for inference.

Backtesting and Evaluation
---------------------------

V4 moves backtesting and evaluation to the dedicated ``openstef-beam`` package with more flexible configuration.

**Before (V3):**

.. code-block:: python

   # V3 had limited built-in backtesting
   # Often required custom implementation

**After (V4):**

.. code-block:: python

   from datetime import datetime
   from openstef_beam.pipelines.backtest import BacktestPipeline
   from openstef_beam.pipelines.evaluation import EvaluationPipeline
   from openstef_beam.configs import BacktestConfig, EvaluationConfig
   from openstef_beam.metrics import MetricProvider
   
   # Configure backtest
   backtest_config = BacktestConfig(
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       step=timedelta(days=1),
   )
   
   # Run backtest
   backtest_pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )
   predictions = backtest_pipeline.run(
       ground_truth=measurements,
       predictors=weather_data,
   )
   
   # Evaluate results
   evaluation_config = EvaluationConfig()
   evaluation_pipeline = EvaluationPipeline(
       config=evaluation_config,
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       window_metric_providers=[MetricProvider()],
       global_metric_providers=[MetricProvider()],
   )
   report = evaluation_pipeline.run(
       ground_truth=measurements,
       predictions=predictions,
   )

V4 provides comprehensive backtesting and evaluation capabilities with configurable metrics, time windows, and lead times.

Tasks Removed
-------------

V3 included task functions that handled database I/O alongside pipeline logic. V4 removes tasks entirely—use pipelines directly and handle data integration separately.

**Before (V3):**

.. code-block:: python

   from openstef.tasks import train_model_task
   
   # Task handled database reads/writes
   train_model_task(pj_id=287, context=db_context)

**After (V4):**

.. code-block:: python

   # Handle data integration yourself
   from your_data_layer import load_training_data, save_model
   
   # Load data
   dataset = load_training_data(target_id=287)
   
   # Train using pipeline
   pipeline = TrainingPipeline(config=config)
   result = pipeline.run(data=dataset)
   
   # Save model
   save_model(result.forecaster, target_id=287)

This separation improves testability and allows flexible data integration. See the :doc:`data_integration` guide for patterns on connecting to various data sources.

Type Hints and Validation
--------------------------

V4 adds comprehensive type hints throughout the codebase. This enables better IDE support, earlier error detection, and clearer APIs.

**Before (V3):**

.. code-block:: python

   def train_model_pipeline(pj, input_data, **kwargs):
       # Types unclear from signature
       pass

**After (V4):**

.. code-block:: python

   def run(
       self,
       data: TimeSeriesDataset,
       validation_split: float = 0.2,
   ) -> TrainingResult:
       """Train forecaster with explicit types."""
       pass

Use type checkers like ``mypy`` or ``pyright`` to catch type errors during development:

.. code-block:: bash

   mypy your_code.py
   pyright your_code.py

Migration Workflow
------------------

Follow these steps to migrate your V3 code to V4:

1. **Update dependencies**: Install V4 packages

   .. code-block:: bash

      pip install --upgrade openstef openstef-beam

2. **Update imports**: Change package imports to new structure

3. **Convert prediction jobs**: Replace dictionaries with typed configs

4. **Update data handling**: Wrap DataFrames in ``TimeSeriesDataset``

5. **Refactor pipelines**: Use new pipeline interfaces with ``run()`` methods

6. **Remove task usage**: Replace tasks with direct pipeline calls

7. **Add type hints**: Annotate your own functions for consistency

8. **Test thoroughly**: V4's validation catches errors earlier—fix any that surface

Backward Compatibility
----------------------

V4 is not backward compatible with V3. The ``openstef-compatibility`` package (coming soon) will provide migration helpers for gradual transitions.

For now, plan for a complete migration. The architectural improvements justify the effort:

- Clearer separation of concerns
- Better testability
- Improved type safety
- More flexible data integration
- Enhanced evaluation capabilities

Next Steps
----------

- Review the :doc:`use_cases` guide for complete V4 examples
- Check :doc:`data_integration` for connecting to your data sources
- See :doc:`deployment` for production deployment patterns
- Explore the API reference for detailed class documentation

If you encounter migration challenges, consult the community forum or open an issue on GitHub.