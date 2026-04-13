Logging
=======

OpenSTEF is a Python library that integrates with Python's standard ``logging``
module. Because it is a library — not an application — OpenSTEF installs a
``NullHandler`` on its loggers by default, which means it produces no output
until your application configures logging. This page explains how to configure
logging for OpenSTEF, how to tune verbosity, how to integrate with production
logging stacks, and how to diagnose common problems.

.. note::

   For deployment patterns that affect how you might centralise log collection,
   see :doc:`deployment`. For data-pipeline specific concerns such as reading
   from remote sources, see :doc:`data_integration`.

.. contents:: On this page
   :local:
   :depth: 2


Understanding the Default Behaviour
------------------------------------

Python libraries are expected to follow the rule described in `PEP 3110
<https://peps.python.org/pep-0003110/>`_ and the `Python logging HOWTO
<https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>`_:
they should never configure logging themselves. OpenSTEF respects this
convention. If you run an OpenSTEF pipeline without any logging configuration
in your application, you will see no output at all — not even warnings.

The moment you add even a minimal ``logging.basicConfig()`` call, OpenSTEF's
messages start flowing through your handlers. This design keeps the library
from interfering with whatever logging setup your application already has.

.. note:: [DIAGRAM: Logger hierarchy showing root → openstef → openstef.pipeline / openstef.models / openstef.feature_engineering sub-loggers, each with NullHandler by default]


Log Levels
----------

OpenSTEF uses the five standard Python log levels with the following
conventions:

- **DEBUG** — step-by-step diagnostic detail: feature shapes, intermediate
  metric values, internal branching decisions. Use this when tracking down
  unexpected model behaviour.
- **INFO** — normal operational milestones: pipeline started, training
  completed, forecast written. Suitable for production dashboards.
- **WARNING** — something unexpected happened but execution continued: a
  missing feature column was imputed, a quantile fell back to a default.
- **ERROR** — a recoverable failure: a single prediction task failed but the
  rest of the batch continued.
- **CRITICAL** — an unrecoverable failure that halts execution.

For day-to-day data science work ``INFO`` is the right level. For production
services ``WARNING`` is usually sufficient unless you are actively
investigating an incident.


Basic Configuration
-------------------

The simplest way to see OpenSTEF output is a single ``basicConfig`` call
before any OpenSTEF imports or pipeline calls:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # OpenSTEF imports and usage follow
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

This configures the *root* logger, which every OpenSTEF sub-logger inherits.
You can then tighten or loosen specific namespaces without touching the root:

.. code-block:: python

   import logging

   # Root at INFO — most libraries stay quiet
   logging.basicConfig(level=logging.INFO)

   # See every decision OpenSTEF's feature engineering makes
   logging.getLogger("openstef.feature_engineering").setLevel(logging.DEBUG)

   # Silence a noisy third-party dependency
   logging.getLogger("lightgbm").setLevel(logging.WARNING)


Logger Hierarchy
----------------

OpenSTEF's loggers follow Python's dot-separated naming hierarchy. The top-level
namespace is ``openstef``. Knowing the sub-namespaces lets you target specific
components:

.. code-block:: python

   import logging

   # Inspect what is registered at runtime
   manager = logging.Logger.manager
   openstef_loggers = [
       name for name in manager.loggerDict
       if name.startswith("openstef")
   ]
   print(openstef_loggers)

Because child loggers propagate to their parent by default, setting a level on
``openstef`` controls the entire library:

.. code-block:: python

   logging.getLogger("openstef").setLevel(logging.DEBUG)


Custom Handlers
---------------

``basicConfig`` is convenient for scripts, but production code typically needs
more control — writing to files, rotating logs, or forwarding to a log
aggregator. Use ``logging.config.dictConfig`` for a fully declarative setup:

.. code-block:: python

   import logging
   import logging.config

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "detailed": {
               "format": (
                   "%(asctime)s %(name)s %(levelname)s "
                   "%(filename)s:%(lineno)d %(message)s"
               ),
               "datefmt": "%Y-%m-%dT%H:%M:%S",
           },
           "json": {
               # Replace with a JSON formatter such as python-json-logger
               # for log aggregators that expect structured input.
               "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "level": "INFO",
               "formatter": "detailed",
               "stream": "ext://sys.stdout",
           },
           "rotating_file": {
               "class": "logging.handlers.RotatingFileHandler",
               "level": "DEBUG",
               "formatter": "detailed",
               "filename": "/var/log/openstef/pipeline.log",
               "maxBytes": 10_485_760,  # 10 MB
               "backupCount": 5,
           },
       },
       "loggers": {
           "openstef": {
               "level": "DEBUG",
               "handlers": ["console", "rotating_file"],
               "propagate": False,
           },
       },
       "root": {
           "level": "WARNING",
           "handlers": ["console"],
       },
   }

   logging.config.dictConfig(LOGGING_CONFIG)

Setting ``"propagate": False`` on the ``openstef`` logger prevents its
messages from being handled a second time by the root logger.


Integration with Production Logging Systems
--------------------------------------------

