Logging
=======

OpenSTEF is a library, which means it makes no assumptions about how your application handles log output. By default, every OpenSTEF package (``openstef``, ``openstef-models``, ``openstef-beam``) attaches only a ``NullHandler`` to its root logger, following the standard Python library convention. This gives you — the application developer — complete control over where log messages go, how they are formatted, and which ones are shown.

This page explains how to activate and configure OpenSTEF logging, how to tune verbosity per module, how to integrate with production logging systems, and how to diagnose common problems.

.. note::

   For guidance on deploying OpenSTEF in production environments, see :doc:`deployment`.
   For data pipeline patterns that produce their own log-worthy events, see :doc:`data_integration`.

.. contents:: On this page
   :local:
   :depth: 2


Getting Started
---------------

Because OpenSTEF ships with a ``NullHandler``, you will see no output at all until you configure a handler yourself. The quickest way to get started in a script or notebook is ``logging.basicConfig``:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

After this call, any OpenSTEF operation that logs at ``INFO`` or above will write to ``stderr``. This is sufficient for interactive exploration and simple scripts.

.. note::

   ``logging.basicConfig`` is a one-shot call — it has no effect if the root logger already has handlers attached (for example, inside a larger application that configures logging at startup). In that case, configure handlers explicitly as shown in the sections below.


Log Levels
----------

OpenSTEF uses the five standard Python log levels. Understanding what each level carries helps you choose the right setting for your environment.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Level
     - What OpenSTEF emits at this level
   * - ``DEBUG``
     - Fine-grained diagnostics: data shapes, intermediate feature values, model hyperparameter search steps, individual pipeline stage entry/exit.
   * - ``INFO``
     - Operational milestones: training started/completed, forecast generated, model persisted, data loaded.
   * - ``WARNING``
     - Recoverable anomalies: missing features imputed, fallback model used, data quality issues detected.
   * - ``ERROR``
     - Failures that prevented a specific operation from completing, with enough context to diagnose the cause.
   * - ``CRITICAL``
     - Severe failures that may leave the system in an inconsistent state.

For day-to-day development, ``INFO`` is the most useful level. Switch to ``DEBUG`` when you need to trace exactly what a pipeline stage is doing. In production, ``WARNING`` or ``ERROR`` keeps log volume manageable.

.. code-block:: python

   import logging

   # Development — see everything
   logging.basicConfig(level=logging.DEBUG)

   # Production — important messages only
   logging.basicConfig(level=logging.WARNING)


Logger Hierarchy and Per-Module Control
----------------------------------------

OpenSTEF loggers follow Python's hierarchical naming convention. Every module creates its logger with ``logging.getLogger(__name__)``, so logger names mirror the package structure:

.. code-block:: text

   openstef
   openstef.pipeline
   openstef.pipeline.train_model
   openstef.model
   openstef_models
   openstef_models.transforms
   openstef_beam

This hierarchy lets you tune verbosity at any level of granularity without touching the rest of your application's logging:

.. code-block:: python

   import logging

   # Quiet everything in openstef_models except warnings
   logging.getLogger("openstef_models").setLevel(logging.WARNING)

   # But keep full detail for the transforms sub-package during debugging
   logging.getLogger("openstef_models.transforms").setLevel(logging.DEBUG)

   # Silence openstef_beam entirely
   logging.getLogger("openstef_beam").setLevel(logging.ERROR)

Child loggers inherit their effective level from the nearest ancestor that has an explicit level set, so you only need to configure the nodes you actually want to change.

To inspect the current state of a logger at runtime:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef_models")
   print(f"Configured level : {logging.getLevelName(logger.level)}")
   print(f"Effective level  : {logging.getLevelName(logger.getEffectiveLevel())}")
   print(f"Own handlers     : {logger.handlers}")
   print(f"Parent handlers  : {logger.parent.handlers}")


Custom Handlers
---------------

For anything beyond a quick script you will want to attach handlers explicitly rather than relying on ``basicConfig``. This gives you independent control over console output, file rotation, and remote sinks.

**Rotating file handler alongside console output**

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Console handler — INFO and above
   console = logging.StreamHandler()
   console.setLevel(logging.INFO)
   console.setFormatter(logging.Formatter(
       "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
   ))

   # Rotating file handler — DEBUG and above, max 10 MB, keep 5 files
   file_handler = RotatingFileHandler(
       "openstef.log", maxBytes=10 * 1024 * 1024, backupCount=5
   )
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(logging.Formatter(
       "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
   ))

   # Attach both handlers to the openstef root logger
   openstef_logger = logging.getLogger("openstef")
   openstef_logger.setLevel(logging.DEBUG)   # let the handlers decide what to show
   openstef_logger.addHandler(console)
   openstef_logger.addHandler(file_handler)

   # Repeat for other OpenSTEF packages if needed
   logging.getLogger("openstef_models").setLevel(logging.DEBUG)
   logging.getLogger("openstef_models").addHandler(console)
   logging.getLogger("openstef_models").addHandler(file_handler)

.. note::

   Setting the logger level to ``DEBUG`` while giving each handler its own level is the standard pattern. The logger acts as a gate — messages below its level are discarded before reaching any handler. Each handler then applies its own secondary filter.


