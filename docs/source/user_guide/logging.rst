Logging
=======

OpenSTEF uses Python's standard logging library to provide visibility into its operations. As a library, OpenSTEF follows Python best practices by using a ``NullHandler`` by default, giving you complete control over how logs are handled in your application.

This page covers how to configure logging for OpenSTEF, adjust log levels for different scenarios, integrate with production logging systems, and debug common logging issues.

Basic Configuration
===================

OpenSTEF will not produce any log output unless you configure logging in your application. The simplest approach uses Python's ``basicConfig``:

.. code-block:: python

   import logging

   # Configure logging before using OpenSTEF
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   # Now OpenSTEF operations will produce log output
   from openstef_models import LinearForecaster
   
   forecaster = LinearForecaster()  # Logs initialization details

This configuration sends all log messages to stderr with timestamps and logger names. For most development and data science workflows, this is sufficient.

Understanding Log Levels
=========================

OpenSTEF uses standard Python logging levels to categorize messages by importance:

- **DEBUG**: Detailed diagnostic information useful when troubleshooting specific issues. Includes parameter values, intermediate results, and execution flow details.
- **INFO**: General information about normal operations. Confirms that things are working as expected (e.g., "Model training started", "Forecast generated for 96 horizons").
- **WARNING**: Indicates something unexpected happened, but OpenSTEF continues working. Examples include missing optional features or deprecated API usage.
- **ERROR**: A serious problem prevented a specific operation from completing. The library may continue with other operations.
- **CRITICAL**: A very serious error that may prevent the library from functioning correctly.

Configure levels based on your use case:

.. code-block:: python

   import logging

   # Development: See everything including debug details
   logging.basicConfig(level=logging.DEBUG)

   # Production: Only warnings and errors
   logging.basicConfig(level=logging.WARNING)

   # Data science workflows: Informational progress messages
   logging.basicConfig(level=logging.INFO)

Logger Hierarchy
================

OpenSTEF uses hierarchical logger names following Python conventions. This allows granular control over which components produce output:

.. code-block:: python

   import logging

   # Configure root logger
   logging.basicConfig(level=logging.INFO)

   # Reduce verbosity for specific packages
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.ERROR)

   # Enable debug logging for a specific module
   logging.getLogger('openstef_models.transforms').setLevel(logging.DEBUG)

Common logger names in OpenSTEF:

- ``openstef_models``: Core forecasting models and algorithms
- ``openstef_beam``: Apache Beam pipeline components
- ``openstef_models.transforms``: Data transformation operations
- ``openstef_models.feature_engineering``: Feature engineering pipelines

Custom Handlers
===============

For production deployments, you'll typically want more sophisticated logging than ``basicConfig`` provides. Python's logging library supports multiple handlers that can send logs to different destinations.

File-based logging
------------------

Write logs to rotating files to prevent disk space issues:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Create formatter
   formatter = logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )

   # Create rotating file handler (10MB max, keep 5 backups)
   file_handler = RotatingFileHandler(
       'openstef.log',
       maxBytes=10*1024*1024,
       backupCount=5
   )
   file_handler.setLevel(logging.INFO)
   file_handler.setFormatter(formatter)

   # Configure root logger
   logger = logging.getLogger()
   logger.setLevel(logging.INFO)
   logger.addHandler(file_handler)

JSON logging for structured data
---------------------------------

Production systems often require structured logs for parsing and analysis:

.. code-block:: python

   import logging
   import json
   from datetime import datetime

   class JSONFormatter(logging.Formatter):
       """Format log records as JSON."""
       
       def format(self, record):
           log_data = {
               'timestamp': datetime.utcnow().isoformat(),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
               'module': record.module,
               'function': record.funcName,
               'line': record.lineno
           }
           
           # Include exception info if present
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           # Include extra fields
           if hasattr(record, 'extra_fields'):
               log_data.update(record.extra_fields)
           
           return json.dumps(log_data)

   # Configure handler with JSON formatter
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   
   logger = logging.getLogger()
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

Multiple handlers
-----------------

Send different log levels to different destinations:

.. code-block:: python

   import logging
   import sys

   # Console handler for warnings and errors
   console_handler = logging.StreamHandler(sys.stderr)
   console_handler.setLevel(logging.WARNING)
   console_handler.setFormatter(
       logging.Formatter('%(levelname)s: %(message)s')
   )

   # File handler for all messages
   file_handler = logging.FileHandler('openstef_detailed.log')
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(
       logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   )

   # Configure root logger with both handlers
   logger = logging.getLogger()
   logger.setLevel(logging.DEBUG)
   logger.addHandler(console_handler)
   logger.addHandler(file_handler)

Integration with Production Systems
====================================

OpenSTEF's use of standard Python logging makes it straightforward to integrate with production logging infrastructure.

Cloud logging services
----------------------

Most cloud platforms provide Python logging integrations. For Google Cloud:

.. code-block:: python

   import logging
   import google.cloud.logging

   # Configure Google Cloud Logging
   client = google.cloud.logging.Client()
   client.setup_logging(log_level=logging.INFO)

   # OpenSTEF logs now flow to Cloud Logging
   from openstef_models import create_forecaster
   
   forecaster = create_forecaster()  # Logs appear in Cloud Logging

For AWS CloudWatch:

