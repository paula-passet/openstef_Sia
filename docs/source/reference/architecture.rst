Architecture Overview
=====================


OpenSTEF Library Architecture
-----------------------------


OpenSTEF is a machine learning library designed with a modular architecture, not a monolithic application. The library consists of self-contained packages that can be used independently or combined, including core data types, forecasting models, feature engineering components, and evaluation tools. This modular design enables flexible integration into existing systems while maintaining focus on energy forecasting capabilities.


.. [DIAGRAM: High-level OpenSTEF library architecture showing core modules: data handling, feature engineering, model training, forecasting, and evaluation]


Repository Component Structure
------------------------------


OpenSTEF V4 is structured as a modular monorepo containing multiple self-contained packages that work together as a cohesive machine learning library. The core modules include openstef-core for foundational data types and interfaces, openstef-models for forecasting algorithms and preprocessing, openstef-meta for advanced ensemble architectures, and openstef-beam for backtesting and evaluation metrics.

Each component maintains clear separation of concerns while sharing common interfaces defined in openstef-core. The models package provides energy-specific transformations and presets, while the meta package adds sophisticated ensemble capabilities. The beam component enables rigorous model validation and performance analysis across the entire forecasting pipeline.

Additional repositories like OpenSTEF-dbc provide database connectivity, OpenSTEF-reference offers complete deployment examples, and OpenSTEF-offline-example contains practical Jupyter notebook demonstrations. This modular architecture allows users to integrate specific components based on their requirements while maintaining the library's unopinionated design philosophy.


.. [DIAGRAM: Repository-level component diagram showing openstef, openstef-meta, openstef-offline-example and their interactions (based on FOSDEM 2026 slide style)]


Core Forecasting Workflow
-------------------------


The OpenSTEF forecasting workflow begins with input data and weather data feeding into the create_forecast_pipeline. The pipeline loads the most recent trained model from MLflow storage, then processes the data through feature engineering to select and create required features based on prediction job configuration. The engineered features are passed to the machine learning component which generates forecasts and confidence intervals using the loaded model. Finally, post-processing combines the forecast results with prediction job metadata to produce the final forecast output dataframe.


.. [DIAGRAM: Forecasting workflow diagram showing: data input → feature engineering → model training/selection → forecasting → output, with feedback loops]


Component Deep Dive: OpenSTEF-Meta
----------------------------------


The openstef-meta component serves as OpenSTEF's meta-learning module, implementing modern ensemble models and advanced model architectures. This component extends the library's forecasting capabilities beyond traditional single-model approaches by providing sophisticated ensemble techniques that combine multiple base models for improved prediction accuracy.

Internally, openstef-meta leverages the foundation provided by openstef-core's data types and interfaces while integrating with openstef-models' preprocessing pipelines. The component implements meta-learning algorithms that automatically select and combine the most appropriate models based on data characteristics and performance metrics, enabling adaptive forecasting strategies for diverse energy prediction scenarios.


.. [DIAGRAM: OpenSTEF-meta component architecture diagram (Sia-style) showing internal modules, data flows, and external interfaces]


Integration Patterns
--------------------


OpenSTEF integrates into enterprise systems through multiple architectural patterns. The library's modular design supports embedding into existing data pipelines, microservice architectures, and batch processing workflows. Common scenarios include integrating tasks for automated data fetching and storage, or using pipelines directly for custom data handling. The unopinionated architecture accommodates various deployment constraints including delayed measurements and weather forecasts while maintaining forecasting performance.


.. [DIAGRAM: Integration architecture examples showing OpenSTEF library integrated with scheduling systems, data sources, and output consumers]


