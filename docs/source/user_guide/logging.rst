Logging Configuration
======================

OpenSTEF uses Python's standard logging module to provide visibility into library operations. As a library, OpenSTEF doesn't configure logging itself—it's your responsibility to set up logging handlers and levels in your application. This page covers how to configure logging for OpenSTEF, adjust verbosity for different environments, integrate with production logging systems, and troubleshoot common logging issues.

Understanding OpenSTEF's Logging Approach
------------------------------------------

OpenSTEF follows Python library best practices by using ``NullHandler`` by default. This means the library will emit log messages, but won't produce any output unless you explicitly configure logging in your application. This design gives you complete control over where logs go and what gets logged.

OpenSTEF uses a hierarchical logger structure with package-level and module-level loggers:

- ``openstef_models``: Core forecasting models and algorithms
- ``openstef_beam``: Apache Beam pipeline components
- ``openstef_models.transforms``: Data transformation operations
- Other module-specific loggers for fine-grained control

This hierarchy allows you to control logging verbosity at different levels of granularity.

Basic Configuration
-------------------

To see OpenSTEF log messages, configure Python's logging module before using the library:

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

This simple setup is sufficient for development and exploratory work. For production deployments, you'll typically want more sophisticated configurations.

Log Levels and Use Cases
-------------------------

OpenSTEF uses standard Python logging levels. Choose the appropriate level based on your environment:

**DEBUG**: Detailed diagnostic information including data shapes, intermediate values, and algorithm steps. Useful when diagnosing problems or understanding model behavior. Can be verbose.

**INFO**: General information about operations—model training progress, data loading, feature engineering steps. Appropriate for data science workflows and development.

**WARNING**: Unexpected situations that don't prevent operation—missing optional features, deprecated parameters, data quality issues. Good default for production.

**ERROR**: Serious problems that prevented a function from completing—invalid data, failed model training, missing required inputs.

**CRITICAL**: Very serious errors that may prevent the program from continuing—unrecoverable failures.

Example configurations for different environments:

.. code-block:: python

   import logging
   
   # Development: See everything
   logging.basicConfig(level=logging.DEBUG)
   
   # Production: Important messages only
   logging.basicConfig(level=logging.WARNING)
   
   # Data science workflows: Informational messages
   logging.basicConfig(level=logging.INFO)

Controlling Verbosity
---------------------

You can adjust logging verbosity for specific OpenSTEF components without affecting other packages:

.. code-block:: python

   import logging
   
   # Set global level
   logging.basicConfig(level=logging.INFO)
   
   # Reduce verbosity for specific OpenSTEF packages
   logging.getLogger('openstef_models').setLevel(logging.WARNING)
   logging.getLogger('openstef_beam').setLevel(logging.ERROR)
   
   # Or increase verbosity for debugging specific modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.DEBUG)

This is particularly useful when OpenSTEF is one of many libraries in your application—you can keep OpenSTEF quiet while debugging other components, or vice versa.

If OpenSTEF is producing too many log messages in tight loops or data processing operations:

.. code-block:: python

   import logging
   
   # Silence noisy modules
   logging.getLogger('openstef_models.transforms').setLevel(logging.ERROR)
   
   # Or disable entirely (not recommended for production)
   logging.getLogger('openstef_models').disabled = True

Custom Handlers
---------------

For production systems, you'll typically want to send logs to files, centralized logging systems, or monitoring platforms. Python's logging module supports multiple handlers simultaneously:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler, SysLogHandler
   
   # Create formatters
   detailed_formatter = logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )
   
   # Console handler for development
   console_handler = logging.StreamHandler()
   console_handler.setLevel(logging.INFO)
   console_handler.setFormatter(detailed_formatter)
   
   # File handler with rotation
   file_handler = RotatingFileHandler(
       'openstef_forecasting.log',
       maxBytes=10*1024*1024,  # 10 MB
       backupCount=5
   )
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(detailed_formatter)
   
   # Configure root logger
   root_logger = logging.getLogger()
   root_logger.setLevel(logging.DEBUG)
   root_logger.addHandler(console_handler)
   root_logger.addHandler(file_handler)
   
   # Now OpenSTEF logs go to both console and file
   from openstef_models import XGBoostForecaster
   
   model = XGBoostForecaster()

Integration with Production Logging Systems
--------------------------------------------

Structured Logging with structlog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your application uses `structlog <https://www.structlog.org/>`_ for structured logging, OpenSTEF integrates seamlessly through Python's standard logging:

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
   
   # Now OpenSTEF logs will be processed by structlog as JSON
   from openstef_models import create_forecaster
   
   forecaster = create_forecaster()

