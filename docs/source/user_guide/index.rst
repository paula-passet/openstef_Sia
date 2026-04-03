User Guide
==========

This section provides practical guidance for integrating OpenSTEF into your energy forecasting workflows. Whether you're building congestion management systems, deploying models to production, or migrating from an earlier version, you'll find concrete patterns and examples to help you succeed.

The user guide focuses on real-world implementation challenges. You'll learn how to connect OpenSTEF to your data sources, configure the library for different deployment scenarios, and apply forecasting models to common energy system problems. Each page includes working code examples and architectural patterns drawn from production deployments.

Start with the use cases page if you're exploring what OpenSTEF can do for your specific forecasting needs. The deployment guide covers everything from simple scheduled scripts to distributed pipeline architectures. When you're ready to connect your data, the data integration page shows how to work with S3, Databricks, InfluxDB, PostgreSQL, and custom sources. If you're upgrading from OpenSTEF 3.x, the migration guide walks through breaking changes and updated APIs. Finally, the logging page helps you configure observability for production systems.

This guide assumes you've already installed OpenSTEF and understand basic forecasting concepts. If you're new to the library, start with the Quick Start guide first.

.. toctree::
   :maxdepth: 1
   :caption: User Guide
   :hidden:

   use_cases
   deployment
   data_integration
   migration_v3_v4
   logging