Structured / JSON logging
^^^^^^^^^^^^^^^^^^^^^^^^^

Log aggregators such as Elasticsearch, Splunk, and Datadog work best with
structured JSON logs. The ``python-json-logger`` package bridges Python's
standard logging and JSON output:

.. code-block:: python

   import logging
   import logging.config
   from pythonjsonlogger import jsonlogger

   handler = logging.StreamHandler()
   handler.setFormatter(
       jsonlogger.JsonFormatter(
           fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
           datefmt="%Y-%m-%dT%H:%M:%SZ",
       )
   )

   logger = logging.getLogger("openstef")
   logger.setLevel(logging.INFO)
   logger.addHandler(handler)
   logger.propagate = False

Each log record is then emitted as a single JSON object, which aggregators can
index and query without fragile regex parsing.

Structlog integration
^^^^^^^^^^^^^^^^^^^^^

If your application already uses `structlog <https://www.structlog.org/>`_,
you can route OpenSTEF's standard-library log records through structlog's
processor chain by bridging the two systems:

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

   # Standard logging still needs a handler; structlog takes it from there.
   logging.basicConfig(format="%(message)s", level=logging.INFO)

OpenSTEF's log records will now pass through structlog's processor chain and
appear alongside your application's own structured events.

Callback-based monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^

For fine-grained observability inside a pipeline run — for example, logging
metrics after each training fold — OpenSTEF exposes a callback interface.
Implementing ``ForecastingCallback`` lets you hook into lifecycle events
without modifying library code:

.. code-block:: python

   import logging
   from openstef.models.callbacks import ForecastingCallback

   logger = logging.getLogger(__name__)

   class MetricsLoggingCallback(ForecastingCallback):
       """Emit structured log lines at key pipeline milestones."""

       def on_fit_start(self, pipeline, dataset):
           logger.info(
               "Training started",
               extra={
                   "n_samples": len(dataset.data),
                   "pipeline": type(pipeline).__name__,
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

Pass the callback when constructing your workflow to activate it. This
approach keeps monitoring logic separate from pipeline logic and is
particularly useful in production deployments described in :doc:`deployment`.


Debugging Tips
--------------

No log output appearing
^^^^^^^^^^^^^^^^^^^^^^^

If you see nothing at all, the most common cause is that logging has not been
configured. OpenSTEF's ``NullHandler`` silently discards all records until a
real handler is attached. Add ``logging.basicConfig(level=logging.DEBUG)``
at the very top of your script — before any other imports — and re-run.

Also verify that the effective level on the logger you care about is not
inadvertently raised:

.. code-block:: python

   import logging

   lg = logging.getLogger("openstef")
   print("level set on logger :", lg.level)
   print("effective level     :", lg.getEffectiveLevel())
   print("handlers            :", lg.handlers)
   print("propagate           :", lg.propagate)

If ``getEffectiveLevel()`` returns a higher value than expected, a parent
logger is overriding the child. Set the level explicitly on the ``openstef``
logger rather than relying on inheritance.

Too much output
^^^^^^^^^^^^^^^

In tight training loops or large batch jobs, DEBUG logging can slow execution
and flood log files. Raise the level on the noisiest namespaces:

.. code-block:: python

   import logging

   logging.getLogger("openstef").setLevel(logging.WARNING)

   # Or target a single noisy sub-module
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

You can also use a ``logging.Filter`` to drop records selectively without
changing levels globally:

.. code-block:: python

   import logging

   class SuppressDebugFilter(logging.Filter):
       """Drop DEBUG records during performance-critical sections."""

       def filter(self, record: logging.LogRecord) -> bool:
           return record.levelno >= logging.INFO

   logging.getLogger("openstef").addFilter(SuppressDebugFilter())

Exceptions not showing full tracebacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you see a one-line error message but no traceback, check that your
formatter includes ``%(exc_info)s`` or that you are calling
``logger.exception(...)`` rather than ``logger.error(...)``:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   try:
       # ... pipeline call ...
       pass
   except Exception:
       # exception() automatically attaches exc_info=True
       logger.exception("Pipeline failed — full traceback follows")

Performance considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Python's logging module is efficient: format strings are not evaluated unless
the record will actually be emitted. OpenSTEF follows this convention
internally. If you are writing custom callbacks or wrappers, use lazy
formatting too:

.. code-block:: python

   # Good — format string evaluated only if DEBUG is active
   logger.debug("Feature matrix shape: %s", feature_matrix.shape)

   # Avoid — f-string always evaluated, even when DEBUG is suppressed
   logger.debug(f"Feature matrix shape: {feature_matrix.shape}")


Summary
-------

- OpenSTEF uses ``NullHandler`` by default — your application must configure
  logging.
- Use ``logging.basicConfig`` for scripts; use ``logging.config.dictConfig``
  for production services.
- Target the ``openstef`` logger namespace to control the whole library, or
  address sub-namespaces for finer control.
- For structured log aggregation, pair Python's standard logging with
  ``python-json-logger`` or structlog.
- Use ``ForecastingCallback`` to emit custom log events at pipeline lifecycle
  milestones without modifying library internals.