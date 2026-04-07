User Guide
==========

This section helps you integrate OpenSTEF into your forecasting workflows. Whether you're building congestion forecasts for grid operators, deploying models to production, or migrating from an earlier version, these guides provide practical implementation patterns and best practices.

:doc:`use_cases` - Common forecasting scenarios with concrete examples, including congestion management, transport forecasts, and grid loss predictions. Learn how to configure models for different accuracy requirements and aggregation levels.

:doc:`deployment` - Production deployment patterns ranging from simple scheduled scripts to enterprise pipeline integrations. Covers Docker-based deployments, cloud infrastructure, and monitoring strategies.

:doc:`data_integration` - Read forecast data from diverse sources including S3, Databricks, InfluxDB, PostgreSQL, and custom databases. Includes patterns for handling different data formats and availability scenarios.

:doc:`migration_v3_v4` - Step-by-step migration guide for upgrading from OpenSTEF V3 to V4. Covers breaking changes in the modular architecture, updated APIs, and new package structure.

:doc:`logging` - Configure logging for production systems. Set appropriate log levels, integrate with monitoring tools, and troubleshoot common issues using OpenSTEF's logging output.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
