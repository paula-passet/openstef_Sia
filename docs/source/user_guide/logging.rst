Logging
=======

OpenSTEF uses Python's standard ``logging`` module throughout its internals. As a library, it ships with a ``NullHandler`` attached to its root logger by default — meaning no log output appears in your application until you explicitly configure it. This page explains how to enable and configure that output, tune log levels for different environments, integrate OpenSTEF logging with production systems, and diagnose common problems.

.. note::

   For guidance on deploying OpenSTEF in production environments, see :doc:`deployment`.
   For data pipeline integration patterns, see :doc:`data_integration`.

.. _logging-basic-setup:

Basic Setup
-----------

Because OpenSTEF is a library, it deliberately avoids configuring logging for you. The ``NullHandler`` default is the correct behaviour for a library: it prevents spurious output when your application has not set up logging, and it gives you full control over formatting, destinations, and verbosity.

To start seeing OpenSTEF log messages, call ``logging.basicConfig()`` (or configure handlers explicitly) before importing and using OpenSTEF:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # OpenSTEF operations will now emit log output
   from openstef.pipeline.train_model import train_model_pipeline_core

That single call is sufficient for interactive work, notebooks, and simple scripts. For anything more structured — production services, scheduled jobs, or multi-process workers — read on.

.. _logging-levels:

Log Levels
----------

OpenSTEF uses the five standard Python log levels. Understanding what each level covers helps you choose the right verbosity for your context:

- **DEBUG** — Fine-grained diagnostics: feature column names, intermediate array shapes, model hyperparameters. Useful when investigating unexpected forecast behaviour.
- **INFO** — Normal operational milestones: pipeline stages starting and completing, model training summaries, forecast generation counts.
- **WARNING** — Recoverable anomalies: missing feature columns that fall back to defaults, data quality issues that were handled automatically.
- **ERROR** — Failures that prevented an operation from completing, such as a training pipeline that could not fit a model for a specific prediction job.
- **CRITICAL** — Severe failures that may compromise the entire process.

For typical data science work, ``INFO`` is the right level. For production services where log volume matters, ``WARNING`` keeps output focused on actionable events. For debugging a specific problem, drop to ``DEBUG`` only for the relevant logger rather than globally:

.. code-block:: python

   import logging

   # Keep most output quiet, but see everything from the training pipeline
   logging.getLogger("openstef").setLevel(logging.WARNING)
   logging.getLogger("openstef.pipeline.train_model").setLevel(logging.DEBUG)

.. _logging-hierarchy:

Logger Hierarchy
----------------

OpenSTEF's loggers follow Python's dot-separated naming convention, which means you can control verbosity at any level of granularity:

.. mermaid:: /diagrams/user_guide/logging_diagram_1.mmd

The hierarchy means that setting a level on a parent logger affects all children unless a child has its own level set explicitly. A few practically useful targets:

- ``openstef`` — the entire library
- ``openstef.pipeline`` — all pipeline tasks (training, forecasting, optimisation)
- ``openstef.model`` — model fitting and serialisation
- ``openstef.data_classes`` — prediction job and feature flag processing

.. code-block:: python

   import logging

   # Silence the whole library except errors
   logging.getLogger("openstef").setLevel(logging.ERROR)

   # Re-enable INFO for just the forecast pipeline
   logging.getLogger("openstef.pipeline.create_forecast").setLevel(logging.INFO)

.. _logging-custom-handlers:

Custom Handlers
---------------

``logging.basicConfig()`` writes to ``stderr``. In most production contexts you will want to direct log output elsewhere — a file, a log aggregator, or a structured JSON stream. Python's ``logging`` module supports this through handlers.

**File handler with rotation:**

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   handler = RotatingFileHandler(
       "openstef.log",
       maxBytes=10 * 1024 * 1024,  # 10 MB
       backupCount=5,
   )
   handler.setLevel(logging.INFO)
   handler.setFormatter(
       logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
   )

   logging.getLogger("openstef").addHandler(handler)

**JSON handler for log aggregators (e.g. Elasticsearch, Loki):**

Many production stacks expect newline-delimited JSON. A lightweight approach uses a custom ``Formatter``:

