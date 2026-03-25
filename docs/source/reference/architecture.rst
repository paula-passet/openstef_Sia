Architecture Overview
=====================


OpenSTEF Library Architecture
-----------------------------


OpenSTEF is a comprehensive machine learning library ecosystem designed specifically for short-term energy forecasting, not a standalone application. As a Python library, OpenSTEF provides the core forecasting algorithms, data preprocessing pipelines, and model evaluation tools that form the foundation for building energy forecasting solutions. The ecosystem consists of multiple interconnected packages including the main OpenSTEF library for machine learning functionality, OpenSTEF-dbc for database connectivity, OpenSTEF-reference for complete stack deployment, and OpenSTEF-offline-example for educational notebooks. To deploy OpenSTEF as a complete forecasting application, organizations must integrate it with additional components such as data fetchers, APIs, and scheduling systems that handle the operational aspects of running forecasts in production environments. This modular approach allows OpenSTEF to remain focused on its core strength—delivering high-quality machine learning models for energy forecasting—while providing the flexibility for integration into diverse technical architectures and business requirements.


This architecture documentation provides a comprehensive overview of OpenSTEF's modular library design and how its components work together to deliver short-term energy forecasting capabilities. As a Python library ecosystem, OpenSTEF is built with flexibility and integration in mind, allowing users to understand how to effectively incorporate its forecasting functionality into their own systems and workflows. The following sections detail the core architectural principles, component relationships, and integration patterns that make OpenSTEF suitable for everything from simple standalone forecasting tasks to complex enterprise energy management systems. Understanding this architecture will help you determine which components you need for your specific use case and how to structure your implementation for optimal performance and maintainability.


.. note::

   OpenSTEF is a Python library, not a standalone application. To use OpenSTEF in production, you must integrate it into your own applications and infrastructure. This typically requires building additional components such as data fetchers, APIs, and orchestration services around the core OpenSTEF library. The reference implementation and examples provided in the OpenSTEF ecosystem demonstrate how to structure such integrations.


Repository-Level Architecture
-----------------------------


OpenSTEF V4 is structured as a modular monorepo containing multiple self-contained packages that work together to provide a comprehensive machine learning library for energy forecasting. The architecture follows key design principles of remaining unopinionated, supporting various data availability constraints, and maintaining high performance while leveraging existing proven technologies. The monorepo structure enables better code organization, shared dependencies, and coordinated releases across all components while allowing each module to serve specific purposes within the overall forecasting ecosystem.


.. [DIAGRAM: Repository-level architecture showing how openstef, openstef-dbc, and other components interact within the monorepo]


The OpenSTEF ecosystem consists of several interconnected components that work together to provide a comprehensive forecasting solution. At the foundation lies **openstef-core**, which provides the essential data types, interfaces, and base classes that all other modules depend on. The **openstef-models** package contains the actual forecasting models and preprocessing pipelines, offering energy-specific transformations and explainability features along with presets for quick implementation. **openstef-meta** extends the modeling capabilities with modern ensemble models and advanced architectures for meta-learning scenarios. The **openstef-beam** package handles backtesting, evaluation, analysis, and metrics, enabling rigorous testing of model changes and regression testing against benchmarks. Supporting the core library are specialized repositories: **OpenSTEF-dbc** provides database connectivity for company-specific integrations, **OpenSTEF-reference** offers a complete deployable stack including databases and UI for reference implementations, and **OpenSTEF-offline-example** contains Jupyter notebooks demonstrating practical usage patterns. This modular architecture allows users to adopt components incrementally based on their specific needs while maintaining the library's unopinionated design philosophy.


- **openstef-core** - Foundation module containing data types, interfaces, base classes, shared exceptions, and testing utilities that serve as the building blocks for all other OpenSTEF components

- **openstef-models** - Core forecasting module with model-agnostic machine learning models, data preprocessing pipelines, energy-specific transformations, explainability features, and presets for quick deployment

