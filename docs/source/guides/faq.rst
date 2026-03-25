Frequently Asked Questions
==========================


General Questions
-----------------


This FAQ section addresses common questions about OpenSTEF and its capabilities. It's important to understand that OpenSTEF is fundamentally a Python library - a software package that provides machine learning functionality for energy load forecasting. While OpenSTEF can be integrated into larger applications with additional components like data fetchers, APIs, and user interfaces, the core OpenSTEF package itself focuses on the machine learning pipelines, feature engineering, and forecasting algorithms. This distinction helps clarify how OpenSTEF fits into your energy forecasting workflow and what additional components you may need to build a complete forecasting solution.


In the context of OpenSTEF, 'short-term' forecasting refers to predicting energy loads on the electrical grid from hours to days ahead. This timeframe is particularly valuable for grid operators and energy companies who need accurate predictions for operational planning, load balancing, and resource allocation in the near future. OpenSTEF's machine learning framework is specifically designed to excel in this short-term horizon, providing both point forecasts and confidence intervals to help users make informed decisions about grid management and energy trading activities.


OpenSTEF is fundamentally a Python library - a software package that provides machine learning capabilities for energy load forecasting. As a library, OpenSTEF contains the core components like prediction jobs, tasks, pipelines, data validation, feature engineering, and machine learning modules, but it does not include a user interface or complete application infrastructure. To deploy OpenSTEF as a full application with graphical interfaces and automated workflows, you need to combine it with additional components such as a data fetcher to collect input data, a data API to serve information to users, and a forecaster service to schedule and run OpenSTEF tasks. The library approach gives you flexibility to integrate OpenSTEF into your existing systems and customize the deployment according to your specific requirements, while a full application deployment provides a complete, ready-to-use forecasting system.


Technical Requirements
----------------------


No, grid topology data is not required for forecasting with OpenSTEF. The library operates on timeseries data of measured load or generation at specific locations and does not need information about the physical grid structure, connections between grid components, or network topology. OpenSTEF focuses on forecasting load at individual measurement points using historical load data combined with external predictors like weather data and market prices, making it suitable for forecasting at any level of the grid hierarchy without requiring detailed knowledge of how grid components are interconnected.


- Historical load or generation data as a time series with regular intervals

- Weather data (temperature, solar irradiance, wind speed) for the forecast period

- Calendar information (holidays, weekdays/weekends) for temporal feature engineering

- At least 1-2 years of historical data for reliable model training

- Data sampling frequency matching your forecast horizon (e.g., 15-minute intervals for short-term forecasts)

- Clean, validated data with minimal gaps or outliers


Topology data becomes particularly useful when you need to understand the hierarchical relationships between different measurement points in your electrical grid. While OpenSTEF can operate with individual time series data for basic forecasting, topology information enables more sophisticated modeling approaches. For instance, if you're forecasting load at a substation level and have measurements from connected feeders or transformers, topology data allows OpenSTEF to leverage these relationships during feature engineering. This hierarchical understanding becomes especially valuable when dealing with missing data scenarios, as the library can use parent-child relationships in the grid topology to fill gaps or validate measurements. Additionally, topology data is beneficial when you want to aggregate forecasts across multiple grid levels or when implementing fallback strategies that rely on upstream or downstream measurement points.


OpenSTEF can incorporate weather data as external predictors to improve forecast accuracy, but it is not strictly required for basic forecasting functionality. The library's feature engineering component automatically selects and creates features based on your prediction job configuration, which can include weather variables when available. If weather data is not accessible, OpenSTEF can still generate forecasts using historical load patterns and other available features. For optimal performance, especially when forecasting renewable generation or temperature-sensitive loads, integrating weather data such as temperature, wind speed, and solar irradiance is recommended. The library's resilient architecture includes multiple fallback strategies to ensure forecasts remain available even when some data sources are temporarily unavailable.


OpenSTEF's Unique Value
-----------------------


OpenSTEF stands out as a comprehensive machine learning framework specifically designed for short-term energy forecasting, offering several key differentiators that set it apart from generic forecasting solutions. Unlike traditional forecasting tools that focus solely on model implementation, OpenSTEF is a complete, model-agnostic Python library that encompasses the entire machine learning pipeline—from data preprocessing and feature engineering to model training, forecasting, evaluation, and post-processing. The framework excels in generating probabilistic forecasts with uncertainty bandwidths rather than single-point predictions, providing critical insights for decision-making in energy systems. What truly distinguishes OpenSTEF is its built-in domain expertise for energy forecasting, including specialized feature engineering capabilities such as converting solar radiation data into photovoltaic generation estimates, making it uniquely suited for real-world energy sector applications where domain knowledge is essential for accurate predictions.


