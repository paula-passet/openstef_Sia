Architecture
============

OpenSTEF V4 introduces a completely redesigned architecture built around modularity, extensibility, and clear separation of concerns. This page explains the overall system design and how the various components work together to deliver flexible short-term energy forecasting capabilities.

Overview
--------

OpenSTEF is structured as a **modular mono-repo** containing multiple self-contained packages that can be used independently or together. This architectural approach enables users to adopt only the components they need while maintaining the option to leverage the full forecasting stack.

.. note::
   [DIAGRAM: Repository-level architecture showing the mono-repo structure with core packages (openstef-core, openstef-models, openstef-meta, openstef-beam) and their relationships, similar to FOSDEM 2026 slide]

The architecture follows key design principles:

- **Modularity First**: Each component works in isolation and can be easily composed into larger systems
- **Type Safety**: Full type safety throughout the codebase to catch bugs early
- **Extensibility**: Clear interfaces for adding custom models, transforms, and metrics
- **Performance**: Efficient implementations optimized for production use cases

Core Packages
-------------

The V4 architecture consists of four primary packages, each with distinct responsibilities:

openstef-core
^^^^^^^^^^^^^

The foundation package that provides shared data types, interfaces, and base classes used by all other components. This package includes:

- Common data structures for forecasting workflows
- Base interfaces for models, transformers, and evaluators  
- Shared exceptions and testing utilities
- Type definitions and protocols

.. code-block:: python

   from openstef.core import ForecastRequest, ModelInterface
   from openstef.core.types import TimeSeriesData

openstef-models  
^^^^^^^^^^^^^^^

Contains the core forecasting functionality including models, preprocessing pipelines, and energy-specific transformations:

- Model-agnostic forecasting algorithms
- Data preprocessing and validation pipelines
- Energy-specific feature engineering
- Model explainability features
- Presets for common use cases

.. code-block:: python

   from openstef.models import XGBQuantileModel
   from openstef.models.preprocessing import EnergyDataPreprocessor
   from openstef.models.presets import get_congestion_preset

openstef-meta
^^^^^^^^^^^^^

Advanced meta-learning capabilities for ensemble models and sophisticated model architectures:

- Modern ensemble methods
- Advanced model architectures
- Meta-learning algorithms for model selection
- Automated hyperparameter optimization

.. note::
   [DIAGRAM: Component-level diagram for openstef-meta showing ensemble architecture and meta-learning flow, similar to Sia picture shown in community meetings]

openstef-beam
^^^^^^^^^^^^^

Backtesting, Evaluation, Analysis, and Metrics package that answers "Are my model changes significant?":

- Comprehensive backtesting frameworks
- Statistical significance testing
- Regression testing against benchmarks
- Advanced evaluation metrics for energy forecasting

.. code-block:: python

   from openstef.beam import BacktestRunner, SignificanceTest
   from openstef.beam.metrics import energy_specific_metrics

Component Interactions
----------------------

The modular design enables flexible component interaction patterns depending on your use case:

Simple Forecasting Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For basic forecasting, components interact in a linear pipeline:

.. code-block:: python

   # Using high-level presets
   from openstef.models.presets import get_transport_preset
   
   # Get preset configuration
   config = get_transport_preset()
   
   # Train and forecast
   model = config.model_class(**config.model_params)
   model.fit(train_data)
   forecast = model.predict(forecast_horizon)

Advanced Ensemble Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For sophisticated forecasting, multiple components work together:

.. code-block:: python

   # Combine multiple packages
   from openstef.models import XGBQuantileModel, LinearModel
   from openstef.meta import EnsembleModel
   from openstef.beam import BacktestRunner
   
   # Create ensemble
   base_models = [XGBQuantileModel(), LinearModel()]
   ensemble = EnsembleModel(base_models)
   
   # Validate with backtesting
   backtest = BacktestRunner(ensemble)
   results = backtest.run(historical_data)

.. note::
   [DIAGRAM: Component interaction flow showing data flow between packages for ensemble forecasting workflow]

Legacy Architecture Comparison
-------------------------------

OpenSTEF V3 used a monolithic architecture with tightly coupled components. The V4 modular design addresses several limitations:

**V3 Limitations:**
- Tight coupling between forecasting and database layers
- Hard-coded assumptions about data sources
- Limited extensibility for custom models
- Complex deployment requirements

**V4 Improvements:**
- Clear separation between library and integration concerns
- Flexible data interfaces supporting multiple sources
- Plugin architecture for custom components
- Simplified deployment with optional components

Migration Considerations
^^^^^^^^^^^^^^^^^^^^^^^^

When migrating from V3 to V4, the key architectural changes to consider:

- **Package Structure**: Import paths have changed to reflect the modular structure
- **Configuration**: Prediction jobs are now more flexible and type-safe
- **Data Interfaces**: New abstract interfaces replace database-specific implementations
- **Model Registration**: Models now use a plugin system instead of hard-coded registries

For detailed migration guidance, see the how-to guides section.

Extensibility Points
--------------------

The V4 architecture provides several well-defined extension points for customization:

Custom Models
^^^^^^^^^^^^^

Implement the ``ModelInterface`` from ``openstef-core`` to add new forecasting algorithms:

.. code-block:: python

   from openstef.core import ModelInterface
   
   class CustomModel(ModelInterface):
       def fit(self, data: TimeSeriesData) -> None:
           # Custom training logic
           pass
           
       def predict(self, horizon: int) -> ForecastResult:
           # Custom prediction logic
           pass

Custom Transformers
^^^^^^^^^^^^^^^^^^^

Add preprocessing steps by implementing transformer interfaces:

.. code-block:: python

   from openstef.core import TransformerInterface
   
   class CustomTransformer(TransformerInterface):
       def transform(self, data: TimeSeriesData) -> TimeSeriesData:
           # Custom transformation logic
           return transformed_data

Custom Metrics
^^^^^^^^^^^^^^

Extend evaluation capabilities with domain-specific metrics:

.. code-block:: python

   from openstef.beam import MetricInterface
   
   class CustomMetric(MetricInterface):
       def calculate(self, actual, predicted) -> float:
           # Custom metric calculation
           return metric_value

This modular architecture ensures that OpenSTEF V4 can adapt to diverse forecasting requirements while maintaining the performance and reliability needed for production energy systems.