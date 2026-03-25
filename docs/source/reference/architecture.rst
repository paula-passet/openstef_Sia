Architecture Overview
=====================


Repository Architecture
-----------------------


OpenSTEF is a Python library consisting of multiple interconnected components that work together to provide short-term energy forecasting capabilities. Rather than being a standalone application, it offers modular packages including data classes, feature engineering, model training, and pipeline orchestration that can be integrated into existing systems and workflows.


.. [DIAGRAM: Repository-level architecture showing core library, pipeline components, feature engineering, model selection, and data interfaces]


Core Pipeline Architecture
--------------------------


The OpenSTEF forecasting pipeline executes a structured workflow from raw data to predictions. The process begins with feature engineering, where the library selects and creates required features based on prediction job configuration, such as historical load patterns. Machine learning components then perform model training or forecasting using algorithms like XGBoost quantile models. Model storage handles trained model persistence through MLFlow integration, supporting local disk, database, or cloud storage. Finally, post-processing combines forecast results with configuration metadata and can decompose aggregate forecasts into component predictions for solar, wind, and energy usage.


.. [DIAGRAM: Pipeline flow diagram showing data ingestion → feature engineering → model training → prediction → output stages]


Component Interactions
----------------------


OpenSTEF's component interactions follow a structured data flow pattern where data providers supply raw time series data through standardized interfaces. The feature_engineering package processes this data using modules like data_preparation, lag_features, and weather_features, transforming raw inputs into model-ready datasets. Model trainers in the model package consume these engineered features through the model_creator and serializer interfaces.

The pipeline package orchestrates these interactions, with modules like train_model and create_forecast coordinating data flow between components. Data classes provide standardized containers like prediction_job and model_specifications that ensure consistent data exchange. The preprocessing and postprocessing packages handle data transformation at pipeline boundaries, while the monitoring package tracks performance metrics across component interactions.


.. [DIAGRAM: Component interaction diagram showing DataProvider, FeatureEngineer, ModelTrainer, Predictor and their relationships]


Extension Points
----------------


OpenSTEF provides several key extension points for customization. Users can implement custom data sources through the database connector interface (OpenSTEF-dbc), extend feature engineering via the feature_engineering.apply_features module, and integrate custom models through the model package interfaces. The preprocessing and postprocessing modules offer hooks for custom data transformations, while the pipeline package allows modification of forecasting workflows.


- AbstractDataPreparation - Base class for custom data preparation implementations

- ARDataPreparation - Reference implementation for autoregressive data preparation

- BaseCase - Interface for implementing custom baseline forecasting methods

- ModelCreator - Base class for creating custom machine learning models

- ObjectiveCreator - Interface for defining custom optimization objectives

- PerformanceMeter - Base class for custom performance monitoring implementations

- Reporter - Interface for implementing custom metrics reporting

- Serializer - Base class for custom model serialization formats

- StandardDeviationGenerator - Interface for custom uncertainty quantification methods

- ConfidenceIntervalApplicator - Base class for custom confidence interval calculations