Integration with Production Logging Systems
--------------------------------------------

**JSON / structured logging with structlog**

Many production stacks expect JSON-formatted log lines so they can be ingested by Elasticsearch, Splunk, Datadog, or similar platforms. The ``structlog`` library integrates cleanly with Python's standard logging, so OpenSTEF's log output flows through it automatically:

.. code-block:: python

   import logging
   import structlog

   # Configure structlog processors
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

   # Standard logging still needs a handler — structlog routes through it
   logging.basicConfig(format="%(message)s", level=logging.INFO)

With this setup every OpenSTEF log record is serialised as a JSON object, making it straightforward to filter and aggregate by ``logger``, ``level``, or any other field in your log management platform.

**dictConfig for application-wide configuration**

In a production service it is common to declare the entire logging configuration in one place using ``logging.config.dictConfig``. This keeps logging setup out of application logic and makes it easy to change via configuration files or environment variables:

.. code-block:: python

   import logging.config

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "standard": {
               "format": "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
           },
           "json": {
               "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
               "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
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
               "backupCount": 3,
           },
       },
       "loggers": {
           "openstef": {
               "level": "DEBUG",
               "handlers": ["console", "file"],
               "propagate": False,
           },
           "openstef_models": {
               "level": "INFO",
               "handlers": ["console", "file"],
               "propagate": False,
           },
           "openstef_beam": {
               "level": "WARNING",
               "handlers": ["console"],
               "propagate": False,
           },
       },
   }

   logging.config.dictConfig(LOGGING_CONFIG)

Setting ``"propagate": False`` on each OpenSTEF logger prevents messages from bubbling up to the root logger and being duplicated by any root-level handlers your application may have.

**Filtering for performance-critical sections**

If OpenSTEF is called inside a tight loop — for example, generating forecasts for hundreds of substations in sequence — the overhead of log-record creation can become measurable. A ``logging.Filter`` lets you suppress verbose output for specific code paths without changing global levels:

.. code-block:: python

   import logging

   class QuietDuringBatchFilter(logging.Filter):
       """Suppress DEBUG messages during high-frequency batch runs."""

       def __init__(self):
           super().__init__()
           self.in_batch = False

       def filter(self, record):
           if self.in_batch:
               return record.levelno >= logging.WARNING
           return True

   batch_filter = QuietDuringBatchFilter()
   logging.getLogger("openstef_models").addFilter(batch_filter)

   # Around the hot loop:
   batch_filter.in_batch = True
   for prediction_job in prediction_jobs:
       run_forecast(prediction_job)
   batch_filter.in_batch = False


Debugging Tips
--------------

**No log output appearing**

OpenSTEF ships with ``NullHandler`` by default — this is intentional library behaviour. If you see nothing:

1. Confirm you have called ``logging.basicConfig`` or attached a handler before importing OpenSTEF modules.
2. Check that the handler's level is not more restrictive than the logger's level.
3. Verify the effective level of the logger you expect to produce output:

   .. code-block:: python

      import logging
      logger = logging.getLogger("openstef_models")
      print(logger.getEffectiveLevel())   # should not be 0 (NOTSET) if root is unconfigured

**Too much output**

Reduce verbosity selectively rather than raising the root logger level, which would silence your own application's logs too:

.. code-block:: python

   import logging

   logging.getLogger("openstef_models").setLevel(logging.WARNING)
   logging.getLogger("openstef_beam").setLevel(logging.WARNING)

   # Silence one particularly noisy sub-module
   logging.getLogger("openstef_models.transforms").setLevel(logging.ERROR)

**Tracing a specific pipeline stage**

When a training or forecast pipeline produces unexpected results, enable ``DEBUG`` only for the relevant sub-package so the signal is not buried in noise:

.. code-block:: python

   import logging

   # Full detail for the training pipeline, quiet everywhere else
   logging.getLogger("openstef").setLevel(logging.WARNING)
   logging.getLogger("openstef.pipeline.train_model").setLevel(logging.DEBUG)

   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter("%(name)s  %(levelname)s  %(message)s"))
   logging.getLogger("openstef.pipeline.train_model").addHandler(handler)

**Duplicate log messages**

If every message appears twice, a logger is propagating to the root logger while also having its own handler attached. Fix this by either setting ``propagate = False`` or removing the duplicate handler:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef_models")
   logger.propagate = False   # stop messages reaching the root logger's handlers


Summary
-------

- OpenSTEF uses ``NullHandler`` by default — you must configure a handler to see any output.
- Use ``logging.basicConfig`` for scripts and notebooks; use ``dictConfig`` or explicit handler setup for production services.
- Target the ``openstef``, ``openstef_models``, and ``openstef_beam`` logger namespaces to control verbosity independently of the rest of your application.
- Integrate with ``structlog`` or ``python-json-logger`` to produce structured JSON output compatible with centralised log management platforms.
- Use ``propagate = False`` when attaching handlers directly to OpenSTEF loggers to avoid duplicate messages.

For production deployment patterns that build on this logging setup, see :doc:`deployment`. For data integration pipelines that generate their own log events, see :doc:`data_integration`.