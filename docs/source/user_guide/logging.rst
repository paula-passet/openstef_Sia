Logging Configuration
=====================

OpenSTEF uses Python's standard logging framework to provide visibility into library operations. As a library, OpenSTEF does not configure logging itself—it's your responsibility to set up logging in your application to see OpenSTEF's messages. This page covers how to configure logging for OpenSTEF, control log verbosity, integrate with production logging systems, and debug common logging issues.

Why Configure Logging?
----------------------

By default, OpenSTEF uses ``NullHandler``, which means log messages are silently discarded unless you configure logging. This follows Python library best practices: libraries should never configure logging themselves, leaving that control to the application.

Configuring logging gives you:

- Visibility into model training progress and performance
- Early warning of data quality issues
- Detailed diagnostics when troubleshooting problems
- Audit trails for production forecasting operations

Basic Configuration
-------------------

The simplest way to see OpenSTEF log messages is to configure Python's root logger:

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

This configuration applies to all loggers in your application. For more control, configure OpenSTEF loggers specifically:

.. code-block:: python

   import logging
   
   # Configure only OpenSTEF loggers
   logging.getLogger('openstef_models').setLevel(logging.INFO)
   logging.getLogger('openstef_beam').setLevel(logging.INFO)
   
   # Add a handler if none exists
   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))
   logging.getLogger('openstef_models').addHandler(handler)

Log Levels
----------

OpenSTEF uses standard Python logging levels. Choose the appropriate level based on your environment:

**DEBUG**
   Detailed diagnostic information including data shapes, feature names, intermediate calculations, and algorithm decisions. Use during development or when diagnosing specific problems. Can be verbose.

**INFO**
   General information about operations: model training started, features selected, validation metrics, forecast generation completed. Appropriate for data science workflows and general monitoring.

**WARNING**
   Something unexpected happened but processing continues: missing features, data quality issues, fallback to default parameters. Always worth reviewing.

**ERROR**
   A serious problem prevented an operation from completing: model training failed, invalid configuration, missing required data. Requires attention.

**CRITICAL**
   A very serious error that may prevent the program from continuing. Rare in library code.

Example configurations for different scenarios:

.. code-block:: python

   import logging
   
   # Development: See everything
   logging.basicConfig(level=logging.DEBUG)
   
   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)
   
   # Data science workflows: Informational messages
   logging.basicConfig(level=logging.INFO)

Logger Hierarchy
----------------

OpenSTEF loggers follow Python's hierarchical naming convention. The main logger hierarchies are:

- ``openstef_models``: Core forecasting models and algorithms
- ``openstef_beam``: Apache Beam pipeline components
- ``openstef_models.transforms``: Data transformation modules
- ``openstef_models.feature_engineering``: Feature engineering components

You can control logging at any level of the hierarchy:

.. code-block:: python

   import logging
   
   # Control all openstef_models logging
   logging.getLogger('openstef_models').setLevel(logging.INFO)
   
   # Make one specific module more verbose
   logging.getLogger('openstef_models.feature_engineering').setLevel(logging.DEBUG)
   
   # Silence a noisy module
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Custom Handlers
---------------

For production systems, you'll typically want to send logs to specialized systems rather than stdout. Here are common patterns:

File Logging
^^^^^^^^^^^^

Write logs to rotating files:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler
   
   # Create rotating file handler
   handler = RotatingFileHandler(
       'openstef_forecasts.log',
       maxBytes=10*1024*1024,  # 10MB
       backupCount=5
   )
   handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))
   
   # Add to OpenSTEF loggers
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_models').setLevel(logging.INFO)

JSON Structured Logging
^^^^^^^^^^^^^^^^^^^^^^^

For log aggregation systems like ELK or Splunk:

.. code-block:: python

   import logging
   import json
   from datetime import datetime
   
   class JSONFormatter(logging.Formatter):
       def format(self, record):
           log_data = {
               'timestamp': datetime.utcnow().isoformat(),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
               'module': record.module,
               'function': record.funcName,
           }
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           return json.dumps(log_data)
   
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger('openstef_models').addHandler(handler)

