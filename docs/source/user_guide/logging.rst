Logging Configuration
=====================

OpenSTEF uses Python's standard logging module and integrates seamlessly with your existing logging infrastructure. As a library, OpenSTEF uses ``NullHandler`` by default, giving you complete control over how and where logs are captured. This page covers how to configure logging for OpenSTEF, adjust log levels for different scenarios, integrate with production logging systems, and troubleshoot common logging issues.

Basic Configuration
-------------------

The simplest way to enable OpenSTEF logging is to configure Python's root logger:

.. code-block:: python

   import logging

   # Basic configuration for development
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )

   # Now use OpenSTEF - logs will appear automatically
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   
   model = XGBOpenstfRegressor()
   # Logs will show initialization details

For production environments, you typically want more control over different OpenSTEF packages:

.. code-block:: python

   import logging

   def setup_openstef_logging(level=logging.INFO):
       """Configure logging for OpenSTEF integration."""
       logging.basicConfig(
           level=level,
           format='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )
       
       # Fine-tune specific packages
       logging.getLogger('openstef').setLevel(level)
       logging.getLogger('openstef.model').setLevel(logging.INFO)
       logging.getLogger('openstef.pipeline').setLevel(logging.WARNING)
       
   setup_openstef_logging(level=logging.INFO)

Log Levels
----------

Choose appropriate log levels based on your use case:

.. code-block:: python

   import logging

   # Development: See everything including debug details
   logging.basicConfig(level=logging.DEBUG)
   logging.getLogger('openstef').setLevel(logging.DEBUG)

   # Production: Important messages and warnings only
   logging.basicConfig(level=logging.WARNING)
   logging.getLogger('openstef').setLevel(logging.WARNING)

   # Data science workflows: Informational progress messages
   logging.basicConfig(level=logging.INFO)
   logging.getLogger('openstef').setLevel(logging.INFO)

OpenSTEF uses standard Python logging levels appropriately:

- **DEBUG**: Detailed diagnostic information (data shapes, column names, intermediate values)
- **INFO**: Important operational information (training progress, data loading, model initialization)
- **WARNING**: Unexpected but recoverable situations (missing values, deprecated features)
- **ERROR**: Serious problems that prevent operation completion
- **CRITICAL**: System-level failures

Logger Hierarchy
----------------

OpenSTEF follows Python's hierarchical logger naming convention. You can control logging at different levels of granularity:

.. code-block:: python

   import logging

   # Control all OpenSTEF logging
   logging.getLogger('openstef').setLevel(logging.INFO)

   # Control specific submodules
   logging.getLogger('openstef.model').setLevel(logging.DEBUG)
   logging.getLogger('openstef.feature_engineering').setLevel(logging.WARNING)
   logging.getLogger('openstef.data_classes').setLevel(logging.ERROR)

   # Silence specific noisy modules
   logging.getLogger('openstef.model.serializer').setLevel(logging.ERROR)

This hierarchical approach lets you see detailed logs for areas you're debugging while keeping other areas quiet.

Custom Handlers
---------------

For production systems, you'll typically want to send logs to multiple destinations. Here's how to set up custom handlers:

.. code-block:: python

   import logging
   import logging.handlers
   import sys

   def setup_production_logging():
       """Configure logging for production with multiple handlers."""
       # Create formatters
       detailed_formatter = logging.Formatter(
           '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )
       simple_formatter = logging.Formatter(
           '%(asctime)s - %(levelname)s - %(message)s'
       )

       # Console handler for INFO and above
       console_handler = logging.StreamHandler(sys.stdout)
       console_handler.setLevel(logging.INFO)
       console_handler.setFormatter(simple_formatter)

       # File handler for all messages
       file_handler = logging.handlers.RotatingFileHandler(
           'openstef.log',
           maxBytes=10*1024*1024,  # 10MB
           backupCount=5
       )
       file_handler.setLevel(logging.DEBUG)
       file_handler.setFormatter(detailed_formatter)

       # Error file handler for warnings and errors
       error_handler = logging.handlers.RotatingFileHandler(
           'openstef_errors.log',
           maxBytes=10*1024*1024,
           backupCount=5
       )
       error_handler.setLevel(logging.WARNING)
       error_handler.setFormatter(detailed_formatter)

       # Configure OpenSTEF logger
       openstef_logger = logging.getLogger('openstef')
       openstef_logger.setLevel(logging.DEBUG)
       openstef_logger.addHandler(console_handler)
       openstef_logger.addHandler(file_handler)
       openstef_logger.addHandler(error_handler)

       return openstef_logger

   setup_production_logging()

Integration with Production Systems
------------------------------------

Structured Logging with structlog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your organization uses structlog for structured logging, OpenSTEF integrates seamlessly:

.. code-block:: python

   import logging
   import structlog

   # Configure structlog to process standard logging
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

   # Now OpenSTEF logs will be JSON-formatted
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   
   model = XGBOpenstfRegressor()
   # Logs appear as structured JSON

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

Cloud Logging Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^

For cloud platforms, you can integrate with their logging services:

.. code-block:: python

   import logging
   from google.cloud import logging as cloud_logging

   def setup_gcp_logging():
       """Configure OpenSTEF logging for Google Cloud Platform."""
       # Set up GCP logging client
       client = cloud_logging.Client()
       client.setup_logging()

       # Configure OpenSTEF logger
       logger = logging.getLogger('openstef')
       logger.setLevel(logging.INFO)
       
       return logger

   # For AWS CloudWatch
   import watchtower

   def setup_aws_logging():
       """Configure OpenSTEF logging for AWS CloudWatch."""
       logger = logging.getLogger('openstef')
       logger.setLevel(logging.INFO)
       
       handler = watchtower.CloudWatchLogHandler(
           log_group='openstef-forecasting',
           stream_name='production'
       )
       logger.addHandler(handler)
       
       return logger

Contextual Logging
^^^^^^^^^^^^^^^^^^

Add consistent context to log messages using ``LoggerAdapter``:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   class ForecastingPipeline:
       """Pipeline with consistent logging context."""
       
       def __init__(self, prediction_job_id: int, model_type: str):
           self.prediction_job_id = prediction_job_id
           self.model_type = model_type
           
           # Create adapter with context
           self.logger = logging.LoggerAdapter(
               logger=logger,
               extra={
                   'prediction_job_id': prediction_job_id,
                   'model_type': model_type
               }
           )
       
       def run_forecast(self, data):
           """Run forecast with contextual logging."""
           # All logs include prediction_job_id and model_type
           self.logger.info(f"Starting forecast for {len(data)} samples")
           
           try:
               result = self._train_and_predict(data)
               self.logger.info(f"Forecast completed successfully")
               return result
           except Exception as e:
               self.logger.error(f"Forecast failed: {e}")
               raise

Debugging Tips
--------------

Enable Debug Logging Selectively
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When debugging issues, enable debug logging only for relevant modules:

.. code-block:: python

   import logging

   # Enable debug for specific module you're investigating
   logging.getLogger('openstef.model.regressors').setLevel(logging.DEBUG)
   
   # Keep everything else at INFO
   logging.getLogger('openstef').setLevel(logging.INFO)

Inspect Logger Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If logs aren't appearing as expected, inspect the logger configuration:

.. code-block:: python

   import logging

   def debug_logger_config(logger_name='openstef'):
       """Print logger configuration for debugging."""
       logger = logging.getLogger(logger_name)
       
       print(f"Logger: {logger_name}")
       print(f"  Level: {logger.level} (effective: {logger.getEffectiveLevel()})")
       print(f"  Handlers: {logger.handlers}")
       print(f"  Propagate: {logger.propagate}")
       
       if logger.parent:
           print(f"  Parent: {logger.parent.name}")
           print(f"  Parent handlers: {logger.parent.handlers}")

   debug_logger_config('openstef')
   debug_logger_config('openstef.model')

Capture Logs in Tests
^^^^^^^^^^^^^^^^^^^^^^

When writing tests, capture logs to verify behavior:

.. code-block:: python

   import logging
   import pytest

   def test_model_training_logs(caplog):
       """Test that model training produces expected logs."""
       from openstef.model.regressors.xgb import XGBOpenstfRegressor
       
       with caplog.at_level(logging.INFO):
           model = XGBOpenstfRegressor()
           # Verify initialization logged
           assert "XGBOpenstfRegressor" in caplog.text

Troubleshooting
---------------

No Log Output Appearing
^^^^^^^^^^^^^^^^^^^^^^^^

If you're not seeing any OpenSTEF log messages:

1. **Check if logging is configured**: OpenSTEF uses ``NullHandler`` by default, so you must configure logging explicitly
2. **Verify log levels**: Ensure your handler level isn't too restrictive
3. **Check logger hierarchy**: Parent logger settings can override child settings

.. code-block:: python

   import logging

   # Verify configuration
   logger = logging.getLogger('openstef')
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
   logging.getLogger('openstef').setLevel(logging.WARNING)
   
   # Or disable specific noisy modules
   logging.getLogger('openstef.feature_engineering.weather_features').setLevel(logging.ERROR)

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging can impact performance in tight loops. Use lazy evaluation for expensive log messages:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   # Bad: String formatting happens even if DEBUG is disabled
   logger.debug(f"Processing data: {expensive_computation()}")

   # Good: Formatting only happens if DEBUG is enabled
   logger.debug("Processing data: %s", expensive_computation())

   # Even better: Check level before expensive operations
   if logger.isEnabledFor(logging.DEBUG):
       result = expensive_computation()
       logger.debug("Processing data: %s", result)

See Also
--------

For related topics, see:

- :doc:`deployment` - Production deployment patterns including monitoring and observability
- :doc:`use_cases` - Common use cases with practical examples
- :doc:`data_integration` - Data integration patterns for different data sources