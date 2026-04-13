User Guide
==========

The User Guide covers practical implementation topics for integrating OpenSTEF into your own pipelines and systems — from connecting data sources to deploying forecasts in production.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples showing how to apply the library to each.

- **Deployment** (:doc:`deployment`)
   Production deployment patterns for running OpenSTEF forecasts reliably, from simple scheduled scripts to containerised pipelines.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data infrastructure — S3, Databricks, InfluxDB, PostgreSQL, and custom sources — with ready-to-adapt integration patterns.

- **Migrating from V3 to V4** (:doc:`migration_v3_v4`)
   Step-by-step guide to updating existing code for the V4 release, covering breaking changes, renamed APIs, and the new modular package structure.

- **Logging** (:doc:`logging`)
   Configure log levels, attach custom handlers, and integrate OpenSTEF's logging output with your application's observability stack.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
