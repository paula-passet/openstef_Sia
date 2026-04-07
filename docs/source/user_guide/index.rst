User Guide
==========

This section covers practical topics for working with OpenSTEF in real-world projects. Whether you are integrating the library into an existing data platform, deploying forecasting pipelines to production, or upgrading from a previous version, you will find guidance here.

:doc:`use_cases` - Common use cases for OpenSTEF with practical examples, including congestion forecasting, load prediction, and renewable generation forecasts. Start here if you want to understand what problems the library solves and how to apply it to your scenario.

:doc:`deployment` - Production deployment patterns for OpenSTEF forecasting pipelines. Covers approaches ranging from simple scheduled scripts to orchestrated workflows, helping you choose the right architecture for your environment.

:doc:`data_integration` - Patterns for connecting OpenSTEF to your data sources and sinks. Includes examples for S3, Databricks, InfluxDB, PostgreSQL, and custom backends, so you can feed real data into the forecasting pipeline and store results where you need them.

:doc:`migration_v3_v4` - A step-by-step migration guide for upgrading from OpenSTEF V3 to V4. Covers breaking changes, updated APIs, and the new modular package structure so you can upgrade with confidence.

:doc:`logging` - Logging configuration and best practices. Learn how to set appropriate log levels, attach custom handlers, and integrate OpenSTEF's log output with centralized monitoring systems.

If you are new to OpenSTEF, consider starting with the :doc:`../getting_started/index` section for installation and a quick-start tutorial before diving into these topics.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
