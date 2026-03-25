Architecture Overview
=====================


Repository Architecture
-----------------------


The OpenSTEF ecosystem consists of multiple repositories that work together to provide a complete forecasting solution. The main openstef package contains core functionality including pipelines, feature engineering, model training, and metrics. Supporting repositories include openstef-dbc for database connectivity, openstef-reference for deployment examples, and openstef-offline-example with Jupyter notebook tutorials. These components are organized as separate packages that can be used independently or together depending on your implementation needs.


.. [DIAGRAM: Repository-level architecture showing openstef-core, openstef-meta, and other key packages with their relationships]


Core Pipeline Architecture
--------------------------


The OpenSTEF forecasting pipeline consists of four main stages that process data sequentially. Feature engineering selects and creates required features based on prediction job configuration, such as historical load data from previous days or weeks. Machine learning performs model training, forecasting, or evaluation using algorithms like XGBoost quantile regression. Model storage manages trained models through MLFlow, enabling persistence to local disk, databases, or cloud storage. Post processing combines forecasts with configuration metadata and can decompose aggregate forecasts into component predictions for solar, wind, and energy usage.


.. [DIAGRAM: Core pipeline architecture showing data ingestion, feature engineering, model training, prediction, and evaluation stages]


Meta Component Architecture
---------------------------


The OpenSTEF-meta component serves as the orchestration layer for complex forecasting workflows within the OpenSTEF library ecosystem. It coordinates the execution of prediction jobs across multiple components, managing task scheduling and data flow between the core forecasting modules. The meta component handles workflow dependencies, ensures proper sequencing of training and forecasting tasks, and provides enterprise-grade integration capabilities for production environments.


.. [DIAGRAM: OpenSTEF-meta architecture showing database models, task scheduling, workflow management, and API interfaces]


Integration Patterns
--------------------


OpenSTEF integrates into larger systems through multiple deployment patterns. As a Python library, it requires additional components for full application deployment including data fetchers, REST APIs, and schedulers. Common integration scenarios include embedding forecasting capabilities into energy management systems, creating custom data pipelines with TargetProvider interfaces, and extending functionality through configuration-driven approaches. The library's modular architecture supports both single-shot integration and continuous forecasting workflows within existing infrastructure.


.. [DIAGRAM: Integration architecture showing how OpenSTEF connects to external data sources, databases, and downstream systems]