.. code-block:: python

   import logging
   import watchtower

   # Configure CloudWatch handler
   handler = watchtower.CloudWatchLogHandler(
       log_group='openstef-forecasting',
       stream_name='production'
   )
   
   logger = logging.getLogger()
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

Syslog integration
------------------

For systems using syslog:

.. code-block:: python

   import logging
   from logging.handlers import SysLogHandler

   # Configure syslog handler
   syslog_handler = SysLogHandler(address='/dev/log')
   syslog_handler.setFormatter(
       logging.Formatter('openstef[%(process)d]: %(levelname)s - %(message)s')
   )

   logger = logging.getLogger()
   logger.addHandler(syslog_handler)
   logger.setLevel(logging.INFO)

Contextual Logging
==================

OpenSTEF includes contextual information in log messages using the ``extra`` parameter. You can leverage this for filtering and monitoring:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   # OpenSTEF may include context like this internally
   logger.info(
       "Model training completed",
       extra={
           'model_type': 'xgboost',
           'training_samples': 10000,
           'duration_seconds': 45.2
       }
   )

For consistent context across multiple log statements, use ``LoggerAdapter``:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   class ForecastingPipeline:
       def __init__(self, pipeline_id: str):
           # Create adapter with consistent context
           self.logger = logging.LoggerAdapter(
               logger,
               extra={'pipeline_id': pipeline_id}
           )
       
       def run(self):
           # All logs include pipeline_id automatically
           self.logger.info("Pipeline started")
           self.logger.info("Loading data")
           self.logger.info("Pipeline completed")

Debugging Tips
==============

When troubleshooting OpenSTEF behavior, logging is your primary diagnostic tool.

No log output appearing
-----------------------

If you're not seeing any OpenSTEF log messages:

1. **Verify logging is configured**: OpenSTEF uses ``NullHandler`` by default, so you must configure logging explicitly.

2. **Check log levels**: Ensure your handler level isn't filtering out messages:

   .. code-block:: python

      import logging

      # Debug logging configuration
      logger = logging.getLogger('openstef_models')
      print(f"Logger level: {logger.level}")
      print(f"Effective level: {logger.getEffectiveLevel()}")
      print(f"Handlers: {logger.handlers}")
      print(f"Parent handlers: {logger.parent.handlers}")

3. **Check logger hierarchy**: Parent logger settings can override child settings.

Too much log output
-------------------

If OpenSTEF produces too many messages:

.. code-block:: python

   import logging

   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.ERROR)

   # Silence specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Temporary debug logging
-----------------------

Enable debug logging temporarily for specific operations:

.. code-block:: python

   import logging

   logger = logging.getLogger('openstef_models')
   
   # Save current level
   original_level = logger.level
   
   try:
       # Enable debug logging
       logger.setLevel(logging.DEBUG)
       
       # Run operation with verbose logging
       forecaster.fit(train_data)
       
   finally:
       # Restore original level
       logger.setLevel(original_level)

Performance Considerations
==========================

Logging can impact performance in tight loops or high-throughput scenarios. OpenSTEF follows best practices to minimize overhead:

- Log messages are not formatted unless actually output
- Debug logging uses conditional execution
- Structured logging uses lazy evaluation

You can further optimize by setting appropriate log levels:

.. code-block:: python

   import logging

   # In production, avoid DEBUG level
   logging.getLogger('openstef_models').setLevel(logging.WARNING)

For fine-grained control, use filters:

.. code-block:: python

   import logging

   class PerformanceFilter(logging.Filter):
       """Skip debug messages during performance-critical sections."""
       
       def filter(self, record):
           return record.levelno >= logging.INFO

   logging.getLogger('openstef_models').addFilter(PerformanceFilter())

Best Practices
==============

When integrating OpenSTEF into your application:

1. **Configure logging early**: Set up logging before importing OpenSTEF modules to capture all messages.

2. **Use appropriate levels**: INFO for monitoring normal operations, DEBUG for troubleshooting specific issues, WARNING or ERROR for production.

3. **Leverage hierarchical control**: Configure package-level loggers to control verbosity of different components independently.

4. **Integrate with existing infrastructure**: OpenSTEF works with any Python logging configuration, so use your organization's standard setup.

5. **Include context**: Use structured logging and contextual information to make logs more useful for debugging and monitoring.

Example complete setup:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   def setup_openstef_logging(level=logging.INFO):
       """Configure logging for OpenSTEF integration."""
       
       # Create formatter
       formatter = logging.Formatter(
           '%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )
       
       # Console handler for warnings and errors
       console_handler = logging.StreamHandler()
       console_handler.setLevel(logging.WARNING)
       console_handler.setFormatter(formatter)
       
       # File handler for detailed logs
       file_handler = RotatingFileHandler(
           'openstef.log',
           maxBytes=10*1024*1024,
           backupCount=5
       )
       file_handler.setLevel(level)
       file_handler.setFormatter(formatter)
       
       # Configure root logger
       logger = logging.getLogger()
       logger.setLevel(level)
       logger.addHandler(console_handler)
       logger.addHandler(file_handler)
       
       # Fine-tune OpenSTEF packages
       logging.getLogger('openstef_models').setLevel(level)
       logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Use in your application
   setup_openstef_logging(level=logging.INFO)

For production deployment patterns and monitoring strategies, see :doc:`deployment`. For data pipeline integration, see :doc:`data_integration`.