- **openstef-meta** - Meta-learning module providing modern ensemble models and advanced model architectures for enhanced forecasting performance

- **openstef-beam** - Backtesting, Evaluation, Analysis, and Metrics module that enables regression testing against benchmarks and helps determine statistical significance of model changes

- **openstef-dbc** - Database connector module providing company-specific database integration capabilities for the OpenSTEF library

- **openstef-reference** - Complete reference implementation that deploys the entire OpenSTEF stack including data models, databases, and user interface components

- **openstef-offline-example** - Educational module containing Jupyter Notebooks that demonstrate OpenSTEF functionality and show how to apply the library to specific use cases


Core Library Components
-----------------------


The OpenSTEF library is architected as a modular system with clearly separated concerns, designed to provide flexible and reusable components for short-term energy forecasting. At its foundation lies the core module structure that emphasizes unopinionated design principles, allowing the library to adapt to various use cases while maintaining high performance and model quality. The architecture follows a modular mono-repo approach with multiple self-contained packages, each serving specific aspects of the forecasting workflow. The core functionality is organized around key modules including data classes for structured data handling, feature engineering components for data preprocessing and transformation, model implementations with confidence interval support, comprehensive metrics and evaluation tools, and flexible pipeline orchestration. This modular design enables users to leverage individual components as needed while providing complete pipeline solutions for common forecasting scenarios, making OpenSTEF both a comprehensive forecasting framework and a collection of specialized tools that can be integrated into existing machine learning workflows.


.. [DIAGRAM: Core library architecture showing modules like model training, forecasting, feature engineering, and data handling]


Data flows through OpenSTEF's core components following a structured pipeline architecture designed for energy forecasting workflows. Raw input data enters through the data preparation modules in `openstef.feature_engineering`, where it undergoes preprocessing, feature extraction, and transformation specific to energy forecasting requirements. The processed data then flows to the model training and prediction components in `openstef.model`, which handle machine learning operations including basecase generation, confidence interval calculation, and forecast creation. Throughout this flow, the `openstef.data_classes` module provides standardized data structures like PredictionJob and ModelSpecifications that ensure consistent data representation between components. The pipeline modules in `openstef.pipeline` orchestrate this entire flow, coordinating between feature engineering, model training, and forecast generation while maintaining data integrity and enabling both real-time forecasting and backtesting workflows. Logging and metrics collection occur continuously throughout the data flow via the `openstef.logging` and `openstef.metrics` modules, providing visibility into the forecasting process and enabling performance evaluation at each stage.


- **Model Training Pipeline** - Core training functionality through `openstef.pipeline.train_model` with support for hyperparameter optimization via `openstef.pipeline.optimize_hyperparameters`, providing automated model selection and tuning capabilities

- **Forecasting Engine** - Comprehensive forecasting pipelines including `openstef.pipeline.create_forecast` for standard predictions, `openstef.pipeline.create_component_forecast` for component-level forecasting, and `openstef.pipeline.create_basecase_forecast` for baseline comparisons

- **Feature Engineering Framework** - Extensive feature processing capabilities in `openstef.feature_engineering` including cyclic features, lag features, rolling features, weather features, holiday features, and automated data preparation with missing values handling

- **Validation and Evaluation** - Built-in validation through `openstef.pipeline.train_create_forecast_backtest` for backtesting, comprehensive metrics in `openstef.metrics` for performance assessment, and confidence interval estimation via `openstef.model.confidence_interval_applicator`


Data Pipeline Architecture
--------------------------


OpenSTEF processes data through a structured pipeline architecture that transforms raw input data into actionable forecasts. The data flow begins with input configuration through prediction jobs, which define the parameters and requirements for specific forecasting tasks. Raw data, including weather data, energy load measurements, and price information, flows into the feature engineering component where relevant features are selected and new derived features are created based on the prediction job configuration. This processed data then moves through the machine learning pipeline, where models are trained or used for forecasting depending on the specified task. The trained models and their outputs are managed through the model storage component using MLFlow for persistence and retrieval. Finally, the post-processing stage combines forecast results with additional configuration information from the prediction job, potentially splitting composite forecasts into component forecasts for solar, wind, and energy usage. This entire workflow is orchestrated through OpenSTEF's pipeline system, which automates the typical machine learning activities and enables single-shot, multi-horizon forecasting capabilities.


