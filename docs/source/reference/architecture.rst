Architecture
============

OpenSTEF V4 is designed as a modular Python machine learning library for short-term energy forecasting. This page provides architectural diagrams and explanations of how the mono-repo components fit together and interact to deliver flexible, production-ready forecasting capabilities.

.. note::
   [DIAGRAM: Repository-level architecture showing mono-repo structure with openstef-core, openstef-models, openstef-beam, and openstef-meta packages and their relationships]

Design Philosophy
-----------------

OpenSTEF V4 follows key architectural principles that distinguish it from monolithic forecasting applications:

**Modular Library Design**
   OpenSTEF remains a machine learning library, not a deployable application. Each component can be used independently or combined with others to build custom forecasting solutions.

**Unopinionated Architecture**
   The library provides flexible interfaces and presets for common use cases without forcing specific implementation patterns. Users can customize any component to match their requirements.

**Performance Without Compromise**
   All architectural decisions prioritize model quality and execution speed. The modular design enhances rather than hinders performance through optimized component interactions.

**Enterprise Integration Ready**
   The flexible architecture supports integration into complex software landscapes with custom APIs, data pipelines, and deployment patterns.

Mono-Repo Structure
--------------------

OpenSTEF V4 is organized as a modular mono-repo containing five self-contained packages that work together seamlessly:

.. note::
   [DIAGRAM: Component-level interaction diagram showing data flow between packages, with openstef-core as foundation, models and meta for ML capabilities, beam for evaluation, and reference for examples]

Core Foundation (`openstef-core`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The foundation package provides shared data types, interfaces, and utilities used by all other components:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseModel
   from openstef_core.exceptions import OpenSTEFError
   
   # Core data structures used across all packages
   dataset = TimeSeriesDataset(data=load_data, target_column="load")

**Key Components:**
- Data types and interfaces for consistent API contracts
- Shared exceptions and error handling
- Testing utilities and base classes
- Configuration management foundations

Machine Learning (`openstef-models`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The models package contains the core machine learning functionality for forecasting:

.. code-block:: python

   from openstef_models.models import XGBoostModel
   from openstef_models.transforms import WeatherTransform
   from openstef_models.explainability import ShapExplainer
   
   # Model-agnostic forecasting with built-in feature engineering
   model = XGBoostModel()
   transform = WeatherTransform()
   explainer = ShapExplainer(model)

**Key Components:**
- Model-agnostic forecasting implementations
- Energy-specific data preprocessing pipelines
- Feature engineering with domain knowledge
- Model explainability and interpretation tools
- Quick-start presets for common use cases

Advanced Models (`openstef-meta`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The meta-learning package provides modern ensemble models and advanced architectures:

.. code-block:: python

   from openstef_meta.ensemble import MetaEnsemble
   from openstef_meta.architectures import DeepForecastModel
   
   # Advanced ensemble and deep learning capabilities
   ensemble = MetaEnsemble(base_models=[model1, model2, model3])
   forecast = ensemble.predict(data)

**Key Components:**
- Meta-learning ensemble techniques
- Advanced model architectures
- Automated model selection strategies
- Performance optimization algorithms

Evaluation Framework (`openstef-beam`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BEAM (Backtesting, Evaluation, Analysis, Metrics) provides comprehensive model evaluation capabilities:

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner
   from openstef_beam.metrics import ForecastMetrics
   from openstef_beam.analysis import PerformanceAnalyzer
   
   # Comprehensive model evaluation and comparison
   backtest = BacktestRunner(model, historical_data)
   results = backtest.run()
   analyzer = PerformanceAnalyzer(results)

**Key Components:**
- Backtesting framework for historical validation
- Comprehensive forecasting metrics
- Performance analysis and visualization
- Model comparison and benchmarking tools
- Regression testing against performance benchmarks

Reference Implementation (`openstef-reference`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The reference package demonstrates complete deployment patterns and integration examples:

.. code-block:: python

   from openstef_reference.pipelines import StandardForecastPipeline
   from openstef_reference.deployment import CronJobDeployment
   
   # Production-ready deployment examples
   pipeline = StandardForecastPipeline(config)
   deployment = CronJobDeployment(pipeline)

**Key Components:**
- Complete forecasting pipeline implementations
- Integration examples with common data sources
- Deployment pattern demonstrations
- Configuration templates and best practices

Component Interactions
----------------------

The packages interact through well-defined interfaces that maintain modularity while enabling powerful combinations:

**Data Flow Architecture**
   Data flows from core datasets through model transforms to predictions, with BEAM providing continuous evaluation feedback loops.

**Plugin Architecture**
   Each package exposes extension points for custom implementations. Users can replace any component while maintaining compatibility with the rest of the system.

**Configuration Management**
   Centralized configuration flows from core through all packages, enabling consistent behavior while allowing component-specific customization.

.. note::
   [DIAGRAM: Data flow diagram showing typical forecasting workflow from raw data input through preprocessing, model training/prediction, to evaluation and deployment]

Integration Patterns
---------------------

OpenSTEF's modular architecture supports multiple integration patterns for different deployment scenarios:

**Research and Experimentation**
   Use individual packages in Jupyter notebooks with minimal setup. The modular design allows researchers to focus on specific aspects like model development or evaluation.

**Small-Scale Deployments**
   Combine packages using the reference implementations as starting points. Docker-compose examples demonstrate production-ready deployments with minimal infrastructure.

**Enterprise Integration**
   Integrate specific packages into existing MLOps pipelines. The unopinionated design allows OpenSTEF components to work within established enterprise architectures.

The architecture ensures that whether you need a single forecasting model or a complete evaluation framework, OpenSTEF provides the flexibility to use exactly what you need without unnecessary complexity.