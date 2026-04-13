User Guide
==========

Practical guidance for integrating OpenSTEF into your own systems and workflows — from connecting data sources to running the library in production.

- **Use Cases** (:doc:`use_cases`)
   Concrete examples of what OpenSTEF can forecast, including congestion management, transport, and grid losses, with guidance on choosing the right approach for your scenario.

- **Deployment** (:doc:`deployment`)
   Production deployment patterns for running OpenSTEF as part of a scheduled pipeline, a service, or a larger MLOps workflow.

- **Data Integration** (:doc:`data_integration`)
   How to connect OpenSTEF to your data sources — S3, Databricks, InfluxDB, PostgreSQL, and custom backends.

- **Migrating from V3 to V4** (:doc:`migration_v3_v4`)
   Breaking changes, updated APIs, and a step-by-step upgrade path for projects currently using OpenSTEF V3.

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
