Logging
=======

OpenSTEF follows the standard Python library convention of adding a ``NullHandler`` to
its package loggers. This means that as a library, OpenSTEF produces no log output by
default — it is entirely up to your application to configure logging. This page explains
how to set up logging for OpenSTEF, how to tune verbosity, how to integrate with
production logging systems, and how to diagnose common problems.

.. note::

   For guidance on running OpenSTEF in production environments, see
   :doc:`deployment`. For data pipeline integration patterns, see
   :doc:`data_integration`.

.. _logging-basics:

How OpenSTEF Uses Logging
--------------------------

OpenSTEF emits log records through Python's standard :mod:`logging` module using
hierarchical logger names rooted at the package name (e.g. ``openstef_models``,
``openstef_beam``). Because the library registers only a ``NullHandler``, none of
these records reach any output destination until your application attaches a handler.

This is intentional and correct library behaviour. It prevents OpenSTEF from
interfering with the logging configuration of the application that embeds it.

.. _logging-levels:

Log Levels
----------

OpenSTEF uses the five standard Python log levels:

- **DEBUG** — fine-grained diagnostic detail: feature engineering steps, intermediate
  model states, per-row decisions. Use this when tracking down unexpected behaviour.
- **INFO** — normal operational milestones: training started, forecast produced,
  metrics computed. Suitable for development and interactive workflows.
- **WARNING** — something unexpected happened but execution continued: missing
  optional features, fallback behaviour triggered.
- **ERROR** — a recoverable problem that prevented a specific operation from
  completing.
- **CRITICAL** — a fatal condition that is likely to abort the run.

For interactive data-science work, ``INFO`` is usually the right level. For production
services, ``WARNING`` keeps noise low while still surfacing actionable events.

.. _logging-basic-config:

Basic Configuration
-------------------

The simplest way to see OpenSTEF log output is to call :func:`logging.basicConfig`
before importing or using any OpenSTEF components:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # OpenSTEF operations will now emit INFO-level records to stdout
   from openstef_models.workflows import CustomForecastingWorkflow

Because OpenSTEF loggers inherit from the root logger by default, this single call is
sufficient for most development scenarios.

To see verbose diagnostic output during model training or feature engineering, switch
to ``DEBUG``:

.. code-block:: python

   logging.basicConfig(level=logging.DEBUG)

And to suppress everything except warnings in a production service:

.. code-block:: python

   logging.basicConfig(level=logging.WARNING)

.. _logging-per-package:

Tuning Verbosity Per Package
-----------------------------

OpenSTEF is split across several packages (``openstef_models``, ``openstef_beam``,
``openstef_core``). You can set independent levels on each logger to get exactly the
detail you need without drowning in noise from other parts of the stack:

.. code-block:: python

   import logging

   # Root application level
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
   )

   # Verbose model diagnostics, quiet beam orchestration
   logging.getLogger("openstef_models").setLevel(logging.DEBUG)
   logging.getLogger("openstef_beam").setLevel(logging.WARNING)

   # Silence a particularly chatty sub-module
   logging.getLogger("openstef_models.transforms").setLevel(logging.ERROR)

This is especially useful in Jupyter notebooks where you want to see high-level
progress without scrolling through hundreds of transform-level debug lines.

.. _logging-custom-handlers:

Custom Handlers
---------------

For anything beyond simple console output you can attach handlers directly to the
OpenSTEF package loggers. The example below writes all ``openstef_models`` records at
``WARNING`` or above to a rotating file, while still sending ``INFO`` records to the
console:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Console handler — INFO and above
   console = logging.StreamHandler()
   console.setLevel(logging.INFO)
   console.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))

   # Rotating file handler — WARNING and above, 5 MB per file, 3 backups
   file_handler = RotatingFileHandler(
       "openstef.log", maxBytes=5 * 1024 * 1024, backupCount=3
   )
   file_handler.setLevel(logging.WARNING)
   file_handler.setFormatter(
       logging.Formatter("%(asctime)s  %(name)s  %(levelname)s  %(message)s")
   )

   pkg_logger = logging.getLogger("openstef_models")
   pkg_logger.setLevel(logging.DEBUG)   # let the handlers decide what to keep
   pkg_logger.addHandler(console)
   pkg_logger.addHandler(file_handler)
   pkg_logger.propagate = False          # don't double-log via the root logger

Setting ``propagate = False`` prevents records from travelling up to the root logger
and being printed a second time if the root logger also has a ``StreamHandler``
attached.

.. _logging-dictconfig:

File-Based Configuration with dictConfig
-----------------------------------------

In production it is common to manage logging configuration in a separate file or
dictionary rather than in code. Python's :func:`logging.config.dictConfig` accepts a
plain dictionary, making it easy to load from YAML or JSON:

.. code-block:: python

   import logging.config

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "detailed": {
               "format": "%(asctime)s  %(name)s  %(levelname)s  %(message)s",
               "datefmt": "%Y-%m-%d %H:%M:%S",
           },
           "json": {
               # Replace with a JSON formatter from your preferred library
               "format": '{"time": "%(asctime)s", "logger": "%(name)s", '
                         '"level": "%(levelname)s", "message": "%(message)s"}',
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "level": "INFO",
               "formatter": "detailed",
               "stream": "ext://sys.stdout",
           },
           "file": {
               "class": "logging.handlers.RotatingFileHandler",
               "level": "WARNING",
               "formatter": "json",
               "filename": "openstef.log",
               "maxBytes": 10485760,
               "backupCount": 5,
           },
       },
       "loggers": {
           "openstef_models": {
               "level": "DEBUG",
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

.. _logging-structlog:

Integration with structlog
---------------------------

If your application uses `structlog <https://www.structlog.org/>`_ for structured
logging, you can route OpenSTEF's standard-library records through it by bridging the
two systems. structlog's stdlib integration processes records emitted by any
``logging.Logger`` — including OpenSTEF's — through the structlog processor chain:

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

   # Standard logging must still be configured — structlog sits on top of it
   logging.basicConfig(format="%(message)s", level=logging.INFO)

With this setup, every record emitted by OpenSTEF will be serialised as JSON by
structlog, making it straightforward to ingest into log aggregation systems such as
Elasticsearch, Loki, or Splunk.

For more detail on the bridge between structlog and the standard library, see the
`structlog standard-library integration guide
<https://www.structlog.org/en/stable/standard-library.html>`_.

.. _logging-callbacks:

Logging via Workflow Callbacks
-------------------------------

For structured, event-driven logging tied to specific stages of a forecast run,
OpenSTEF's ``ForecastingCallback`` interface is often a better fit than attaching
handlers to package loggers. Callbacks fire at well-defined lifecycle points — training
start, training end, prediction end — and receive the workflow and dataset objects
directly, giving you rich context without parsing log strings:

.. code-block:: python

   import logging
   from openstef_models.mixins.callbacks import ForecastingCallback

   logger = logging.getLogger(__name__)


   class AuditLoggingCallback(ForecastingCallback):
       """Emit structured audit records at key workflow stages."""

       def on_fit_start(self, pipeline, dataset):
           logger.info(
               "Training started",
               extra={
                   "n_samples": len(dataset.data),
                   "model": type(pipeline).__name__,
               },
           )

       def on_fit_end(self, pipeline, dataset, result):
           if result is not None:
               logger.info(
                   "Training complete",
                   extra={"metrics": result.metrics_full.to_dict()},
               )

       def on_predict_end(self, pipeline, dataset, forecasts):
           logger.info(
               "Forecast produced",
               extra={"n_rows": len(forecasts.data)},
           )

Callbacks are registered when constructing a workflow and are particularly useful in
production deployments where you want to push metrics to a monitoring system alongside
log records. See :doc:`deployment` for patterns that combine callbacks with alerting
and observability tooling.

.. _logging-production:

Production Logging Patterns
-----------------------------

In a production service, a few additional practices keep logging manageable:

**Use a single configuration point.** Call ``logging.config.dictConfig`` (or
``fileConfig``) once at application startup, before any OpenSTEF imports that might
trigger lazy logger creation.

**Avoid configuring logging inside library code.** If you are building a library on
top of OpenSTEF, follow the same convention OpenSTEF itself uses: register only a
``NullHandler`` and leave configuration to the end application.

**Set levels appropriate to the environment.** A common pattern is to read the desired
level from an environment variable:

.. code-block:: python

   import logging
   import os

   log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
   logging.basicConfig(
       level=getattr(logging, log_level, logging.INFO),
       format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
   )

**Suppress third-party noise.** OpenSTEF depends on libraries such as XGBoost and
scikit-learn that can be verbose at ``DEBUG`` level. Silence them explicitly if needed:

.. code-block:: python

   logging.getLogger("xgboost").setLevel(logging.WARNING)
   logging.getLogger("sklearn").setLevel(logging.WARNING)

.. _logging-debugging:

Debugging Tips
--------------

**No log output appearing**

OpenSTEF uses ``NullHandler`` by default, so if you see nothing, the most likely cause
is that no handler has been configured. Call ``logging.basicConfig(level=logging.DEBUG)``
at the very top of your script (before any imports) to confirm:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)  # must come first

   import openstef_models  # now records will be visible

**Inspecting the logger hierarchy**

If you are unsure why a particular logger is silent or unexpectedly verbose, inspect
its effective configuration at runtime:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef_models")
   print(f"Level:           {logger.level}")
   print(f"Effective level: {logger.getEffectiveLevel()}")
   print(f"Handlers:        {logger.handlers}")
   print(f"Propagate:       {logger.propagate}")
   print(f"Parent handlers: {logger.parent.handlers}")

**Too much output**

If DEBUG-level output from OpenSTEF is overwhelming, raise the level on the specific
sub-logger that is noisy rather than silencing the whole package:

.. code-block:: python

   # Only suppress the chatty transforms sub-module
   logging.getLogger("openstef_models.transforms").setLevel(logging.WARNING)

**Performance impact**

Logging in tight loops can add measurable overhead. OpenSTEF follows Python best
practices — log messages are not formatted unless a handler will actually emit them —
but you can add a :class:`logging.Filter` to skip records during
performance-critical sections:

.. code-block:: python

   import logging

   class ProductionFilter(logging.Filter):
       """Drop DEBUG records in performance-sensitive paths."""

       def filter(self, record):
           return record.levelno >= logging.INFO

   logging.getLogger("openstef_models").addFilter(ProductionFilter())

.. note::

   For questions about integrating OpenSTEF's data inputs with external systems such
   as InfluxDB or Databricks — which often have their own logging requirements — see
   :doc:`data_integration`.