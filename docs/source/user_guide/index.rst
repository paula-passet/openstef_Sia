User Guide
==========

This section provides practical guidance for integrating OpenSTEF into your energy forecasting workflows. Whether you're deploying models to production, connecting to existing data sources, or migrating from an earlier version, you'll find implementation patterns and best practices here.

:doc:`use_cases` - Common forecasting scenarios with complete examples, including congestion management, load forecasting, and solar/wind prediction. See how to structure your code for different prediction types.

:doc:`deployment` - Production deployment patterns ranging from simple scheduled scripts to distributed Apache Beam pipelines. Learn how to choose the right approach for your scale and infrastructure.

:doc:`data_integration` - Connect OpenSTEF to your data sources. Examples cover S3, Databricks, InfluxDB, PostgreSQL, and custom data providers with practical code for each integration pattern.

:doc:`migration_v3_v4` - Upgrade from OpenSTEF v3 to v4 with this detailed migration guide. Covers breaking changes in the API, package structure updates, and step-by-step refactoring instructions.

:doc:`logging` - Configure logging for your forecasting pipelines. Set appropriate log levels, add custom handlers, and integrate with monitoring systems to track model performance and diagnose issues.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
