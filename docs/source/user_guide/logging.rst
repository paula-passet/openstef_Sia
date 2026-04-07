Logging and Diagnostics
=======================

OpenSTEF uses Python's standard ``logging`` module throughout its codebase. As a library, OpenSTEF follows the best practice of attaching a ``NullHandler`` to its loggers by default, which means **no log output appears unless you explicitly configure logging** in your application. This page covers how to configure logging for different environments, control verbosity, integrate with production logging systems, and use log output to debug forecasting issues.

Basic Configuration
-------------------

The simplest way to see OpenSTEF log output is to configure Python's root logger before using any OpenSTEF components:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # Now OpenSTEF operations will produce log output
   from openstef.pipeline.train_model import train_model_pipeline

With this in place, OpenSTEF will emit informational messages about data loading, feature engineering, model training, and forecast generation.

Choosing Log Levels
^^^^^^^^^^^^^^^^^^^

Different log levels suit different situations:

.. code-block:: python

   import logging

   # Development: See everything, including internal decision-making
   logging.basicConfig(level=logging.DEBUG)

   # Data science workflows: Progress and summary information
   logging.basicConfig(level=logging.INFO)

   # Production: Only warnings and errors
   logging.basicConfig(level=logging.WARNING)

OpenSTEF emits messages at these levels:

- **DEBUG** — Detailed internal state: feature matrices, intermediate calculations, model hyperparameters considered during training.
- **INFO** — Progress milestones: training started, data loaded, forecast generated, model saved.
- **WARNING** — Recoverable issues: missing input columns, fallback behavior triggered, data quality concerns.
- **ERROR** — Failures that prevent a pipeline from completing.

Logger Hierarchy
----------------

OpenSTEF loggers follow Python's hierarchical naming convention, which lets you control verbosity at different levels of granularity.

Package-Level Control
^^^^^^^^^^^^^^^^^^^^^

Control logging for entire OpenSTEF packages:

.. code-block:: python

   import logging

   # Show detailed output from the core openstef package
   logging.getLogger("openstef").setLevel(logging.DEBUG)

   # Suppress verbose output from openstef-models internals
   logging.getLogger("openstef_models").setLevel(logging.WARNING)

Module-Level Control
^^^^^^^^^^^^^^^^^^^^

When debugging a specific issue, narrow the scope to individual modules:

.. code-block:: python

   import logging

   # Debug feature engineering specifically
   logging.getLogger("openstef.feature_engineering").setLevel(logging.DEBUG)

   # Only show errors from validation
   logging.getLogger("openstef.validation").setLevel(logging.ERROR)

This hierarchical control is especially useful in production, where you want minimal noise from most components but detailed output from a module you're investigating.

Contextual Information
----------------------

OpenSTEF includes contextual information in many log messages to aid debugging and monitoring. When using an appropriate formatter, you'll see extra fields like model type, training sample count, feature lists, and forecast horizons:

.. code-block:: text

   2025-01-20 14:30:25 - openstef.pipeline.train_model - INFO - Model training started
     extra_info: {
       'model_type': 'xgb',
       'training_samples': 8760,
       'features': ['temperature', 'humidity', 'hour_of_day'],
       'horizon': 24
     }

This contextual information is particularly valuable when:

- Debugging why a model's accuracy degraded
- Monitoring training pipelines across many prediction jobs
- Analyzing which features were selected for a given forecast
- Tracking data quality across processing workflows

Integration with Production Logging Systems
--------------------------------------------

Structured Logging with structlog
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your production system uses `structlog <https://www.structlog.org/>`_ for structured, JSON-formatted log output, you can integrate OpenSTEF's standard logging into the structlog pipeline:

.. code-block:: python

   import logging
   import structlog

   structlog.configure(
       processors=[
           structlog.stdlib.filter_by_level,
           structlog.stdlib.add_logger_name,
           structlog.stdlib.add_log_level,
           structlog.stdlib.PositionalArgumentsFormatter(),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.UnicodeDecoder(),
           structlog.processors.JSONRenderer(),
       ],
       context_class=dict,
       logger_factory=structlog.stdlib.LoggerFactory(),
       wrapper_class=structlog.stdlib.BoundLogger,
       cache_logger_on_first_use=True,
   )

   # Configure standard logging so OpenSTEF messages flow through structlog
   logging.basicConfig(
       format="%(message)s",
       level=logging.INFO,
   )

   # All OpenSTEF log messages will now be JSON-formatted
   from openstef.pipeline.create_forecast import create_forecast_pipeline

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

