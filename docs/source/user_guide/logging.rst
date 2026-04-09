Logging Configuration
=====================

OpenSTEF uses Python's standard logging library to provide visibility into its operations. As a library, OpenSTEF follows Python best practices by using ``NullHandler`` by default, giving you complete control over logging configuration in your application.

This page covers how to configure logging for OpenSTEF, control log verbosity, integrate with production logging systems, and troubleshoot common logging issues.

Basic Configuration
===================

To see OpenSTEF log messages, configure Python's logging module before using OpenSTEF:

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

This simple setup is sufficient for most use cases, including Jupyter notebooks, scripts, and simple applications.

Log Levels
==========

OpenSTEF uses standard Python logging levels to categorize messages:

- **DEBUG**: Detailed diagnostic information useful when diagnosing problems (e.g., feature shapes, transformation steps)
- **INFO**: General information about operations (e.g., model training started, forecast generated)
- **WARNING**: Unexpected situations that don't prevent operation (e.g., missing optional features, fallback behavior)
- **ERROR**: Serious problems that prevented a function from completing (e.g., invalid data format, model training failure)
- **CRITICAL**: Very serious errors that may prevent the program from continuing

Choose the appropriate level based on your environment:

.. code-block:: python

   import logging

   # Development: See everything
   logging.basicConfig(level=logging.DEBUG)

   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)

   # Data science workflows: Informational messages
   logging.basicConfig(level=logging.INFO)

Hierarchical Logger Control
============================

OpenSTEF uses hierarchical logger names following Python conventions. This allows fine-grained control over different parts of the library.

Package-level control
---------------------

Control logging for entire OpenSTEF packages:

.. code-block:: python

   import logging

   # Show only warnings from openstef-beam
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Enable debug mode for openstef-models
   logging.getLogger('openstef_models').setLevel(logging.DEBUG)

   # Disable all openstef-models logging
   logging.getLogger('openstef_models').setLevel(logging.CRITICAL)

Module-level control
--------------------

Control logging for specific modules within a package:

.. code-block:: python

   import logging

   # Only show errors from the presets module
   logging.getLogger('openstef_models.presets').setLevel(logging.ERROR)

   # Debug feature engineering specifically
   logging.getLogger('openstef_models.transforms').setLevel(logging.DEBUG)

This granular control is particularly useful when debugging specific components without being overwhelmed by logs from other parts of the library.

Production Logging Setup
=========================

For production environments, you typically need more sophisticated logging configurations including file output, log rotation, and structured logging.

File-based logging
------------------

Write OpenSTEF logs to files with rotation:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Create rotating file handler
   handler = RotatingFileHandler(
       'openstef.log',
       maxBytes=10*1024*1024,  # 10 MB
       backupCount=5
   )
   handler.setLevel(logging.INFO)
   handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))

   # Configure OpenSTEF loggers
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_beam').addHandler(handler)

Multiple handlers
-----------------

Send different log levels to different destinations:

.. code-block:: python

   import logging
   import sys

   # Console handler for warnings and above
   console_handler = logging.StreamHandler(sys.stdout)
   console_handler.setLevel(logging.WARNING)
   console_handler.setFormatter(logging.Formatter(
       '%(levelname)s: %(message)s'
   ))

   # File handler for all messages
   file_handler = logging.FileHandler('openstef_detailed.log')
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))

   # Apply to OpenSTEF loggers
   openstef_logger = logging.getLogger('openstef_models')
   openstef_logger.addHandler(console_handler)
   openstef_logger.addHandler(file_handler)
   openstef_logger.setLevel(logging.DEBUG)

Integration with logging systems
---------------------------------

OpenSTEF works seamlessly with popular Python logging frameworks:

