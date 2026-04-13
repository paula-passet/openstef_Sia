User Guide
==========

The User Guide covers practical implementation topics for integrating OpenSTEF into your own pipelines and systems — from connecting data sources to deploying forecasts in production.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples to guide your implementation.

- **Deployment** (:doc:`deployment`)
   Understand production deployment patterns for the OpenSTEF library, from simple scheduled scripts to containerised pipelines and enterprise integrations.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data infrastructure — S3, Databricks, InfluxDB, PostgreSQL, or a custom source — using the library's flexible data interfaces.

- **Migration Guide: V3 → V4** (:doc:`migration_v3_v4`)
   Upgrading from OpenSTEF V3? Start here for a full breakdown of breaking changes, updated APIs, and the new modular package structure.

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
