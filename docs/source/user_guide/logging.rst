Logging
=======

OpenSTEF uses Python's standard logging library to provide visibility into forecasting operations. The library follows a no-default-output approach, giving you complete control over how logging is handled in your application.

Overview
========

OpenSTEF follows these logging principles:

- **No default output**: Uses ``NullHandler`` by default, so no log messages appear unless you configure logging
- **Standard library**: Uses Python's built-in ``logging`` module for consistency and compatibility
- **Hierarchical loggers**: Package-level and module-level loggers allow granular control
- **Structured context**: Log messages include contextual information for debugging and monitoring

This design ensures OpenSTEF integrates seamlessly with your existing logging infrastructure without imposing its own configuration.

Basic Configuration
===================

To see OpenSTEF log messages, configure logging in your application before using the library:

.. code-block:: python

   import logging

   # Basic configuration - shows INFO level and above
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   # Now OpenSTEF operations will produce log output
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   
   model = XGBQuantileOpenstfRegressor()
   # Logs initialization details at INFO level

For production environments, you'll typically want more control over formatting and output destinations:

.. code-block:: python

   import logging
   import sys

   # Configure root logger with custom formatting
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S',
       handlers=[
           logging.StreamHandler(sys.stdout),
           logging.FileHandler('openstef_forecasting.log')
       ]
   )

   # Adjust OpenSTEF-specific log levels
   logging.getLogger('openstef').setLevel(logging.INFO)

Log Levels
==========

OpenSTEF uses standard Python log levels appropriately:

- **DEBUG**: Detailed diagnostic information useful during development and troubleshooting
- **INFO**: Confirmation that operations are working as expected (model training progress, prediction completion)
- **WARNING**: Something unexpected happened but the operation can continue
- **ERROR**: A serious problem prevented an operation from completing
- **CRITICAL**: A severe error that may prevent the library from functioning

Recommended levels by use case:

- **Development**: ``DEBUG`` to see detailed operation flow
- **Production monitoring**: ``INFO`` to track forecasting operations
- **Production stable**: ``WARNING`` to reduce log volume while catching issues

Granular Control
================

OpenSTEF's hierarchical logger structure allows you to control logging at different levels of granularity.

Package-level control
---------------------

Control logging for entire OpenSTEF packages:

.. code-block:: python

   import logging

   # Show only warnings from OpenSTEF
   logging.getLogger('openstef').setLevel(logging.WARNING)

   # Enable debug mode for model-related operations
   logging.getLogger('openstef.model').setLevel(logging.DEBUG)

   # Suppress verbose output from feature engineering
   logging.getLogger('openstef.feature_engineering').setLevel(logging.ERROR)

Module-level control
--------------------

For even finer control, target specific modules:

.. code-block:: python

   import logging

   # Debug specific model types
   logging.getLogger('openstef.model.regressors.xgb').setLevel(logging.DEBUG)

   # Reduce verbosity of data validation
   logging.getLogger('openstef.validation').setLevel(logging.WARNING)

   # Only show errors from serialization
   logging.getLogger('openstef.model.serializer').setLevel(logging.ERROR)

This granularity is particularly useful when debugging specific components without being overwhelmed by logs from other parts of the library.

Production Integration
======================

OpenSTEF integrates with common production logging patterns.

JSON structured logging
-----------------------

For systems that consume structured logs (e.g., ELK stack, Splunk):

.. code-block:: python

   import logging
   import json
   import sys

   class JSONFormatter(logging.Formatter):
       """Format log records as JSON for structured logging systems."""
       
       def format(self, record):
           log_data = {
               'timestamp': self.formatTime(record),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
           }
           
           # Include extra fields if present
           if hasattr(record, 'training_info'):
               log_data['training_info'] = record.training_info
           if hasattr(record, 'performance_info'):
               log_data['performance_info'] = record.performance_info
               
           return json.dumps(log_data)

   # Configure handler with JSON formatter
   handler = logging.StreamHandler(sys.stdout)
   handler.setFormatter(JSONFormatter())
   
   logger = logging.getLogger('openstef')
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

Rotating file handlers
----------------------

For long-running forecasting services, use rotating file handlers to manage log file size:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Rotate logs at 10MB, keep 5 backup files
   handler = RotatingFileHandler(
       'openstef_forecasts.log',
       maxBytes=10*1024*1024,  # 10MB
       backupCount=5
   )
   handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))

   logging.getLogger('openstef').addHandler(handler)
   logging.getLogger('openstef').setLevel(logging.INFO)

Cloud logging integration
-------------------------

Integration with cloud logging services (AWS CloudWatch, Google Cloud Logging, Azure Monitor):

.. code-block:: python

   import logging
   import watchtower  # AWS CloudWatch handler

   # Configure CloudWatch handler
   cloudwatch_handler = watchtower.CloudWatchLogHandler(
       log_group='openstef-forecasting',
       stream_name='production'
   )
   
   logging.getLogger('openstef').addHandler(cloudwatch_handler)
   logging.getLogger('openstef').setLevel(logging.INFO)

See the :doc:`deployment` guide for more production deployment patterns.

Contextual Information
======================

OpenSTEF includes contextual information in log messages to aid debugging and monitoring.

Using log extras
----------------

Add structured context to log messages using the ``extra`` parameter:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)

   def train_forecast_model(data, config):
       """Train a forecasting model with detailed logging context."""
       
       # Add context to log messages
       training_context = {
           "model_type": config.model_type,
           "training_samples": len(data),
           "horizon_hours": config.horizon,
           "validation_split": config.validation_split
       }
       
       logger.info(
           f"Starting model training with {config.model_type}",
           extra={"training_info": training_context}
       )
       
       # Train model...
       model = fit_model(data, config)
       
       # Log performance metrics with context
       performance_context = {
           "training_time_seconds": model.training_time,
           "model_size_mb": model.size_mb,
           "final_score": model.validation_score
       }
       
       logger.info(
           "Model training completed",
           extra={"performance_info": performance_context}
       )
       
       return model

