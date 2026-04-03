Logging Configuration
=====================

OpenSTEF uses Python's standard logging module to provide visibility into library operations. As a library, OpenSTEF follows best practices by using ``NullHandler`` by default, giving you complete control over how and where log messages appear. This page covers how to configure logging for different environments, integrate with production logging systems, and troubleshoot common issues.

Overview
--------

OpenSTEF's logging system provides:

- **Standard Python logging**: Uses the built-in logging module for compatibility
- **Package-level loggers**: Separate loggers for ``openstef_models``, ``openstef_beam``, and other packages
- **Granular control**: Configure different log levels for different components
- **Structured context**: Log messages include contextual information for debugging

Basic Configuration
-------------------

To see OpenSTEF log messages, configure logging in your application:

.. code-block:: python

   import logging

   # Basic configuration - shows INFO level and above
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

   # Now OpenSTEF operations will produce log output
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline

   # Logging will show training progress
   model = train_model_pipeline(data, model_type='xgb')

This basic setup is sufficient for development and data science workflows where you want to see what OpenSTEF is doing.

Log Levels
----------

OpenSTEF uses standard Python logging levels to categorize messages by importance:

- **DEBUG**: Detailed diagnostic information (data shapes, column names, internal states)
- **INFO**: Important operational milestones (processing started/completed, model trained)
- **WARNING**: Unexpected situations that don't prevent execution (missing data, deprecated usage)
- **ERROR**: Serious problems that prevent a function from completing
- **CRITICAL**: Very serious errors that may crash the application

Configure different levels for different use cases:

.. code-block:: python

   import logging

   # Development: See everything including diagnostics
   logging.basicConfig(level=logging.DEBUG)

   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)

   # Data science workflows: Informational messages
   logging.basicConfig(level=logging.INFO)

Logger Hierarchy
----------------

OpenSTEF loggers follow Python's hierarchical naming convention. You can control logging at different levels of granularity:

.. code-block:: python

   import logging

   # Configure all OpenSTEF packages
   logging.getLogger('openstef').setLevel(logging.INFO)

   # Configure specific packages differently
   logging.getLogger('openstef_models').setLevel(logging.INFO)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Disable logging for specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

This hierarchy allows you to reduce noise from verbose components while maintaining visibility into critical operations.

Production Integration
----------------------

Standard logging setup
^^^^^^^^^^^^^^^^^^^^^^

For most production applications, configure logging with appropriate handlers and formatters:

.. code-block:: python

   import logging
   import logging.handlers

   # Create formatter
   formatter = logging.Formatter(
       fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )

   # Console handler for container logs
   console_handler = logging.StreamHandler()
   console_handler.setLevel(logging.INFO)
   console_handler.setFormatter(formatter)

   # File handler with rotation
   file_handler = logging.handlers.RotatingFileHandler(
       filename='openstef.log',
       maxBytes=10485760,  # 10MB
       backupCount=5
   )
   file_handler.setLevel(logging.WARNING)
   file_handler.setFormatter(formatter)

   # Configure root logger
   root_logger = logging.getLogger()
   root_logger.setLevel(logging.INFO)
   root_logger.addHandler(console_handler)
   root_logger.addHandler(file_handler)

   # Optional: Adjust OpenSTEF package levels
   logging.getLogger('openstef_models').setLevel(logging.INFO)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

Structured logging with structlog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production systems that require structured logging, integrate OpenSTEF with `structlog <https://www.structlog.org/>`_:

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
   from openstef.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(data, model_type='xgb')
   # Logs appear as structured JSON

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

Cloud logging integration
^^^^^^^^^^^^^^^^^^^^^^^^^^

When deploying to cloud platforms, integrate with their logging systems:

.. code-block:: python

   import logging
   from google.cloud import logging as gcp_logging

   # Google Cloud Logging
   client = gcp_logging.Client()
   client.setup_logging(log_level=logging.INFO)

   # OpenSTEF logs now appear in Cloud Logging
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(data, model_type='xgb')

For AWS CloudWatch or Azure Monitor, use their respective logging handlers. See the :doc:`deployment` page for environment-specific deployment patterns.

Adding Context to Logs
-----------------------

Using extras for structured context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enhance log messages with structured context using the ``extra`` parameter:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   def train_forecasting_model(data, config):
       """Train a forecasting model with detailed logging context."""
       
       # Add extra context to log messages
       training_context = {
           "model_type": config.model_type,
           "training_samples": len(data),
           "feature_count": len(data.columns),
           "horizon": config.horizon,
       }
       
       logger.info(
           f"Starting model training with {config.model_type}",
           extra={"training_info": training_context}
       )
       
       # Train model
       model = train_model_pipeline(data, **config)
       
       logger.info(
           "Model training completed",
           extra={"training_info": training_context}
       )
       
       return model