.. code-block:: python

   import json
   import logging
   import traceback


   class JsonFormatter(logging.Formatter):
       """Emit each log record as a single JSON object."""

       def format(self, record: logging.LogRecord) -> str:
           payload = {
               "timestamp": self.formatTime(record, self.datefmt),
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
           }
           if record.exc_info:
               payload["exception"] = traceback.format_exception(*record.exc_info)
           return json.dumps(payload)


   handler = logging.StreamHandler()
   handler.setFormatter(JsonFormatter())
   logging.getLogger("openstef").addHandler(handler)

.. _logging-structlog:

Integration with structlog
--------------------------

If your application already uses `structlog <https://www.structlog.org/>`_ for structured, context-rich logging, you can route OpenSTEF's standard-library log records through structlog's processor chain by enabling its standard-library integration:

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

   # Standard logging must still be configured — structlog bridges into it
   logging.basicConfig(format="%(message)s", level=logging.INFO)

With this setup, every ``logging.getLogger("openstef.*")`` call flows through structlog's processor chain and is emitted as structured JSON alongside your application's own structured logs.

.. _logging-production:

Production Logging Patterns
---------------------------

In production, a few additional practices keep logging useful without becoming a burden.

**Suppress noisy dependencies alongside OpenSTEF:**

OpenSTEF depends on libraries such as ``sklearn``, ``xgboost``, and ``lightgbm`` that can emit their own verbose output. Silence them independently so you don't have to raise OpenSTEF's level to compensate:

.. code-block:: python

   import logging

   for noisy_lib in ("lightgbm", "xgboost", "sklearn"):
       logging.getLogger(noisy_lib).setLevel(logging.WARNING)

**Attach a filter to skip debug messages in hot paths:**

If a particular pipeline runs at high frequency and DEBUG is enabled globally for other reasons, a filter avoids the overhead of formatting messages you don't need:

.. code-block:: python

   import logging


   class MinLevelFilter(logging.Filter):
       def __init__(self, min_level: int) -> None:
           super().__init__()
           self.min_level = min_level

       def filter(self, record: logging.LogRecord) -> bool:
           return record.levelno >= self.min_level


   forecast_logger = logging.getLogger("openstef.pipeline.create_forecast")
   forecast_logger.addFilter(MinLevelFilter(logging.INFO))

**Propagation and library isolation:**

If you want OpenSTEF logs to go to a dedicated handler and nowhere else, disable propagation to the root logger:

.. code-block:: python

   import logging

   openstef_logger = logging.getLogger("openstef")
   openstef_logger.propagate = False
   openstef_logger.addHandler(your_dedicated_handler)

.. warning::

   Disabling propagation means the root logger's handlers will no longer receive OpenSTEF messages. Only do this when you have a specific handler attached to ``openstef`` directly, otherwise you will silently lose all log output from the library.

.. _logging-debugging:

Debugging Tips
--------------

**No log output at all?**

OpenSTEF's ``NullHandler`` default means nothing appears unless you configure logging. Check three things:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef")
   print("Level:", logger.level)                    # 0 means NOTSET — inherits from parent
   print("Effective level:", logger.getEffectiveLevel())
   print("Handlers:", logger.handlers)
   print("Root handlers:", logging.getLogger().handlers)

If ``getEffectiveLevel()`` returns 30 (WARNING) or higher, and you expected INFO output, either the root logger or the ``openstef`` logger has been set too restrictively.

**Too much output?**

Drop the level on the noisiest sub-logger rather than silencing the whole library:

.. code-block:: python

   import logging

   # Example: feature engineering is verbose at DEBUG
   logging.getLogger("openstef.feature_engineering").setLevel(logging.WARNING)

**Checking handler configuration at runtime:**

.. code-block:: python

   import logging

   # Print the full logger tree for openstef and its children
   for name, logger in logging.Logger.manager.loggerDict.items():
       if name.startswith("openstef") and isinstance(logger, logging.Logger):
           print(f"{name}: level={logger.level}, handlers={logger.handlers}")

**Performance note:**

Logging has negligible cost when the effective level filters a message out, because Python evaluates the level check before formatting the message string. However, constructing expensive objects solely to pass to a log call is wasteful. Prefer lazy formatting:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   # Good — string is only formatted if DEBUG is active
   logger.debug("Feature matrix shape: %s", feature_matrix.shape)

   # Avoid — the f-string is always evaluated, even if DEBUG is filtered
   logger.debug(f"Feature matrix shape: {feature_matrix.shape}")

----

For related topics, see :doc:`deployment` for how logging fits into containerised and cloud-native deployments, and :doc:`data_integration` for logging patterns when reading from external data sources such as InfluxDB or Databricks.