.. [DIAGRAM: Data pipeline architecture showing input data, preprocessing, model training, forecasting, and output stages]


OpenSTEF's data pipeline architecture centers around four key transformation steps that process raw energy data into actionable forecasts. The **feature engineering** component transforms input data by selecting and creating relevant features based on prediction job configurations, such as generating historical load patterns from yesterday or last week's data. The **machine learning** layer performs model training, forecasting, and evaluation using algorithms like XGBoost quantile regression, with all operations configured through prediction job specifications. **Model storage** interfaces handle the persistence and retrieval of trained models using MLFlow, supporting various backends including local disk, databases, and cloud storage like AWS S3. Finally, the **post processing** component enriches forecast outputs by combining prediction results with additional metadata from prediction jobs and can decompose aggregate forecasts into component-specific predictions for solar, wind, and energy usage. These transformation steps are orchestrated through OpenSTEF's pipeline system, which provides a clean interface between data processing stages while maintaining flexibility for both automated task-based workflows and direct pipeline usage where users manage their own data I/O operations.


Integration Patterns
--------------------


OpenSTEF offers flexible integration patterns as a Python library, allowing organizations to incorporate forecasting capabilities into their existing systems. The most common pattern involves using OpenSTEF's pipelines directly, where you handle data fetching and storage yourself, giving you complete control over data sources and destinations. Alternatively, you can use OpenSTEF's tasks, which provide a higher-level interface that manages database interactions for you. For production deployments, organizations typically integrate OpenSTEF within a broader architecture that includes a data fetcher component to collect input data, a data API to serve information to applications, and a forecaster service that orchestrates OpenSTEF's training and prediction workflows. This modular approach allows OpenSTEF to fit seamlessly into existing data pipelines, whether deployed as containerized services in Kubernetes, scheduled batch jobs, or embedded within larger energy management applications.


.. [DIAGRAM: Integration architecture showing OpenSTEF library integrated with external data sources, schedulers, and output systems]


- Scheduled cron jobs for automated training and forecasting workflows in containerized environments like Kubernetes

- Workflow orchestrators such as Apache Airflow, Prefect, or Dagster for complex multi-step forecasting pipelines

- Cloud platforms including AWS, Azure, and Google Cloud Platform with native container orchestration services

- CI/CD pipelines for automated model retraining and deployment using GitHub Actions, GitLab CI, or Jenkins

- Data pipeline frameworks like Apache Beam or Spark for large-scale feature engineering and batch processing

- Microservices architectures with REST APIs for real-time forecast serving and model management

- Event-driven systems using message queues like Apache Kafka or RabbitMQ for streaming data processing

- Jupyter notebook environments for interactive development and experimentation workflows


.. note::

   OpenSTEF is a Python library that provides machine learning functionality for energy forecasting, not a complete application. To use OpenSTEF in production, you must build your own application layer around it. This includes creating components such as a data fetcher to retrieve input data, a data API to serve information, and a forecaster service to orchestrate OpenSTEF tasks and pipelines. You can choose to use OpenSTEF's high-level tasks (which handle database operations) or work directly with pipelines (requiring you to manage data fetching and storage yourself). The library focuses solely on the machine learning aspects of forecasting - all integration, scheduling, data management, and user interface components must be implemented separately.


Component Dependencies
----------------------