Cloud Logging Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Integrate with cloud provider logging services:

.. code-block:: python

   import logging
   
   # Google Cloud Logging
   from google.cloud import logging as gcp_logging
   
   client = gcp_logging.Client()
   handler = gcp_logging.handlers.CloudLoggingHandler(client)
   
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_models').setLevel(logging.INFO)

.. code-block:: python

   import logging
   
   # AWS CloudWatch Logs
   import watchtower
   
   handler = watchtower.CloudWatchLogHandler(
       log_group='openstef-forecasts',
       stream_name='production'
   )
   
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_models').setLevel(logging.INFO)

Production Best Practices
--------------------------

Configure Logging Early
^^^^^^^^^^^^^^^^^^^^^^^

Set up logging before importing OpenSTEF modules to ensure all messages are captured:

.. code-block:: python

   import logging
   
   # Configure logging first
   logging.basicConfig(level=logging.INFO)
   
   # Then import OpenSTEF
   from openstef_models import LinearForecaster

Use Appropriate Levels
^^^^^^^^^^^^^^^^^^^^^^^

In production, use WARNING or ERROR levels to reduce noise:

.. code-block:: python

   import logging
   
   # Production configuration
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

This ensures you see problems without overwhelming your logging system with routine operations.

Add Contextual Information
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use LoggerAdapter to add context to all log messages from a specific operation:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   def generate_forecast(prediction_job_id: int, model_config):
       # Add context to all log messages
       context_logger = logging.LoggerAdapter(
           logger,
           {'prediction_job_id': prediction_job_id}
       )
       
       context_logger.info("Starting forecast generation")
       # All subsequent logs will include prediction_job_id
       forecaster = train_model(model_config)
       context_logger.info("Forecast generation complete")

Monitor Error Rates
^^^^^^^^^^^^^^^^^^^

Set up alerts on ERROR and CRITICAL level messages:

.. code-block:: python

   import logging
   
   class ErrorAlertHandler(logging.Handler):
       def emit(self, record):
           if record.levelno >= logging.ERROR:
               # Send alert to monitoring system
               send_alert(
                   title=f"OpenSTEF Error: {record.getMessage()}",
                   severity='high',
                   details={
                       'logger': record.name,
                       'module': record.module,
                       'function': record.funcName,
                   }
               )
   
   logging.getLogger('openstef_models').addHandler(ErrorAlertHandler())

Debugging Tips
--------------

No Log Output Appearing
^^^^^^^^^^^^^^^^^^^^^^^^

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

Too Much Log Output
^^^^^^^^^^^^^^^^^^^

If OpenSTEF is producing too many log messages:

.. code-block:: python

   import logging
   
   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)
   
   # Or disable specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging can impact performance in tight loops. Use conditional logging for expensive operations:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   # Bad: Always formats message even if not logged
   logger.debug(f"Data summary: {large_df.describe().to_string()}")
   
   # Good: Only formats if debug logging is enabled
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug(f"Data summary: {large_df.describe().to_string()}")
   
   # Also good: Use lazy formatting
   logger.debug("Processed %d rows", len(large_df))

Testing Logging
^^^^^^^^^^^^^^^

When testing code that uses logging, use pytest's ``caplog`` fixture:

.. code-block:: python

   import logging
   import pytest
   
   def test_forecast_generation_logs_progress(caplog):
       """Test that forecast generation logs expected messages."""
       with caplog.at_level(logging.INFO):
           forecaster = LinearForecaster()
           forecaster.fit(train_data)
           
       # Verify expected log messages
       assert "Training started" in caplog.text
       assert "Training complete" in caplog.text
       
       # Verify log levels
       info_messages = [r for r in caplog.records if r.levelno == logging.INFO]
       assert len(info_messages) >= 2

See Also
--------

- :doc:`deployment` - Production deployment patterns including logging infrastructure
- :doc:`data_integration` - Data pipeline logging and monitoring
- :doc:`use_cases` - Common use cases with logging examples