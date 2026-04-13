User Guide
==========

The User Guide covers practical implementation topics for integrating OpenSTEF into your own pipelines and systems — from connecting data sources to deploying forecasts in production.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with practical examples showing how to apply the library to each.

- **Deployment** (:doc:`deployment`)
   Patterns for running OpenSTEF in production, from simple scheduled scripts to containerised pipelines and enterprise integrations.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data infrastructure — S3, Databricks, InfluxDB, PostgreSQL, and custom sources — using the library's flexible input interfaces.

- **Migrating from V3 to V4** (:doc:`migration_v3_v4`)
   Step-by-step guide to updating existing code for the V4 release, covering breaking API changes, restructured packages, and new configuration patterns.

- **Logging** (:doc:`logging`)
   Configure log levels, attach custom handlers, and integrate OpenSTEF's logging output with your existing observability stack.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