- Built-in feature engineering for energy-specific transformations like solar radiation to PV generation estimates

- Probabilistic forecasting with uncertainty bands instead of single-point predictions

- Short-term forecasting optimization for hours-to-days-ahead predictions typical in energy operations

- Complete machine learning pipeline designed for energy sector workflows including data preprocessing, model training, and post-processing

- Model-agnostic framework allowing flexibility to use different algorithms while maintaining energy-sector optimizations

- Domain knowledge integration for grid management and congestion forecasting scenarios

- Support for energy load forecasting at specific grid points for operational decision-making


OpenSTEF incorporates deep energy domain expertise directly into its feature engineering pipeline, setting it apart from generic forecasting frameworks. The library automatically transforms weather data into energy-relevant features, such as converting solar radiation measurements into photovoltaic generation estimates. This built-in domain knowledge eliminates the need for users to manually engineer complex energy-specific features, as OpenSTEF understands the relationships between meteorological conditions and energy consumption or generation patterns. The framework's feature engineering capabilities are specifically designed for short-term energy forecasting scenarios, incorporating industry best practices and domain-specific transformations that would otherwise require extensive energy sector expertise to implement correctly.


Unlike traditional forecasting libraries that provide only point predictions, OpenSTEF specializes in probabilistic forecasting through quantile regression. This means instead of generating a single forecast value, OpenSTEF produces multiple forecasts with uncertainty bands that quantify the confidence level of predictions. For energy grid operators, this uncertainty quantification is crucial - knowing not just that peak load will be 150 MW, but understanding it could range from 140-160 MW with 80% confidence, enables better risk management and operational decisions. This probabilistic approach allows grid operators to make informed decisions about when to call customers for demand response, balancing the risk of unnecessary interventions against the cost of grid overloads.


Performance and Quality
-----------------------


OpenSTEF measures forecast quality through a comprehensive set of accuracy metrics that adapt to different use cases and business requirements. The library evaluates performance using standard statistical measures such as Mean Absolute Error (MAE), Root Mean Square Error (RMSE), and Mean Absolute Percentage Error (MAPE), allowing users to assess both absolute and relative forecast accuracy. For specialized applications like congestion management, OpenSTEF focuses on accuracy metrics during critical periods, particularly near peak load conditions where precise predictions are most valuable for grid operators. The measurement approach recognizes that forecast quality requirements vary significantly across aggregation levels - from highly aggregated substation forecasts to individual customer predictions where behavioral variability introduces additional uncertainty. OpenSTEF's modular architecture in version 4.0 enables users to implement custom metrics and evaluation frameworks that align with their specific business contexts and operational needs.


OpenSTEF forecast accuracy varies significantly depending on the specific use case and aggregation level. For highly aggregated forecasts such as substation-level predictions, typical accuracy ranges from 85-95% depending on data quality and forecast horizon. Individual customer forecasts tend to be less accurate due to behavioral variability and unpredictable consumption patterns. Key factors affecting performance include the level of data aggregation (higher aggregation generally improves accuracy), forecast horizon (shorter horizons typically yield better results), data quality and availability, seasonal patterns and weather dependencies, and the specific optimization target such as peak load accuracy for congestion management versus overall energy prediction. The library's modular architecture allows users to optimize models for their specific accuracy requirements and business context.


OpenSTEF's computational requirements scale with the complexity of your forecasting use case and deployment scenario. For research and experimentation, the library runs efficiently on standard laptops with minimal resource overhead, making it accessible for educational tutorials and low-code notebook environments. Small-scale deployments can operate effectively with basic infrastructure using Docker-compose setups, requiring only modest CPU and memory resources for typical forecasting workloads. Enterprise integration scenarios may demand more substantial computational resources, particularly when processing large numbers of prediction points or handling high-frequency data updates. The modular architecture in OpenSTEF 4.0 allows you to optimize resource usage by selecting only the components needed for your specific use case, avoiding unnecessary computational overhead from unused features. Performance-critical deployments benefit from the library's efficient implementations that are specifically optimized for production environments, while the flexible configuration mechanisms help balance accuracy requirements against computational costs based on your operational constraints.


.. note::

   Forecast accuracy in OpenSTEF varies significantly based on your specific use case, data quality, and aggregation level. Individual customer forecasts are inherently more challenging due to behavioral variability, while highly aggregated forecasts typically achieve better accuracy. The quality and completeness of your input data directly impacts model performance - missing values, irregular patterns, or poor data quality will reduce forecast accuracy. Consider your specific requirements: congestion management may prioritize accuracy during peak periods, while other applications may need consistent performance across all time periods.


Implementation and Deployment
-----------------------------


