Architecture
============

OpenSTEF V4 introduces a fundamentally new modular architecture that transforms the library from a monolithic package into a composable ecosystem of specialized components. This architectural evolution enables greater flexibility, better maintainability, and easier integration into diverse deployment scenarios while preserving the performance and domain expertise that makes OpenSTEF effective for short-term energy forecasting.

System Overview
---------------

OpenSTEF V4 is structured as a **modular mono-repo** containing multiple self-contained packages that work together to provide comprehensive forecasting capabilities. Each package serves a specific purpose and can be used independently or combined with others to create complete forecasting solutions.

.. note::
   The diagrams below use placeholder directives that will be replaced with actual Sia-style architecture diagrams in future documentation updates.

.. diagram:: repo_level_architecture
   :type: sia
   :caption: Repository-level architecture showing how mono-repo components interact
   :reference: FOSDEM 2026 presentation slide

The architecture follows five core design principles that guide all development decisions:

**Modularity First**
   Components work in isolation and compose easily into larger systems. Each package has clear boundaries and well-defined interfaces.

**Type Safety**
   Full type safety throughout the codebase catches bugs early and improves maintainability during development and integration.

**Extensibility**
   Clear interfaces enable adding custom models, transforms, and metrics without modifying core library code.

**Performance**
   Efficient implementations optimized for production use cases maintain OpenSTEF's reputation for speed and accuracy.

**Unopinionated Design**
   The library provides powerful defaults while remaining flexible enough to support diverse use cases beyond its original domain.

Core Package Architecture
-------------------------

The V4 architecture consists of five primary packages, each with distinct responsibilities and clear interaction patterns.

OpenSTEF-Core
^^^^^^^^^^^^^

The foundation package provides shared data types, interfaces, and base classes used throughout the ecosystem. This package establishes the common vocabulary and contracts that enable other packages to work together seamlessly.

.. diagram:: core_architecture
   :type: sia
   :caption: OpenSTEF-Core internal architecture and interfaces
   :reference: Community meeting presentation

**Key Components:**
- Data types and schemas for forecasting workflows
- Base classes for models, transformers, and evaluators  
- Shared exceptions and error handling utilities
- Testing utilities and fixtures for package development

OpenSTEF-Models
^^^^^^^^^^^^^^^

The primary forecasting package contains model-agnostic implementations of machine learning pipelines, data preprocessing, and energy-specific transformations. This package provides the core forecasting functionality most users interact with directly.

**Key Components:**
- Forecasting models with consistent interfaces
- Data preprocessing and validation pipelines
- Energy domain transformations (solar radiation, temperature effects)
- Explainability features for model interpretation
- Preset configurations for common use cases

OpenSTEF-Meta
^^^^^^^^^^^^^

The meta-learning package implements advanced ensemble models and modern architectures that combine multiple forecasting approaches for improved accuracy and robustness.

.. diagram:: meta_architecture
   :type: sia
   :caption: OpenSTEF-Meta component architecture
   :reference: Community meeting Sia diagram

**Key Components:**
- Ensemble model architectures
- Meta-learning algorithms for model combination
- Advanced feature selection and engineering
- Multi-model coordination and optimization

OpenSTEF-Beam
^^^^^^^^^^^^^

The backtesting, evaluation, analysis, and metrics package provides comprehensive tools for assessing forecast quality and comparing model performance. Originally developed as an internal Alliander project, this package answers the critical question: "Are my model changes significant?"

**Key Components:**
- Backtesting frameworks with realistic constraints
- Statistical significance testing for model comparisons
- Comprehensive evaluation metrics for energy forecasting
- Regression testing against established benchmarks
- Performance analysis and reporting tools

Integration Patterns
--------------------

The modular architecture supports three primary integration patterns, each optimized for different deployment scenarios and user requirements.

Pipeline Integration
^^^^^^^^^^^^^^^^^^^

For users who need direct control over data flow and processing, the pipeline integration pattern provides fine-grained access to individual components. This approach requires manual data management but offers maximum flexibility.

.. code-block:: python

   from openstef.models import ForecastingPipeline
   from openstef.core import PredictionJob
   
   # Direct pipeline usage with manual data handling
   pipeline = ForecastingPipeline(config=job_config)
   forecast = pipeline.predict(input_data)

Task Integration
^^^^^^^^^^^^^^^

The task integration pattern provides higher-level abstractions that handle data retrieval, processing, and storage automatically. This approach simplifies integration for users who want OpenSTEF to manage the complete forecasting workflow.

.. code-block:: python

   from openstef.tasks import TrainingTask, ForecastingTask
   
   # Task-based integration with automatic data handling
   training_task = TrainingTask(prediction_job)
   model = training_task.run()
   
   forecasting_task = ForecastingTask(prediction_job, model)
   results = forecasting_task.run()

Component Integration
^^^^^^^^^^^^^^^^^^^^

For advanced users building custom solutions, individual components can be composed into specialized workflows that combine OpenSTEF capabilities with external systems and custom logic.

.. code-block:: python

   from openstef.core import BaseModel
   from openstef.models import FeatureEngineer
   from openstef.beam import ModelEvaluator
   
   # Custom composition of individual components
   feature_engineer = FeatureEngineer(config)
   processed_data = feature_engineer.transform(raw_data)
   
   model = CustomModel()  # Your implementation
   evaluator = ModelEvaluator(metrics=['rmse', 'mape'])

Data Flow Architecture
---------------------

The V4 architecture implements a clear data flow pattern that separates concerns while maintaining performance. Data moves through well-defined stages, each handled by specialized components with clear input and output contracts.

**Input Stage**
   Raw time series data, weather forecasts, and configuration parameters enter the system through standardized interfaces defined in OpenSTEF-Core.

**Processing Stage**
   Feature engineering, data validation, and preprocessing transform raw inputs into model-ready datasets using components from OpenSTEF-Models.

**Modeling Stage**
   Training, forecasting, or evaluation operations execute using model implementations that can range from simple presets to complex meta-learning ensembles.

**Output Stage**
   Results flow through evaluation and post-processing components before being returned in standardized formats or written to external systems.

This architecture ensures that data transformations are reproducible, components remain testable in isolation, and the system can scale from research notebooks to production deployments without requiring architectural changes.

Migration and Compatibility
---------------------------

The V4 architecture represents a significant evolution from previous versions, introducing breaking changes that enable the new modular design. However, the migration path is designed to be straightforward for most use cases.

.. warning::
   OpenSTEF V4 introduces breaking changes from V3. Review the :doc:`../guides/how_to_guides` for detailed migration instructions.

**Key Changes:**
- Package structure reorganized into specialized modules
- Configuration format updated for improved flexibility
- Some API endpoints renamed for consistency
- Enhanced type safety may require code updates

**Migration Benefits:**
- Improved performance through optimized component interactions
- Better extensibility for custom use cases
- Enhanced testing and debugging capabilities
- Clearer separation of concerns for easier maintenance

For detailed migration guidance, see the :doc:`../guides/how_to_guides` section, which includes step-by-step instructions and common migration patterns based on feedback from early adopters.