User Guide
==========

This section covers practical implementation topics for using OpenSTEF as a library in your own
Python projects — from integrating data sources and deploying pipelines to handling real-world
forecasting scenarios.

- **Use Cases** (:doc:`use_cases`)
   Worked examples for common forecasting scenarios including congestion management, transport
   forecasts, and grid losses — useful when you want to see how OpenSTEF applies to a specific
   problem domain.

- **Deployment** (:doc:`deployment`)
   Production deployment patterns ranging from simple scheduled scripts to containerised pipelines
   — consult this when you are ready to move beyond experimentation and run OpenSTEF reliably in
   your infrastructure.

- **Data Integration** (:doc:`data_integration`)
   How to connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, and
   custom backends — covering the interfaces you need to implement and common integration patterns.

- **Migrating from V3 to V4** (:doc:`migration_v3_v4`)
   A guide to breaking changes, updated APIs, and restructured packages introduced in OpenSTEF 4.0
   — start here if you are upgrading an existing V3 codebase.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
