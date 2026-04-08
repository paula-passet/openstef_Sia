Logging
=======

OpenSTEF uses Python's standard logging library to provide visibility into its operations. As a library, OpenSTEF does not configure logging by default—it uses a ``NullHandler`` to give you complete control over how logging is handled in your application.

This page covers how to configure logging for OpenSTEF, integrate it with production logging systems, and troubleshoot common issues.

Basic Configuration
===================

To see OpenSTEF log messages, configure Python's logging module in your application before importing OpenSTEF:

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

For development and debugging, use ``DEBUG`` level to see detailed diagnostic information:

.. code-block:: python

   import logging

   # Development: See everything
   logging.basicConfig(level=logging.DEBUG)

For production environments, use ``WARNING`` or ``ERROR`` to reduce noise:

.. code-block:: python

   import logging

   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)

Understanding Log Levels
=========================

OpenSTEF uses standard Python logging levels with the following conventions:

* **DEBUG**: Detailed diagnostic information (data shapes, column names, internal states)
* **INFO**: Important operational milestones (processing started/completed, model trained)
* **WARNING**: Unexpected situations that don't prevent execution (missing data, deprecated usage)
* **ERROR**: Serious problems that prevent a function from completing
* **CRITICAL**: Very serious errors that may crash the application (rarely used)

Example showing appropriate usage:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)

   def process_forecast_data(data):
       # DEBUG: Detailed diagnostic information
       logger.debug(f"Processing {len(data)} samples")
       logger.debug(f"Date range: {data.index.min()} to {data.index.max()}")
       
       # INFO: Important operational information
       logger.info(f"Starting data processing for {len(data)} samples")
       
       # WARNING: Something unexpected but recoverable
       missing_count = data.isnull().sum().sum()
       if missing_count > 0:
           logger.warning(f"Found {missing_count} missing values, will interpolate")
           data = data.interpolate()
       
       try:
           processed_data = apply_transformations(data)
           logger.info("Data processing completed successfully")
           return processed_data
       except ValueError as e:
           # ERROR: Serious problem that prevents completion
           logger.error(f"Data processing failed: {e}")
           raise

Logger Hierarchy
================

OpenSTEF loggers follow Python's hierarchical naming convention. You can control logging at different granularity levels:

.. code-block:: python

   import logging

   # Control all OpenSTEF logging
   logging.getLogger('openstef_models').setLevel(logging.INFO)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Fine-tune specific modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)
   logging.getLogger('openstef_models.forecasters').setLevel(logging.DEBUG)

This hierarchical control is particularly useful when debugging specific components without being overwhelmed by logs from other parts of the library.

Production Logging Integration
===============================

File-based logging
------------------

For production deployments, you typically want to log to files with rotation:

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

   # Add handler to OpenSTEF loggers
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_beam').addHandler(handler)

JSON logging for structured output
-----------------------------------

Many production systems use JSON-formatted logs for easier parsing and analysis:

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
           
           # Include extra fields if present
           if hasattr(record, 'extra_fields'):
               log_data.update(record.extra_fields)
           
           return json.dumps(log_data)

   # Configure handler with JSON formatter
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger('openstef_models').addHandler(handler)
   logging.getLogger('openstef_models').setLevel(logging.INFO)

Integration with structlog
---------------------------

If you're using `structlog <https://www.structlog.org/>`_ in your application, OpenSTEF integrates seamlessly through Python's standard logging:

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

Adding Context to Logs
======================

