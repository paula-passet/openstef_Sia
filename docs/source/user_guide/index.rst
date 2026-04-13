User Guide
==========

The User Guide covers practical implementation topics for integrating and operating OpenSTEF as a library
in your own systems and workflows.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples to guide your implementation.

- **Deployment** (:doc:`deployment`)
   Understand production deployment patterns for the library, from simple scheduled scripts to containerised pipelines and enterprise integrations.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, and custom backends — using the library's flexible data interfaces.

- **Migration V3 → V4** (:doc:`migration_v3_v4`)
   Upgrade an existing V3 codebase to V4: breaking changes, updated APIs, and a step-by-step migration checklist.

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