Benefits of structured context:

- **Filtering**: Filter logs by model type, data size, or other attributes
- **Monitoring**: Production systems can alert on specific conditions
- **Debugging**: Rich context helps identify issues without code changes
- **Log processing**: Structured data integrates with log aggregation systems

Using LoggerAdapter
-------------------

For consistent context across multiple log messages, use ``LoggerAdapter``:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   class ForecastingPipeline:
       """Forecasting pipeline with consistent logging context."""
       
       def __init__(self, config):
           self.config = config
           
           # Create adapter with consistent context
           self.logger = logging.LoggerAdapter(
               logger=logger,
               extra={
                   "pipeline_id": config.pipeline_id,
                   "prediction_type": config.prediction_type,
                   "location": config.location_name
               }
           )
       
       def run_forecast(self, data):
           """Execute forecasting pipeline."""
           # All log messages include the adapter's extra context
           self.logger.info(f"Starting forecast for {len(data)} time steps")
           
           try:
               predictions = self._generate_predictions(data)
               self.logger.info(f"Forecast completed: {len(predictions)} predictions")
               return predictions
           except Exception as e:
               # Extra context automatically included in error logs
               self.logger.error(f"Forecast failed: {e}", exc_info=True)
               raise

This approach ensures consistent context without repeating ``extra`` parameters in every log call.

Debugging Tips
==============

Common debugging scenarios and solutions.

No log output appearing
-----------------------

If you're not seeing OpenSTEF log messages:

1. **Check if logging is configured**: OpenSTEF uses ``NullHandler`` by default
2. **Verify log levels**: Ensure your handler level isn't too restrictive
3. **Check logger hierarchy**: Parent logger settings can override child settings

.. code-block:: python

   import logging

   # Debug logging configuration
   logger = logging.getLogger('openstef')
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
   logging.getLogger('openstef').setLevel(logging.WARNING)

   # Or disable specific noisy modules
   logging.getLogger('openstef.validation').setLevel(logging.ERROR)
   logging.getLogger('openstef.feature_engineering.apply_features').setLevel(logging.WARNING)

Performance considerations
--------------------------

Logging can impact performance in tight loops. OpenSTEF follows best practices:

- Log messages are not formatted unless actually output
- Debug logging is conditionally executed
- Structured logging uses lazy evaluation

You can further optimize by setting appropriate levels:

.. code-block:: python

   import logging

   # Set appropriate levels to avoid unnecessary processing
   logging.getLogger('openstef').setLevel(logging.WARNING)

   # Use logging filters for fine-grained control
   class PerformanceFilter(logging.Filter):
       def filter(self, record):
           # Skip debug messages during performance-critical sections
           return record.levelno >= logging.INFO

   logging.getLogger('openstef').addFilter(PerformanceFilter())

Testing with logging
--------------------

When writing tests that use OpenSTEF, use pytest's ``caplog`` fixture to capture and verify log messages:

.. code-block:: python

   import logging
   import pytest

   def test_model_training_logs_progress(caplog):
       """Verify that model training produces expected log messages."""
       
       with caplog.at_level(logging.INFO):
           model = train_forecaster(sample_data, sample_config)
       
       # Verify expected log messages
       assert "Starting model training" in caplog.text
       assert "Model training completed" in caplog.text
       
       # Verify log levels
       info_messages = [
           record for record in caplog.records 
           if record.levelno == logging.INFO
       ]
       assert len(info_messages) >= 2

Best Practices
==============

Recommended practices for OpenSTEF logging:

1. **Configure logging early**: Set up logging before importing OpenSTEF modules
2. **Use appropriate levels**: INFO for general monitoring, DEBUG for troubleshooting
3. **Leverage hierarchical control**: Use package/module-level logger configuration
4. **Add context**: Use ``extra`` parameters or ``LoggerAdapter`` for structured information
5. **Integrate with existing systems**: OpenSTEF works with any Python logging configuration

Complete setup example
----------------------

.. code-block:: python

   import logging
   import sys

   def setup_openstef_logging(level=logging.INFO, log_file=None):
       """Set up logging for OpenSTEF integration."""
       
       # Create handlers
       handlers = [logging.StreamHandler(sys.stdout)]
       if log_file:
           handlers.append(logging.FileHandler(log_file))
       
       # Basic configuration
       logging.basicConfig(
           level=level,
           format='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S',
           handlers=handlers
       )
       
       # Fine-tune OpenSTEF packages
       logging.getLogger('openstef').setLevel(level)
       
       # Reduce verbosity of dependencies if needed
       logging.getLogger('urllib3').setLevel(logging.WARNING)
       logging.getLogger('matplotlib').setLevel(logging.WARNING)

   # Use in your application
   setup_openstef_logging(
       level=logging.INFO,
       log_file='openstef_forecasts.log'
   )

   # Now use OpenSTEF with proper logging
   from openstef.pipeline.train_model import train_model_pipeline
   
   result = train_model_pipeline(pj, input_data)

For advanced logging configurations like custom formatters, filters, and handlers, refer to the official `Python logging documentation <https://docs.python.org/3/library/logging.html>`_.

See Also
========

- :doc:`deployment` - Production deployment patterns and monitoring
- :doc:`data_integration` - Data pipeline integration patterns
- :doc:`use_cases` - Common OpenSTEF use cases with examples