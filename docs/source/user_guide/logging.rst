Logging Configuration
=====================

OpenSTEF uses Python's standard logging library to provide visibility into model training, predictions, and data processing operations. This page covers how to configure logging for different environments, control log verbosity, integrate with production logging systems, and troubleshoot common issues.

As a library, OpenSTEF follows Python logging best practices by using ``NullHandler`` by default, giving you full control over how and where log messages appear in your application.

Basic Configuration
===================

To see OpenSTEF log messages, configure logging in your application before importing OpenSTEF modules:

.. code-block:: python

   import logging

   # Basic configuration - shows INFO level and above
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   # Now OpenSTEF operations will produce log output
   from openstef_models import LinearForecaster
   
   forecaster = LinearForecaster()  # Will log initialization details

For production applications, configure logging early in your application startup, before importing any OpenSTEF modules.

Log Levels
==========

OpenSTEF uses standard Python logging levels to provide different amounts of detail:

* **DEBUG**: Detailed diagnostic information including feature values, intermediate calculations, and model parameters
* **INFO**: General information about training progress, prediction runs, and data processing steps
* **WARNING**: Unexpected situations like missing features or data quality issues that don't prevent execution
* **ERROR**: Serious problems that prevented a specific operation from completing
* **CRITICAL**: Very serious errors that may prevent the program from continuing

Choose the appropriate level for your use case:

.. code-block:: python

   import logging

   # Development: See everything for debugging
   logging.basicConfig(level=logging.DEBUG)

   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)

   # Data science workflows: Monitor progress without excessive detail
   logging.basicConfig(level=logging.INFO)

Logger Hierarchy
================

OpenSTEF loggers follow Python's hierarchical naming convention, allowing fine-grained control over different components.

Package level control
---------------------

Control logging for entire OpenSTEF packages:

.. code-block:: python

   import logging

   # Disable all openstef-models logging
   logging.getLogger('openstef_models').setLevel(logging.CRITICAL)

   # Show only warnings from openstef-beam
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Enable debug mode for specific package
   logging.getLogger('openstef_models').setLevel(logging.DEBUG)

Module level control
--------------------

Control logging for specific modules when you need even more precision:

.. code-block:: python

   import logging

   # Only show errors from the presets module
   logging.getLogger('openstef_models.presets').setLevel(logging.ERROR)

   # Debug feature engineering specifically
   logging.getLogger('openstef_models.transforms').setLevel(logging.DEBUG)

This hierarchical approach lets you keep most logging quiet while enabling detailed output for the specific component you're investigating.

Integration with Production Systems
====================================

Structured logging with structlog
----------------------------------

If you're using `structlog <https://www.structlog.org/>`_ in your application, configure it to integrate with Python's standard logging:

.. code-block:: python

   import logging
   import structlog

   # Configure structlog to integrate with standard logging
   structlog.configure(
       processors=[
           structlog.stdlib.filter_by_level,
           structlog.stdlib.add_logger_name,
           structlog.stdlib.add_log_level,
           structlog.stdlib.PositionalArgumentsFormatter(),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.UnicodeDecoder(),
           structlog.processors.JSONRenderer()
       ],
       context_class=dict,
       logger_factory=structlog.stdlib.LoggerFactory(),
       wrapper_class=structlog.stdlib.BoundLogger,
       cache_logger_on_first_use=True,
   )

   # Configure standard logging
   logging.basicConfig(
       format="%(message)s",
       level=logging.INFO,
   )

   # Now OpenSTEF logs will be processed by structlog
   from openstef_models import create_forecaster
   
   forecaster = create_forecaster()

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

Custom handlers
---------------

Add custom handlers to route OpenSTEF logs to files, external services, or monitoring systems:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler, SysLogHandler

   # File handler with rotation
   file_handler = RotatingFileHandler(
       'openstef.log',
       maxBytes=10*1024*1024,  # 10MB
       backupCount=5
   )
   file_handler.setLevel(logging.INFO)
   file_handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))

   # Syslog handler for centralized logging
   syslog_handler = SysLogHandler(address='/dev/log')
   syslog_handler.setLevel(logging.WARNING)

   # Apply handlers to OpenSTEF loggers
   openstef_logger = logging.getLogger('openstef_models')
   openstef_logger.addHandler(file_handler)
   openstef_logger.addHandler(syslog_handler)
   openstef_logger.setLevel(logging.INFO)

