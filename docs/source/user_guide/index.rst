User Guide
==========

The User Guide covers practical implementation topics for integrating OpenSTEF into your own systems and workflows — from connecting data sources to running forecasts in production.

- **Use Cases** (:doc:`use_cases`)
   Explore concrete forecasting scenarios — congestion management, transport forecasts, and grid losses — with worked examples to match OpenSTEF to your problem.

- **Deployment** (:doc:`deployment`)
   Understand production deployment patterns, from simple scheduled scripts to pipeline integrations, and choose the approach that fits your infrastructure.

- **Data Integration** (:doc:`data_integration`)
   Connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, or a custom backend — with patterns for reading and writing forecast data.

- **Migration V3 → V4** (:doc:`migration_v3_v4`)
   Upgrading from V3? This guide covers breaking changes, updated APIs, and the steps needed to bring your existing code forward to V4.

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