Enhance log messages with structured context using the ``extra`` parameter:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)

   def train_model(data, config):
       """Train a forecasting model with detailed logging context."""
       
       # Add context to log messages
       logger.info(
           "Starting model training",
           extra={
               'model_type': config.model_type,
               'data_samples': len(data),
               'feature_count': data.shape[1],
               'training_period': f"{data.index.min()} to {data.index.max()}"
           }
       )
       
       # Train model...
       model = fit_model(data, config)
       
       logger.info(
           "Model training completed",
           extra={
               'model_type': config.model_type,
               'training_score': model.score,
               'training_duration_seconds': model.training_time
           }
       )
       
       return model

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
                   'pipeline_id': config.pipeline_id,
                   'model_type': config.model_type
               }
           )
       
       def run(self, data):
           """Run forecasting pipeline."""
           # All log messages include pipeline_id and model_type
           self.logger.info(f"Starting pipeline with {len(data)} samples")
           
           try:
               result = self._process(data)
               self.logger.info("Pipeline completed successfully")
               return result
           except Exception as e:
               self.logger.error(f"Pipeline failed: {e}")
               raise

Debugging Tips
==============

Enabling debug logging
----------------------

When troubleshooting issues, enable DEBUG logging for OpenSTEF components:

.. code-block:: python

   import logging

   # Enable debug logging for all OpenSTEF
   logging.getLogger('openstef_models').setLevel(logging.DEBUG)
   logging.getLogger('openstef_beam').setLevel(logging.DEBUG)

   # Or just for specific modules
   logging.getLogger('openstef_models.forecasters').setLevel(logging.DEBUG)

Diagnosing logging configuration
---------------------------------

If you're not seeing expected log messages, diagnose the configuration:

.. code-block:: python

   import logging

   logger = logging.getLogger('openstef_models')
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers}")

Common issues:

1. **No log output appearing**: OpenSTEF uses ``NullHandler`` by default—you must configure logging
2. **Log level too restrictive**: Ensure your handler level isn't filtering out messages
3. **Logger hierarchy issues**: Parent logger settings can override child settings

Reducing log verbosity
----------------------

If OpenSTEF produces too many log messages in production:

.. code-block:: python

   import logging

   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Or disable specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Performance Considerations
==========================

Logging can impact performance in tight loops. OpenSTEF follows best practices to minimize overhead:

* Log messages are not formatted unless actually output
* Debug logging is conditionally executed
* Structured logging uses lazy evaluation

You can further optimize by setting appropriate log levels:

.. code-block:: python

   import logging

   # Set appropriate levels to avoid unnecessary processing
   logging.getLogger('openstef_models').setLevel(logging.WARNING)

For fine-grained control, use logging filters:

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

1. **Configure logging early**: Set up logging before importing OpenSTEF modules
2. **Use appropriate levels**: INFO for general monitoring, DEBUG for troubleshooting
3. **Leverage hierarchical control**: Use package/module-level logger configuration for granular control
4. **Add context**: Use ``extra`` parameters or ``LoggerAdapter`` to enrich log messages
5. **Integrate with existing systems**: OpenSTEF works with any Python logging configuration

Complete setup example:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   def setup_openstef_logging(level=logging.INFO, log_file=None):
       """Set up logging for OpenSTEF integration."""
       
       # Create formatter
       formatter = logging.Formatter(
           '%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
           datefmt='%Y-%m-%d %H:%M:%S'
       )
       
       # Console handler
       console_handler = logging.StreamHandler()
       console_handler.setFormatter(formatter)
       console_handler.setLevel(level)
       
       # Configure OpenSTEF loggers
       for logger_name in ['openstef_models', 'openstef_beam']:
           logger = logging.getLogger(logger_name)
           logger.setLevel(level)
           logger.addHandler(console_handler)
       
       # Optional file handler
       if log_file:
           file_handler = RotatingFileHandler(
               log_file,
               maxBytes=10*1024*1024,
               backupCount=5
           )
           file_handler.setFormatter(formatter)
           file_handler.setLevel(level)
           
           for logger_name in ['openstef_models', 'openstef_beam']:
               logging.getLogger(logger_name).addHandler(file_handler)

   # Use in your application
   setup_openstef_logging(level=logging.INFO, log_file='openstef.log')

See Also
========

* :doc:`deployment` - Production deployment patterns including monitoring and observability
* :doc:`data_integration` - Data integration patterns that benefit from detailed logging
* :doc:`use_cases` - Common use cases with logging examples