.. code-block:: python

   import logging
   import logging.config

   # Load logging configuration from file
   logging.config.fileConfig('logging.conf')

   # Or use dictConfig for programmatic setup
   LOGGING_CONFIG = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'detailed': {
               'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
           },
       },
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
               'level': 'INFO',
               'formatter': 'detailed',
           },
       },
       'loggers': {
           'openstef_models': {
               'level': 'INFO',
               'handlers': ['console'],
               'propagate': False,
           },
           'openstef_beam': {
               'level': 'WARNING',
               'handlers': ['console'],
               'propagate': False,
           },
       },
   }

   logging.config.dictConfig(LOGGING_CONFIG)

Contextual Information
======================

OpenSTEF includes contextual information in log messages through the ``extra`` parameter, making it easier to filter and analyze logs in production systems.

Using LoggerAdapter for consistent context
-------------------------------------------

When you need consistent context across multiple log messages:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   class ForecastingPipeline:
       """Forecasting pipeline with consistent logging context."""
       
       def __init__(self, model_id: str, location: str):
           # Create adapter with consistent context
           self.logger = logging.LoggerAdapter(
               logger=logger,
               extra={
                   "model_id": model_id,
                   "location": location,
               }
           )
       
       def generate_forecast(self, data):
           """Generate forecast with contextual logging."""
           # All log messages include model_id and location
           self.logger.info(f"Starting forecast generation")
           
           try:
               result = self._run_model(data)
               self.logger.info(f"Forecast completed successfully")
               return result
           except Exception as e:
               self.logger.error(f"Forecast failed: {e}")
               raise

This contextual information is particularly valuable when aggregating logs from multiple forecasting jobs or when integrating with monitoring systems that support structured logging.

Debugging Tips
==============

Enable debug logging temporarily
---------------------------------

When troubleshooting issues, enable debug logging for specific components:

.. code-block:: python

   import logging

   # Temporarily enable debug logging
   logging.getLogger('openstef_models').setLevel(logging.DEBUG)

   # Run your code
   forecaster.train(data)

   # Restore normal logging
   logging.getLogger('openstef_models').setLevel(logging.INFO)

Inspect logger configuration
-----------------------------

If logs aren't appearing as expected, inspect the logger configuration:

.. code-block:: python

   import logging

   logger = logging.getLogger('openstef_models')
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers}")

This helps identify configuration issues like missing handlers or incorrect log levels.

Capture warnings
----------------

Python warnings can be redirected to the logging system:

.. code-block:: python

   import logging
   import warnings

   # Redirect warnings to logging
   logging.captureWarnings(True)

   # Configure warnings logger
   warnings_logger = logging.getLogger('py.warnings')
   warnings_logger.setLevel(logging.WARNING)

Troubleshooting
===============

No log output appearing
-----------------------

If you're not seeing OpenSTEF log messages:

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

Logging can impact performance in tight loops. OpenSTEF follows best practices to minimize overhead, but you can further optimize:

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

Follow these guidelines when configuring logging for OpenSTEF:

1. **Configure logging early**: Set up logging before importing OpenSTEF modules to ensure all messages are captured
2. **Use appropriate levels**: INFO for general monitoring, DEBUG for troubleshooting, WARNING for production
3. **Leverage hierarchical control**: Use package and module-level logger configuration for fine-grained control
4. **Integrate with your existing setup**: OpenSTEF works with any Python logging configuration
5. **Include context**: Use ``LoggerAdapter`` or ``extra`` parameters to add contextual information for production debugging

Complete setup example
----------------------

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
       
       # Fine-tune specific packages
       logging.getLogger('openstef_models').setLevel(level)
       logging.getLogger('openstef_beam').setLevel(logging.WARNING)  # Less verbose

   # Use in your application
   setup_openstef_logging(level=logging.INFO)

   # Now use OpenSTEF with proper logging
   from openstef_models import create_forecaster
   forecaster = create_forecaster()

For production deployment patterns and monitoring integration, see :doc:`deployment`. For data pipeline logging considerations, see :doc:`data_integration`.