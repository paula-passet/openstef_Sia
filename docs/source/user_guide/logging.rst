Logging
=======

OpenSTEF, like any well-behaved Python library, does not configure logging for you. It
attaches a ``NullHandler`` to its loggers and leaves all configuration decisions to your
application. This page explains how to surface those log messages, how to tune
verbosity, and how to integrate OpenSTEF's logging output with production systems.

.. note::

   For deployment-specific concerns such as log aggregation in containerised
   environments, see :doc:`deployment`. For troubleshooting data pipeline issues that
   go beyond logging, see :doc:`data_integration`.

.. contents:: On this page
   :local:
   :depth: 2


Why OpenSTEF Uses NullHandler
------------------------------

Following the guidance in :pep:`328` and the Python logging HOWTO, OpenSTEF ships with
a ``NullHandler`` on every package-level logger. This means that importing
``openstef`` into your application will never produce unexpected console output or
interfere with your application's own logging configuration. You opt in to log output
explicitly, which is the correct behaviour for a library.


Basic Configuration
-------------------

The simplest way to see OpenSTEF log messages is to configure the root logger before
you start using the library:

.. code-block:: python

   import logging
   import openstef

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # OpenSTEF operations now emit log output
   from openstef.pipeline.train_model import train_model_pipeline
   # ... your pipeline calls here

Because ``basicConfig`` configures the root logger, all child loggers — including
OpenSTEF's — inherit the level and handler automatically.

.. note::

   Call ``logging.basicConfig`` (or any other logging setup) **before** importing
   OpenSTEF pipeline functions. Python's logging module is initialised at import time,
   and handlers attached after the fact may miss early messages.


Log Levels
----------

OpenSTEF uses the five standard Python log levels. The table below describes what each
level means in the context of the library:

- **DEBUG** — Fine-grained trace information: feature engineering steps, individual
  model hyperparameter values, intermediate DataFrame shapes. Useful when diagnosing
  unexpected model behaviour.
- **INFO** — Normal operational milestones: pipeline stages starting and completing,
  model training summary statistics, forecast generation counts.
- **WARNING** — Something unexpected occurred but the pipeline continued: missing
  optional input columns, fallback behaviour triggered, deprecated API usage.
- **ERROR** — A recoverable problem that caused a pipeline step to fail: a single
  prediction job failed while others succeeded.
- **CRITICAL** — An unrecoverable failure that halts execution.

For day-to-day use, ``INFO`` is the recommended level. Use ``DEBUG`` when actively
investigating a problem, and ``WARNING`` in production where log volume matters.

.. code-block:: python

   import logging

   # Development — see everything
   logging.basicConfig(level=logging.DEBUG)

   # Production — important messages only
   logging.basicConfig(level=logging.WARNING)

   # Data science workflows — informational progress
   logging.basicConfig(level=logging.INFO)


Logger Hierarchy
----------------

OpenSTEF loggers follow Python's hierarchical naming convention. The top-level logger
names correspond to the installed packages:

- ``openstef`` — the core forecasting library
- ``openstef_dbc`` — the database connector package (if installed)

You can control verbosity at any level of the hierarchy:

.. code-block:: python

   import logging

   # Silence the entire openstef package except warnings
   logging.getLogger("openstef").setLevel(logging.WARNING)

   # But keep INFO-level output for the training pipeline specifically
   logging.getLogger("openstef.pipeline.train_model").setLevel(logging.INFO)

   # Suppress noisy feature engineering detail
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

This granularity is useful when you want pipeline-level progress messages without the
volume of per-step debug traces.


Custom Handlers
---------------

``logging.basicConfig`` is convenient but limited. For production use you will
typically want to route log records to multiple destinations — for example, a file for
persistent storage and ``stderr`` for container log capture.

**File and console handler**

.. code-block:: python

   import logging
   import sys

   logger = logging.getLogger()  # root logger
   logger.setLevel(logging.DEBUG)  # capture everything; handlers filter below

   fmt = logging.Formatter(
       "%(asctime)s %(name)s %(levelname)s %(message)s",
       datefmt="%Y-%m-%dT%H:%M:%S",
   )

   # Console handler — INFO and above
   console = logging.StreamHandler(sys.stdout)
   console.setLevel(logging.INFO)
   console.setFormatter(fmt)

   # Rotating file handler — DEBUG and above
   from logging.handlers import RotatingFileHandler
   file_handler = RotatingFileHandler(
       "openstef.log", maxBytes=10 * 1024 * 1024, backupCount=5
   )
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(fmt)

   logger.addHandler(console)
   logger.addHandler(file_handler)

.. note::

   Set the root logger level to the *most permissive* level you need across all
   handlers (``DEBUG`` in the example above). Individual handler levels then act as
   filters. If you set the root logger to ``WARNING``, a ``DEBUG``-level file handler
   will never receive records regardless of its own level setting.

**JSON handler for log aggregation**

Structured JSON logs integrate cleanly with log aggregation platforms such as
Elasticsearch, Splunk, or Loki. The standard library does not include a JSON
formatter, but you can write a lightweight one:

.. code-block:: python

   import json
   import logging
   import traceback
   from datetime import datetime, timezone


   class JsonFormatter(logging.Formatter):
       """Emit each log record as a single JSON line."""

       def format(self, record: logging.LogRecord) -> str:
           payload = {
               "timestamp": datetime.fromtimestamp(
                   record.created, tz=timezone.utc
               ).isoformat(),
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
           }
           if record.exc_info:
               payload["exception"] = self.formatException(record.exc_info)
           return json.dumps(payload)


   handler = logging.StreamHandler()
   handler.setFormatter(JsonFormatter())
   logging.getLogger().addHandler(handler)
   logging.getLogger().setLevel(logging.INFO)