Contextual Information
======================

OpenSTEF includes contextual information in log messages to help with debugging and monitoring. Many log messages include extra fields that provide additional context:

.. code-block:: python

   # Example of structured log output (when using appropriate formatters)
   2025-01-20 14:30:25 - openstef_models.training - INFO - Model training started
   extra_info: {
       'model_type': 'XGBoostForecaster',
       'training_samples': 8760,
       'features': ['temperature', 'humidity', 'hour_of_day'],
       'horizon': 24
   }

This contextual information is particularly useful when debugging model training issues, monitoring model performance in production, analyzing feature engineering pipelines, or tracking data processing workflows.

Troubleshooting
===============

No log output appearing
-----------------------

If you're not seeing any OpenSTEF log messages:

1. **Check if logging is configured**: OpenSTEF uses ``NullHandler`` by default
2. **Verify log levels**: Ensure your handler level isn't too restrictive
3. **Check logger hierarchy**: Parent logger settings can override child settings

.. code-block:: python

   import logging

   # Debug logging configuration
   logger = logging.getLogger('openstef_models')
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers}")

Too much log output
-------------------

If OpenSTEF is producing too many log messages:

.. code-block:: python

   import logging

   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Or disable specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Performance considerations
--------------------------

Logging can impact performance in tight loops. OpenSTEF follows best practices where log messages are not formatted unless actually output, debug logging is conditionally executed, and structured logging uses lazy evaluation.

You can further optimize by setting appropriate levels to avoid unnecessary processing:

.. code-block:: python

   import logging

   # Set appropriate levels to avoid unnecessary processing
   logging.getLogger('openstef_models').setLevel(logging.WARNING)

   # Use logging filters for fine-grained control
   class PerformanceFilter(logging.Filter):
       def filter(self, record):
           # Skip debug messages during performance-critical sections
           return record.levelno >= logging.INFO

   logging.getLogger('openstef_models').addFilter(PerformanceFilter())

Best Practices
==============

For effective logging when using OpenSTEF as a library:

1. **Configure logging early**: Set up logging before importing OpenSTEF modules
2. **Use appropriate levels**: INFO for general monitoring, DEBUG for troubleshooting
3. **Leverage hierarchical control**: Use package/module-level logger configuration to control specific components
4. **Integrate with your existing setup**: OpenSTEF works with any Python logging configuration

Example complete setup:

.. code-block:: python

   import logging

   def setup_openstef_logging(level=logging.INFO):
       """Set up logging for OpenSTEF integration."""
       # Basic configuration
       logging.basicConfig(
           level=level,
           format='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )
       
       # Optional: Fine-tune specific packages
       logging.getLogger('openstef_models').setLevel(level)
       logging.getLogger('openstef_beam').setLevel(logging.WARNING)  # Less verbose

   # Use in your application
   setup_openstef_logging(level=logging.INFO)
   
   from openstef_models import create_forecaster
   forecaster = create_forecaster()

Jupyter Notebooks
-----------------

Configure logging for interactive data science work:

.. code-block:: python

   import logging

   # Configure for notebook use
   logging.basicConfig(
       level=logging.INFO,
       format='%(name)-20s | %(levelname)-8s | %(message)s',
       force=True  # Override any existing configuration
   )

   # Now OpenSTEF operations will show progress
   from openstef_models import load_sample_data, XGBoostForecaster
   
   data = load_sample_data()  # Shows data loading progress
   model = XGBoostForecaster()
   model.fit(data)  # Shows training progress

For more advanced logging configurations like custom formatters, rotating logs, and other features, refer to the official `Python logging documentation <https://docs.python.org/3/library/logging.html>`_.

See Also
========

* :doc:`deployment` - Production deployment patterns including logging considerations
* :doc:`data_integration` - Data integration patterns where logging helps track data processing