OpenSTEF's component architecture follows a modular dependency structure where the core library serves as the foundation for various specialized components. The main OpenSTEF package provides the core machine learning functionality and serves as a dependency for several optional components. OpenSTEF-dbc extends the core library by providing company-specific database connectors, while OpenSTEF-reference builds upon both to deliver a complete reference implementation including datamodels, databases, and user interface components. OpenSTEF-offline-example depends on the core library to provide practical Jupyter Notebook examples. When deploying OpenSTEF as a full application, additional custom components are required that depend on the core library: a Data Fetcher component for input data retrieval, a Data API for data access, and a Forecaster component for orchestrating OpenSTEF tasks and pipelines. This layered dependency structure allows users to adopt OpenSTEF incrementally, starting with the core library and adding components based on their specific requirements.


.. [DIAGRAM: Dependency diagram showing relationships between core library, database connector, and optional components]


OpenSTEF as a library has minimal required dependencies - primarily the core Python package itself for basic forecasting functionality. However, different use cases require different combinations of components. For basic forecasting tasks, only the core OpenSTEF library is needed along with your input data. For production deployments, you'll need to create additional components: a data fetcher to collect input data, a data API to serve data to applications, and a forecaster service to orchestrate OpenSTEF tasks. Optional components include OpenSTEF-dbc for database connectivity (useful for enterprise environments), OpenSTEF-reference for a complete reference implementation with UI and databases, and OpenSTEF-offline-example for learning and experimentation through Jupyter notebooks. The modular architecture allows you to implement only the components your specific use case requires, from simple standalone forecasting scripts to full-scale production systems with web interfaces and automated scheduling.


- pandas - Data manipulation and analysis library for handling time series data and feature engineering

- scikit-learn - Machine learning library providing algorithms for training and prediction models

- numpy - Numerical computing library for array operations and mathematical functions

- xgboost - Gradient boosting framework used as one of the core prediction algorithms

- lightgbm - Gradient boosting framework providing an alternative machine learning algorithm

- matplotlib - Plotting library for generating forecast visualizations and metrics charts

- seaborn - Statistical data visualization library built on matplotlib for enhanced plotting

- joblib - Library for efficient serialization and parallel processing of machine learning models

- scipy - Scientific computing library providing statistical functions and optimization tools

- holidays - Library for handling country-specific holidays in feature engineering

- requests - HTTP library for fetching external data sources like weather APIs

- pydantic - Data validation library for ensuring data integrity in prediction jobs and configurations


Extensibility Points
--------------------


OpenSTEF is designed as a modular and extensible forecasting library that allows users to customize and extend functionality according to their specific needs. The library follows a plugin-based architecture where core components can be replaced or enhanced through well-defined interfaces. This design philosophy enables organizations to integrate OpenSTEF into existing systems while maintaining the ability to customize data connectors, feature engineering pipelines, model implementations, and post-processing steps. The extensibility is demonstrated through companion packages like OpenSTEF-dbc for database connectivity and OpenSTEF-reference for complete stack deployment, showing how the core library can be extended without modifying its fundamental structure.


.. [DIAGRAM: Extensibility architecture showing custom feature engineering, model types, and data connectors]


- Custom machine learning models by extending the base model classes in openstef.model package

- Feature engineering pipelines through openstef.feature_engineering modules for domain-specific transformations

- Data source connectors by implementing custom database adapters similar to OpenSTEF-dbc

- Preprocessing and postprocessing workflows via openstef.preprocessing and openstef.postprocessing modules

- Pipeline components by extending openstef.pipeline modules for custom forecasting workflows

- Monitoring and metrics collection through openstef.monitoring and openstef.metrics interfaces

- Task orchestration by implementing custom tasks in the openstef.tasks framework


For detailed guidance on implementing custom components, refer to the how-to guides in the documentation. The "Creating Custom Models" guide walks through implementing new forecasting algorithms by extending the base model interfaces. The "Custom Feature Engineering" guide demonstrates how to create domain-specific feature transformers that integrate with OpenSTEF's feature pipeline. For database integration, consult the "Database Connectors" guide which shows how to implement custom data adapters following the patterns established in OpenSTEF-dbc. Additionally, the OpenSTEF-offline-example repository provides Jupyter notebooks with practical examples of extending OpenSTEF functionality for specific use cases.