This produces structured JSON logs that are easy to parse and query in centralized logging systems like ELK Stack, Splunk, or CloudWatch.

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

Cloud and Container Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In containerized or cloud environments, you typically want logs to go to stdout/stderr for collection by the orchestration platform:

.. code-block:: python

   import logging
   import sys
   import json
   
   class JSONFormatter(logging.Formatter):
       """Format logs as JSON for cloud logging systems."""
       
       def format(self, record):
           log_data = {
               'timestamp': self.formatTime(record),
               'level': record.levelname,
               'logger': record.name,
               'message': record.getMessage(),
           }
           
           if record.exc_info:
               log_data['exception'] = self.formatException(record.exc_info)
           
           return json.dumps(log_data)
   
   # Configure for cloud environment
   handler = logging.StreamHandler(sys.stdout)
   handler.setFormatter(JSONFormatter())
   
   logging.root.addHandler(handler)
   logging.root.setLevel(logging.INFO)

This approach works well with Kubernetes, AWS ECS, Google Cloud Run, and similar platforms that collect container stdout.

Debugging Tips
--------------

Diagnosing Logging Issues
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're not seeing expected log output, check the logging configuration:

.. code-block:: python

   import logging
   
   # Debug logging configuration
   logger = logging.getLogger('openstef_models')
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers}")

Common issues:

1. **No handlers configured**: OpenSTEF uses ``NullHandler`` by default
2. **Log level too restrictive**: Handler or logger level filters out messages
3. **Parent logger settings**: Hierarchical settings can override child loggers

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Logging can impact performance, especially in tight loops or with expensive operations. Use conditional logging for expensive debug operations:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   def process_large_dataset(data):
       logger.info("Starting data processing")
       
       # Bad: Always computes expensive string formatting
       # logger.debug(f"Data summary: {data.describe().to_string()}")
       
       # Good: Only computes if DEBUG is enabled
       if logger.isEnabledFor(logging.DEBUG):
           logger.debug(f"Data summary: {data.describe().to_string()}")
       
       for chunk in process_in_chunks(data):
           # Good: Minimal context for frequent operations
           logger.debug("Processed chunk of size %d", len(chunk))
       
       logger.info("Processing completed")
       return processed_data

Performance guidelines:

- Use ``logger.isEnabledFor(level)`` for expensive debug operations
- Prefer ``%`` formatting over f-strings in log calls for lazy evaluation
- Avoid expensive computations in log message arguments
- Use appropriate log levels to control output volume

Error Handling with Logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Combine exception handling with informative logging:

.. code-block:: python

   import logging
   from pathlib import Path
   
   logger = logging.getLogger(__name__)
   
   def load_training_data(file_path: Path):
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
           logger.error(f"Data file not found: {file_path}")
           raise
       except pd.errors.EmptyDataError:
           logger.error(f"Data file is empty: {file_path}")
           raise
       except Exception as e:
           logger.exception(f"Unexpected error loading data from {file_path}")
           raise

The ``logger.exception()`` method automatically includes the full traceback, which is invaluable for debugging production issues.

Complete Setup Example
----------------------

Here's a complete logging setup function you can adapt for your application:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler
   
   def setup_openstef_logging(
       level=logging.INFO,
       log_file=None,
       json_format=False
   ):
       """Set up logging for OpenSTEF integration.
       
       Args:
           level: Logging level (default: INFO)
           log_file: Optional file path for log output
           json_format: Use JSON formatting for structured logs
       """
       # Choose formatter
       if json_format:
           formatter = JSONFormatter()
       else:
           formatter = logging.Formatter(
               '%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S'
           )
       
       # Console handler
       console_handler = logging.StreamHandler()
       console_handler.setLevel(level)
       console_handler.setFormatter(formatter)
       
       # Configure root logger
       root_logger = logging.getLogger()
       root_logger.setLevel(level)
       root_logger.addHandler(console_handler)
       
       # Optional file handler
       if log_file:
           file_handler = RotatingFileHandler(
               log_file,
               maxBytes=10*1024*1024,
               backupCount=5
           )
           file_handler.setLevel(logging.DEBUG)
           file_handler.setFormatter(formatter)
           root_logger.addHandler(file_handler)
       
       # Fine-tune OpenSTEF packages
       logging.getLogger('openstef_models').setLevel(level)
       logging.getLogger('openstef_beam').setLevel(logging.WARNING)
   
   # Use in your application
   setup_openstef_logging(
       level=logging.INFO,
       log_file='forecasting.log'
   )

For production deployment patterns and monitoring integration, see :doc:`deployment`. For data pipeline logging considerations, see :doc:`data_integration`.