Integration with structlog
--------------------------

If your application already uses `structlog <https://www.structlog.org/>`_ for
structured, context-rich logging, you can route OpenSTEF's standard-library log
records through structlog's processor chain:

.. code-block:: python

   import logging
   import structlog

   # 1. Configure structlog processors
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

   # 2. Configure the standard library bridge
   logging.basicConfig(format="%(message)s", level=logging.INFO)

   # OpenSTEF log records now flow through the structlog processor chain
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

With this setup, every OpenSTEF log record is enriched by structlog's processors and
emitted as a JSON object, making it straightforward to correlate forecasting events
with other application telemetry.

For the full range of structlog configuration options, refer to the
`structlog standard library integration guide
<https://www.structlog.org/en/stable/standard-library.html>`_.


Integration with Production Logging Systems
-------------------------------------------

**Python logging dictConfig**

In production applications it is common to define the entire logging configuration
declaratively using ``logging.config.dictConfig``. This keeps logging setup separate
from application logic and makes it easy to change configuration without touching code:

.. code-block:: python

   import logging.config

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "standard": {
               "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
           },
           "json": {
               "()": "your_app.logging.JsonFormatter",  # custom formatter class
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "level": "INFO",
               "formatter": "standard",
               "stream": "ext://sys.stdout",
           },
           "file": {
               "class": "logging.handlers.RotatingFileHandler",
               "level": "DEBUG",
               "formatter": "json",
               "filename": "openstef.log",
               "maxBytes": 10485760,
               "backupCount": 5,
           },
       },
       "loggers": {
           "openstef": {
               "level": "INFO",
               "handlers": ["console", "file"],
               "propagate": False,
           },
       },
       "root": {
           "level": "WARNING",
           "handlers": ["console"],
       },
   }

   logging.config.dictConfig(LOGGING_CONFIG)

Setting ``"propagate": False`` on the ``openstef`` logger prevents records from
bubbling up to the root logger and being emitted twice.

**Cloud and platform handlers**

Most cloud platforms provide a Python logging handler that forwards records to their
native log service. The pattern is always the same — install the handler on the
``openstef`` logger (or the root logger) before running any pipelines:

.. code-block:: python

   import logging

   # Example: Google Cloud Logging
   # import google.cloud.logging
   # client = google.cloud.logging.Client()
   # client.setup_logging()  # attaches handler to root logger

   # Example: Azure Monitor / OpenTelemetry
   # from azure.monitor.opentelemetry import configure_azure_monitor
   # configure_azure_monitor()

   # After setup, OpenSTEF logs are forwarded automatically
   logging.getLogger("openstef").setLevel(logging.INFO)


Debugging Tips
--------------

**No log output appearing**

OpenSTEF uses ``NullHandler`` by default, so if you see nothing, logging has not been
configured. The fastest fix:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

If output still does not appear, inspect the logger state directly:

.. code-block:: python

   import logging

   lg = logging.getLogger("openstef")
   print("Level:", lg.level)
   print("Effective level:", lg.getEffectiveLevel())
   print("Handlers:", lg.handlers)
   print("Parent handlers:", lg.parent.handlers)

Check that neither the logger's own level nor a parent logger's level is set more
restrictively than you expect.

**Duplicate log messages**

Duplicate messages are almost always caused by ``propagate=True`` (the default) on a
logger that has its own handler *and* whose parent also has a handler. Fix by setting
``propagate=False`` on the child logger:

.. code-block:: python

   logging.getLogger("openstef").propagate = False

**Reducing verbosity in production**

If OpenSTEF is producing more output than you need:

.. code-block:: python

   import logging

   # Raise the threshold for the whole package
   logging.getLogger("openstef").setLevel(logging.WARNING)

   # Or target a specific noisy sub-module
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

**Performance considerations**

Logging in tight loops can add measurable overhead. OpenSTEF follows Python best
practices — messages are not formatted unless a handler will actually emit them — but
you can further reduce overhead by:

- Setting the logger level to ``WARNING`` or higher in performance-critical paths.
- Using a ``logging.Filter`` to skip categories of messages selectively.

.. code-block:: python

   import logging

   class SuppressDebugFilter(logging.Filter):
       """Drop DEBUG records from the feature engineering module."""

       def filter(self, record: logging.LogRecord) -> bool:
           if "feature_engineering" in record.name:
               return record.levelno >= logging.INFO
           return True

   logging.getLogger("openstef").addFilter(SuppressDebugFilter())


Summary
-------

- OpenSTEF is a library and deliberately does not configure logging — you own that
  responsibility in your application.
- Use ``logging.basicConfig`` for quick setup; use ``dictConfig`` for production.
- Control verbosity at any level of the ``openstef.*`` logger hierarchy.
- JSON formatters and structlog integration make it straightforward to feed OpenSTEF
  output into log aggregation platforms.
- When debugging, inspect ``getEffectiveLevel()`` and ``handlers`` on the logger
  object to understand exactly what is and is not being captured.

For production deployment patterns that go beyond logging configuration, see
:doc:`deployment`. For guidance on connecting OpenSTEF to external data sources where
data-pipeline errors often surface first in logs, see :doc:`data_integration`.