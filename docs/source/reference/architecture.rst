Architecture
============

OpenSTEF V4 introduces a modular architecture designed for flexibility, extensibility, and enterprise integration. This page explains the structural design of the OpenSTEF library at multiple levels, from the overall mono-repository organization to detailed component interactions.

Repository-Level Architecture
------------------------------

OpenSTEF V4 is structured as a modular mono-repository containing multiple self-contained packages that work together to provide comprehensive short-term energy forecasting capabilities.

.. note::
   [DIAGRAM: Repository-level Sia-style diagram showing the mono-repo structure with five core packages (openstef-core, openstef-models, openstef-meta, openstef-beam, openstef-deploy) and their high-level relationships. Reference: FOSDEM 2026 presentation slide showing package dependencies and data flow.]

The mono-repository approach provides several advantages:

- **Unified versioning**: All components are released together, ensuring compatibility
- **Shared development**: Common tooling, testing, and CI/CD across all packages
- **Simplified dependency management**: Internal dependencies are clearly defined
- **Coordinated evolution**: Breaking changes can be managed across the entire ecosystem

Core Package Components
-----------------------

The OpenSTEF V4 architecture consists of five primary packages, each serving a specific purpose in the forecasting workflow:

openstef-core
^^^^^^^^^^^^^

The foundation package that provides shared infrastructure for all other components:

- **Data types and interfaces**: Common data structures and abstract base classes
- **Shared exceptions**: Standardized error handling across the library
- **Testing utilities**: Common test fixtures and helper functions
- **Base configuration**: Core settings and validation logic

This package ensures consistency and interoperability across all OpenSTEF components.

openstef-models
^^^^^^^^^^^^^^^

The main forecasting engine containing model-agnostic machine learning capabilities:

- **Forecasting models**: Support for XGBoost, LightGBM, and other ML algorithms
- **Data preprocessing pipelines**: Standardized data cleaning and preparation
- **Energy-specific transformations**: Domain knowledge for energy forecasting
- **Explainability features**: Model interpretation and feature importance
- **Presets for quick start**: Pre-configured setups for common use cases

openstef-meta
^^^^^^^^^^^^^

Advanced meta-learning capabilities for ensemble modeling and modern architectures:

- **Modern ensemble models**: Sophisticated model combination strategies
- **Advanced model architectures**: State-of-the-art forecasting approaches
- **Automated model selection**: Intelligent choice of optimal models

.. note::
   [DIAGRAM: Component-level Sia-style diagram for openstef-meta showing the meta-learning pipeline, ensemble strategies, and model selection process. Reference: Community meeting presentation showing meta-learning architecture.]

openstef-beam
^^^^^^^^^^^^^

Backtesting, Evaluation, Analysis, and Metrics package for rigorous model validation:

- **Regression testing**: Automated benchmarking against reference models
- **Statistical significance testing**: Determine if model changes are meaningful
- **Performance analysis**: Comprehensive evaluation metrics and reporting
- **Benchmark comparisons**: Standardized evaluation against industry baselines

This package originated from internal Alliander projects and provides production-grade evaluation capabilities.

openstef-deploy
^^^^^^^^^^^^^^^

Deployment and orchestration tools for production environments:

- **Container orchestration**: Docker and Kubernetes deployment templates
- **Pipeline orchestration**: Integration with Dagster, Airflow, and other workflow engines
- **Monitoring and alerting**: Production monitoring capabilities
- **Reference implementations**: Complete deployment examples

Component Interaction Patterns
-------------------------------

The OpenSTEF architecture follows clear interaction patterns that promote modularity while enabling sophisticated forecasting workflows.

Pipeline-Based Workflow
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF organizes functionality around pipelines that can be composed and customized:

.. code-block:: python

   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes import PredictionJobDataClass
   
   # Configure prediction job
   job = PredictionJobDataClass(
       name="substation_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Train model using pipeline
   model = train_model(job, training_data)
   
   # Generate forecast
   forecast = create_forecast(job, model, input_data)

.. note::
   [DIAGRAM: Pipeline interaction diagram showing the flow from PredictionJob configuration through data validation, feature engineering, model training/inference, and post-processing. Show how components from different packages collaborate.]

Task vs Pipeline Abstraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides two levels of abstraction for different use cases:

- **Tasks**: High-level operations that handle data retrieval and storage automatically
- **Pipelines**: Lower-level operations that work with provided data directly

This dual approach supports both quick prototyping and custom integration scenarios.

Data Flow Architecture
^^^^^^^^^^^^^^^^^^^^^^

The modular design enables flexible data flow patterns:

1. **Data ingestion**: Flexible input from various sources (databases, files, APIs)
2. **Validation**: Standardized data quality checks using openstef-core
3. **Feature engineering**: Energy-specific transformations from openstef-models
4. **Model training/inference**: Algorithm-agnostic processing
5. **Evaluation**: Comprehensive analysis using openstef-beam
6. **Post-processing**: Results formatting and uncertainty quantification

.. note::
   [DIAGRAM: Data flow diagram showing how data moves through the OpenSTEF components, with clear interfaces between packages and optional customization points for enterprise integration.]

Extensibility and Customization
--------------------------------

The modular architecture supports extensive customization without modifying core components:

Custom Model Integration
^^^^^^^^^^^^^^^^^^^^^^^^

New forecasting algorithms can be integrated by implementing standard interfaces:

.. code-block:: python

   from openstef.model.basecase import BaseModel
   
   class CustomForecastModel(BaseModel):
       def fit(self, X, y):
           # Custom training logic
           pass
       
       def predict(self, X):
           # Custom prediction logic
           pass

Custom Feature Engineering
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Domain-specific feature engineering can be added through the feature applicator system:

.. code-block:: python

   from openstef.feature_engineering import FeatureAdder
   
   class CustomFeatureAdder(FeatureAdder):
       def add_features(self, data, prediction_job):
           # Custom feature engineering logic
           return enhanced_data

Enterprise Integration Points
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The V4 architecture provides clear integration points for enterprise environments:

- **Custom data connectors**: Pluggable data source adapters
- **Authentication and authorization**: Configurable security layers
- **Monitoring hooks**: Integration with enterprise monitoring systems
- **Custom deployment patterns**: Flexible orchestration options

This modular design ensures that OpenSTEF can be adapted to diverse organizational requirements while maintaining the core forecasting capabilities that make it effective for short-term energy forecasting applications.