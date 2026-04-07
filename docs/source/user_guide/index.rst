User Guide
==========

This section provides practical guidance for integrating OpenSTEF into your forecasting workflows. Whether you're building congestion management systems, deploying models to production, or connecting to existing data infrastructure, these pages help you move from concepts to working implementations.

The guides below cover common integration patterns and real-world scenarios. Start with :doc:`use_cases` to see how OpenSTEF solves specific forecasting problems, then explore deployment and data integration topics as your implementation progresses.

:doc:`use_cases` - Common forecasting scenarios with complete examples, including congestion management, capacity planning, and custom prediction pipelines. See how to structure your code for different business requirements.

:doc:`deployment` - Production deployment patterns ranging from simple scheduled jobs to distributed systems. Covers containerization, orchestration, monitoring, and scaling strategies for operational forecasting systems.

:doc:`data_integration` - Connect OpenSTEF to your data sources. Examples for reading from S3, Databricks, InfluxDB, PostgreSQL, and implementing custom data loaders. Includes handling different time series formats and data quality patterns.

:doc:`migration_v3_v4` - Upgrade guide for existing OpenSTEF V3 users. Breaking changes, updated APIs, package structure modifications, and step-by-step migration instructions to help you transition smoothly.

:doc:`logging` - Configure logging for debugging and production monitoring. Set appropriate log levels, integrate with centralized logging systems, and follow best practices for observability in forecasting pipelines.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
