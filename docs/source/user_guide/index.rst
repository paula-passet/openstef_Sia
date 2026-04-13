User Guide
==========

The user guide covers practical implementation topics for integrating and operating OpenSTEF as a library within your own systems and workflows.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples to guide your implementation.

- **Deployment** (:doc:`deployment`)
   Patterns for running OpenSTEF in production, from simple scheduled scripts to containerised pipelines and enterprise integrations.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, or a custom backend — and understand the expected input formats.

- **Migration V3 → V4** (:doc:`migration_v3_v4`)
   Breaking changes, updated APIs, and a step-by-step upgrade path for projects moving from OpenSTEF V3 to V4.

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
