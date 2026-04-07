Logging
=======

OpenSTEF uses Python's standard logging module to provide visibility into library operations. This page explains how to configure logging for different environments, control log output, integrate with production logging systems, and debug common issues.

As a library, OpenSTEF does not configure logging by itself—it's your application's responsibility to set up logging handlers and levels. OpenSTEF follows Python logging best practices by using named loggers and attaching a ``NullHandler`` by default, ensuring no output unless you explicitly configure it.

Basic Configuration
-------------------

To see OpenSTEF log messages, configure logging in your application before importing OpenSTEF components:

.. code-block:: python

   import logging
   
   # Basic configuration - shows INFO level and above
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   
   # Now OpenSTEF operations will produce log output
   from openstef_models.forecasting import LinearForecaster
   
   forecaster = LinearForecaster()  # Will log initialization details

This basic setup is sufficient for development and data science workflows. For production deployments, see :doc:`deployment` for more sophisticated logging configurations.

Log Levels
----------

OpenSTEF uses standard Python logging levels to categorize messages by importance:

- **DEBUG**: Detailed diagnostic information, typically only useful when diagnosing problems. Includes data shapes, intermediate computation results, and algorithm steps.
- **INFO**: General information about program execution. Confirms that operations are proceeding as expected (e.g., "Model training started", "Prediction completed").
- **WARNING**: Something unexpected happened, but the software is still working. May indicate suboptimal conditions (e.g., "Missing features filled with defaults").
- **ERROR**: A serious problem occurred that prevented a function from completing. The library will typically raise an exception alongside the error log.
- **CRITICAL**: A very serious error that may prevent the program from continuing. Rarely used in library code.

Configure different log levels based on your environment:

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

OpenSTEF loggers follow Python's hierarchical naming convention. The main logger namespaces are:

- ``openstef_models``: Core forecasting models and algorithms
- ``openstef_beam``: Apache Beam pipeline components
- ``openstef_models.transforms``: Data transformation modules
- ``openstef_models.integrations``: Third-party integrations (MLflow, etc.)

You can control logging at different levels of granularity:

.. code-block:: python

   import logging
   
   # Control all OpenSTEF logging
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   
   # Fine-grained control for specific modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)
   logging.getLogger('openstef_models.integrations.mlflow').setLevel(logging.DEBUG)
   
   # Keep other modules at INFO
   logging.getLogger('openstef_beam').setLevel(logging.INFO)

This hierarchical approach allows you to reduce noise from verbose modules while maintaining detailed logging for areas you're actively debugging.

Custom Handlers
---------------

For production systems, you'll typically want to send logs to multiple destinations: console for immediate feedback, files for persistence, and external systems for aggregation and monitoring.

File Logging
^^^^^^^^^^^^

Write logs to rotating files to prevent disk space issues:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler
   
   # Create a rotating file handler (10MB per file, keep 5 backups)
   file_handler = RotatingFileHandler(
       'openstef.log',
       maxBytes=10 * 1024 * 1024,  # 10MB
       backupCount=5
   )
   file_handler.setLevel(logging.INFO)
   file_handler.setFormatter(logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   ))
   
   # Attach to OpenSTEF loggers
   logging.getLogger('openstef_models').addHandler(file_handler)
   logging.getLogger('openstef_beam').addHandler(file_handler)

JSON Structured Logging
^^^^^^^^^^^^^^^^^^^^^^^^

Structured logs are easier to parse and query in production logging systems:

.. code-block:: python

   import logging
   import json
   from datetime import datetime
   
   class JSONFormatter(logging.Formatter):
       """Format log records as JSON for structured logging."""
       
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
           if hasattr(record, 'model_id'):
               log_data['model_id'] = record.model_id
           if hasattr(record, 'prediction_id'):
               log_data['prediction_id'] = record.prediction_id
           
           return json.dumps(log_data)
   
   # Configure handler with JSON formatter
   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())
   logging.getLogger('openstef_models').addHandler(handler)

Integration with Production Systems
------------------------------------

Cloud Logging
^^^^^^^^^^^^^

For cloud deployments, integrate with platform-specific logging services:

.. code-block:: python

   import logging
   
   # Google Cloud Logging
   from google.cloud import logging as gcp_logging
   
   client = gcp_logging.Client()
   handler = client.get_default_handler()
   
   logger = logging.getLogger('openstef_models')
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

.. code-block:: python

   # AWS CloudWatch Logs
   import watchtower
   import logging
   
   handler = watchtower.CloudWatchLogHandler(
       log_group='openstef-forecasting',
       stream_name='production'
   )
   
   logger = logging.getLogger('openstef_models')
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

Centralized Logging Systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For systems like ELK Stack, Splunk, or Datadog, use their Python handlers:

.. code-block:: python

   # Example: Logstash integration
   import logging
   from logstash_async.handler import AsynchronousLogstashHandler
   
   handler = AsynchronousLogstashHandler(
       host='logstash.example.com',
       port=5959,
       database_path='logstash.db'
   )
   
   logger = logging.getLogger('openstef_models')
   logger.addHandler(handler)

Contextual Logging
------------------

Add context to log messages to make them more useful for debugging and monitoring:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   def train_model(model_id: str, data):
       # Use LoggerAdapter to add context to all messages
       adapter = logging.LoggerAdapter(logger, {'model_id': model_id})
       
       adapter.info("Starting model training")
       # All subsequent log messages will include model_id
       
       try:
           result = perform_training(data)
           adapter.info("Training completed successfully", 
                       extra={'num_samples': len(data), 'rmse': result.rmse})
       except Exception as e:
           adapter.error("Training failed", exc_info=True)
           raise

Debugging Tips
--------------

Missing Log Messages
^^^^^^^^^^^^^^^^^^^^

If you're not seeing expected log output, check these common issues:

1. **Logging not configured**: OpenSTEF uses ``NullHandler`` by default, so you must configure logging explicitly
2. **Log level too restrictive**: Ensure your handler level isn't filtering out messages
3. **Logger hierarchy issues**: Parent logger settings can override child settings

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

If OpenSTEF is producing excessive log messages:

.. code-block:: python

   import logging
   
   # Reduce OpenSTEF verbosity
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.WARNING)
   
   # Or disable specific noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging can impact performance in tight loops or with expensive operations:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   def process_large_dataset(data):
       # Bad: Expensive operation in log argument (always evaluated)
       # logger.debug(f"Data summary: {data.describe().to_string()}")
       
       # Good: Conditional expensive logging
       if logger.isEnabledFor(logging.DEBUG):
           logger.debug(f"Data summary: {data.describe().to_string()}")
       
       for chunk in process_in_chunks(data):
           # Good: Minimal context for frequent operations
           logger.debug("Processed chunk of size %d", len(chunk))
       
       logger.info("Processing completed")
       return data

**Performance guidelines:**

- Use ``logger.isEnabledFor(level)`` for expensive debug operations
- Prefer ``%`` formatting over f-strings in log calls for lazy evaluation
- Avoid expensive computations in log message arguments
- Use appropriate log levels to control output volume

Error Handling with Logging
----------------------------

Combine proper exception handling with informative logging:

.. code-block:: python

   import logging
   from pathlib import Path
   
   logger = logging.getLogger(__name__)
   
   def load_data(file_path: Path):
       """Load data with error handling and logging."""
       logger.info(f"Loading data from {file_path}")
       
       try:
           if not file_path.exists():
               raise FileNotFoundError(f"Data file not found: {file_path}")
           
           logger.debug(f"File size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
           
           data = pd.read_csv(file_path)
           logger.info(f"Successfully loaded {len(data)} rows, {len(data.columns)} columns")
           
           return data
           
       except FileNotFoundError:
           logger.error(f"File not found: {file_path}")
           raise
       except pd.errors.ParserError as e:
           logger.error(f"Failed to parse CSV file: {e}", exc_info=True)
           raise
       except Exception as e:
           logger.critical(f"Unexpected error loading data: {e}", exc_info=True)
           raise

The ``exc_info=True`` parameter includes the full traceback in the log output, which is invaluable for debugging production issues.

Related Topics
--------------

- :doc:`deployment` - Production deployment patterns including logging infrastructure
- :doc:`data_integration` - Data loading patterns that benefit from proper logging
- :doc:`use_cases` - Practical examples showing logging in context