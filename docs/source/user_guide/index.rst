User Guide
==========

The user guide covers practical implementation topics for integrating OpenSTEF into your own systems and workflows, answering common "how do I..." questions for both new and experienced users.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples to guide your implementation.

- **Deployment** (:doc:`deployment`)
   Patterns for running OpenSTEF in production, from simple scheduled scripts to enterprise pipeline integration.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, and custom backends — with practical integration patterns.

- **Migrating from V3 to V4** (:doc:`migration_v3_v4`)
   Understand the breaking changes in V4, updated APIs, and how to update existing code to work with the new modular architecture.

- **Logging** (:doc:`logging`)
   Configure log levels, attach custom handlers, and integrate OpenSTEF's logging with your existing observability stack.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