Using LoggerAdapter for consistent context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you need the same context across multiple log messages, use ``logging.LoggerAdapter``:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   class ForecastingPipeline:
       """Forecasting pipeline with consistent logging context."""
       
       def __init__(self, pipeline_id, config):
           self.pipeline_id = pipeline_id
           self.config = config
           
           # Create adapter with consistent context
           self.logger = logging.LoggerAdapter(
               logger=logger,
               extra={
                   "pipeline_id": pipeline_id,
                   "model_type": config.model_type,
                   "horizon": config.horizon
               }
           )
       
       def run(self, data):
           """Run the forecasting pipeline."""
           # All log messages automatically include the adapter's extra context
           self.logger.info(f"Starting pipeline on {len(data)} samples")
           
           try:
               model = train_model_pipeline(data, **self.config)
               self.logger.info("Pipeline completed successfully")
               return model
           except Exception as e:
               # Extra context automatically included
               self.logger.error(f"Pipeline failed: {e}")
               raise

This approach ensures consistent context across all operations within a class or workflow.

Debugging Tips
--------------

Enabling debug logging
^^^^^^^^^^^^^^^^^^^^^^^

When troubleshooting issues, enable DEBUG logging to see detailed diagnostic information:

.. code-block:: python

   import logging

   # Enable debug logging for OpenSTEF
   logging.basicConfig(level=logging.DEBUG)
   
   # Or just for specific components
   logging.getLogger('openstef.model').setLevel(logging.DEBUG)
   logging.getLogger('openstef.pipeline').setLevel(logging.DEBUG)
   
   # Now run your code - you'll see detailed information
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(data, model_type='xgb')

Debug logs show data shapes, column names, internal states, and other diagnostic information useful for troubleshooting.

Inspecting logger configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If logging isn't working as expected, inspect the logger configuration:

.. code-block:: python

   import logging

   # Debug logging configuration
   logger = logging.getLogger('openstef')
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers}")

This helps identify configuration issues like missing handlers or incorrect log levels.

Troubleshooting
---------------

No log output appearing
^^^^^^^^^^^^^^^^^^^^^^^

If you're not seeing any OpenSTEF log messages:

1. **Check if logging is configured**: OpenSTEF uses ``NullHandler`` by default, so you must configure logging in your application
2. **Verify log levels**: Ensure your handler level isn't too restrictive
3. **Check logger hierarchy**: Parent logger settings can override child settings

.. code-block:: python

   import logging

   # Ensure logging is configured
   logging.basicConfig(level=logging.INFO)
   
   # Verify OpenSTEF logger level
   openstef_logger = logging.getLogger('openstef')
   print(f"Effective level: {openstef_logger.getEffectiveLevel()}")

Too much log output
^^^^^^^^^^^^^^^^^^^

If OpenSTEF is producing too many log messages:

.. code-block:: python

   import logging

   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)

   # Or disable specific noisy modules
   logging.getLogger('openstef.feature_engineering').setLevel(logging.ERROR)

Performance considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging can impact performance in tight loops. Use appropriate log levels and consider lazy evaluation:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   # Inefficient - string formatting happens even if DEBUG is disabled
   for i in range(1000000):
       logger.debug(f"Processing item {i} with data {expensive_operation()}")

   # Efficient - check level first
   for i in range(1000000):
       if logger.isEnabledFor(logging.DEBUG):
           logger.debug(f"Processing item {i} with data {expensive_operation()}")

   # Or use lazy formatting
   for i in range(1000000):
       logger.debug("Processing item %s with data %s", i, expensive_operation())

In production, set log levels to WARNING or ERROR to minimize performance impact.

Best Practices
--------------

Follow these guidelines for effective logging:

1. **Use appropriate log levels**: DEBUG for diagnostics, INFO for milestones, WARNING for unexpected situations, ERROR for failures
2. **Include context**: Add structured context using ``extra`` or ``LoggerAdapter`` to make logs searchable
3. **Don't log sensitive data**: Avoid logging passwords, API keys, or personally identifiable information
4. **Use logger names**: Create module-level loggers with ``logger = logging.getLogger(__name__)``
5. **Configure once**: Set up logging at application startup, not in library code
6. **Test logging configuration**: Verify logs appear correctly in your target environment

See Also
--------

- :doc:`deployment` - Production deployment patterns including logging configuration for different environments
- :doc:`data_integration` - Data integration patterns that benefit from logging visibility
- :doc:`use_cases` - Common use cases showing logging in context