OpenSTEF primarily uses traditional machine learning approaches rather than deep learning methods. The library implements automatic machine learning pipelines that focus on proven, interpretable algorithms suitable for energy forecasting applications. This design choice ensures reliability and transparency in production environments where understanding model behavior is crucial for grid operations. Traditional ML methods also require less computational resources and training data compared to deep learning approaches, making them more practical for the diverse range of energy forecasting scenarios that OpenSTEF supports. The library's emphasis on resilient forecasting with multiple fallback strategies aligns well with traditional ML's more predictable behavior and faster inference times, which are essential for critical energy sector applications where forecast availability cannot be compromised.


OpenSTEF offers flexible deployment options to accommodate diverse IT environments and integration requirements. As a Python library, OpenSTEF can be integrated into existing systems through multiple approaches. For organizations seeking a complete solution, the OpenSTEF-reference repository provides a full stack deployment including databases, APIs, and user interfaces that can be containerized and deployed on any cloud platform. Companies with specific database requirements can utilize OpenSTEF-dbc for custom database connectivity, while those preferring to build their own integration can use the core OpenSTEF library alongside custom data fetchers, APIs, and scheduling components. The modular architecture allows teams to adopt only the components they need, whether integrating forecasting capabilities into existing energy management systems or building standalone applications. For evaluation and learning purposes, OpenSTEF-offline-example provides Jupyter notebooks demonstrating practical implementation patterns without requiring full infrastructure setup.


- Containerized deployment on Kubernetes with scheduled CronJobs for training and forecasting tasks

- Docker Compose setup using the OpenSTEF-reference implementation for complete stack deployment

- Cloud-agnostic container orchestration platforms (AWS ECS, Azure Container Instances, Google Cloud Run)

- Apache Airflow for complex ML pipeline orchestration and dependency management

- Kubernetes operators for automated model training, validation, and deployment workflows

- CI/CD pipelines with GitLab CI or GitHub Actions for automated testing and deployment

- Microservices architecture with separate containers for data fetching, API services, and forecasting components

- Hybrid cloud deployments combining on-premises data sources with cloud-based compute resources

- Event-driven architectures using message queues (RabbitMQ, Apache Kafka) for real-time forecast triggers

- Infrastructure as Code (IaC) using Terraform or Helm charts for reproducible deployments


OpenSTEF is released as an open source library, allowing for both commercial and non-commercial use. The core OpenSTEF package provides the machine learning forecasting functionality without licensing restrictions typical of proprietary software. Organizations can integrate OpenSTEF into their existing systems, modify the code to meet specific requirements, and deploy it in production environments. However, users should be aware that OpenSTEF is a library component that requires additional infrastructure for full application deployment, including data fetchers, APIs, and scheduling systems that organizations must develop or source separately. While the core forecasting algorithms are freely available, production deployments may require custom database connectors and integration work specific to each organization's IT landscape.


Getting Help and Support
------------------------


The OpenSTEF community provides several channels for getting help and support. For technical questions and discussions, you can participate in the four-weekly community meetings that are open to anyone interested in the project. If you encounter bugs or want to request features, please open an issue on the GitHub repository. For general support and community discussions, you can post questions in the OpenSTEF Teams channel. Additionally, the project maintains comprehensive documentation and examples through various repositories including OpenSTEF-reference for a complete stack deployment and OpenSTEF-offline-example with Jupyter notebooks demonstrating practical usage. All community resources, meeting schedules, and contribution guidelines can be found on the main OpenSTEF GitHub organization page.


- Getting Started Guide - Learn the basics of installing and using the OpenSTEF library

- API Reference - Complete documentation of all OpenSTEF functions and classes

- Tutorial Notebooks - Step-by-step examples in the OpenSTEF-offline-example repository

- Architecture Overview - Understanding how OpenSTEF fits into your forecasting pipeline

- Configuration Guide - Setting up prediction jobs and model parameters

- Data Requirements - Understanding input data formats and feature engineering

- Model Training - How to train forecasting models with your data

- Making Predictions - Generating forecasts and confidence intervals

- Troubleshooting - Common issues and their solutions


OpenSTEF thrives as an open-source project through active community participation and welcomes contributions in all forms. Whether you're interested in contributing code, reporting bugs, requesting features, or simply sharing your experiences with the library, your involvement helps strengthen the project for everyone. The community holds four-weekly meetings that are open to anyone interested in discussing progress, refining open issues, and exploring collaboration possibilities. You can contribute by following the contributing guidelines on GitHub, opening issues for bugs or feature requests, or joining the community discussions through the OpenSTEF Teams channel. The project's Technical Steering Committee provides governance and direction, ensuring that community input shapes the future development of this powerful forecasting library.