File and Rotating Log Handlers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For long-running production services, write logs to rotating files to prevent unbounded disk usage:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Create a rotating file handler (10 MB per file, keep 5 backups)
   handler = RotatingFileHandler(
       "openstef_forecast.log",
       maxBytes=10 * 1024 * 1024,
       backupCount=5,
   )
   handler.setFormatter(
       logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
   )

   # Attach to the openstef logger
   logger = logging.getLogger("openstef")
   logger.addHandler(handler)
   logger.setLevel(logging.INFO)

Centralized Logging (ELK, CloudWatch, etc.)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Most centralized logging platforms consume JSON. Combine a JSON formatter with your platform's log shipper:

.. code-block:: python

   import logging
   import json

   class JSONFormatter(logging.Formatter):
       def format(self, record):
           log_entry = {
               "timestamp": self.formatTime(record),
               "logger": record.name,
               "level": record.levelname,
               "message": record.getMessage(),
           }
           if record.exc_info:
               log_entry["exception"] = self.formatException(record.exc_info)
           return json.dumps(log_entry)

   handler = logging.StreamHandler()
   handler.setFormatter(JSONFormatter())

   logging.getLogger("openstef").addHandler(handler)
   logging.getLogger("openstef").setLevel(logging.INFO)

Your log shipper (Filebeat, Fluentd, CloudWatch agent) can then parse and forward these structured entries.

Jupyter Notebook Configuration
------------------------------

Interactive environments benefit from a compact format and the ``force=True`` parameter to override any pre-existing configuration:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(name)-30s | %(levelname)-8s | %(message)s",
       force=True,
   )

   # OpenSTEF operations now show inline progress
   from openstef.pipeline.train_model import train_model_pipeline

.. note::

   The ``force=True`` parameter (Python 3.8+) removes any existing handlers before applying the new configuration. This is essential in notebooks where cells may be re-executed.

Debugging Tips
--------------

No Log Output Appearing
^^^^^^^^^^^^^^^^^^^^^^^^

If OpenSTEF operations complete silently, the most common cause is that no logging handler is configured. OpenSTEF uses ``NullHandler`` by default — this is intentional library behavior.

Diagnose the issue by inspecting the logger state:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef")
   print(f"Logger level: {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers: {logger.handlers}")
   print(f"Parent handlers: {logger.parent.handlers if logger.parent else 'None'}")

If ``Handlers`` is empty (or contains only ``NullHandler``), add a handler using ``logging.basicConfig()`` or by attaching one directly.

Too Much Log Output
^^^^^^^^^^^^^^^^^^^

If OpenSTEF is flooding your logs, selectively raise the level for noisy packages:

.. code-block:: python

   import logging

   logging.getLogger("openstef").setLevel(logging.WARNING)

   # Or target specific noisy modules
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF follows logging best practices — messages are not formatted unless actually emitted, and debug logging uses lazy evaluation. However, in tight loops or high-throughput scenarios, you can further reduce overhead:

.. code-block:: python

   import logging

   # Raise levels to avoid unnecessary string formatting
   logging.getLogger("openstef").setLevel(logging.WARNING)

   # Use filters for fine-grained control without changing levels
   class CriticalPathFilter(logging.Filter):
       def filter(self, record):
           return record.levelno >= logging.WARNING

   logging.getLogger("openstef").addFilter(CriticalPathFilter())

Best Practices Summary
----------------------

1. **Configure logging early** — set up handlers before importing OpenSTEF modules to capture initialization messages.
2. **Use appropriate levels** — ``INFO`` for general monitoring, ``DEBUG`` only when actively troubleshooting.
3. **Leverage the hierarchy** — use package- and module-level control rather than global settings.
4. **Don't suppress warnings in production** — OpenSTEF warnings often indicate data quality issues that affect forecast accuracy.
5. **Use structured logging** — JSON-formatted output integrates cleanly with modern observability platforms.

.. note::

   For production deployment patterns including monitoring and alerting, see :doc:`deployment`. For data pipeline issues that often surface through log messages, see :doc:`data_integration`.