Logging
=======

.. contents:: On this page
   :local:
   :depth: 2

OpenSTEF is a library and, following Python conventions, it does not configure
logging on your behalf. Instead, it emits log records through the standard
:mod:`logging` module and leaves all handler, formatter, and level decisions to
the application that calls it. This page explains how to wire up logging so you
can see what OpenSTEF is doing, how to tune verbosity for different
environments, how to integrate with structured-logging systems, and how to
diagnose the most common logging problems.

.. note::

   For deployment-specific concerns such as log aggregation in Kubernetes or
   cloud environments, see :doc:`deployment`. For data-pipeline debugging that
   goes beyond log messages, see :doc:`use_cases`.

---

Basic Setup
-----------

Because OpenSTEF registers only a ``NullHandler`` on its root loggers, you will
see no output at all unless your application configures at least one handler.
The simplest way to do that is with :func:`logging.basicConfig`:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

Place this call once, as early as possible in your entry-point script or
application bootstrap, **before** importing OpenSTEF components. Any log
records emitted during import-time initialisation will then be captured.

---

Log Levels
----------

OpenSTEF uses the five standard Python log levels with the following intent:

- **DEBUG** – step-by-step diagnostic detail: feature construction, model
  hyper-parameters, intermediate metric values. Useful when diagnosing
  unexpected forecast behaviour.
- **INFO** – normal operational milestones: training started, training
  finished, forecast produced, metrics logged. Suitable for day-to-day
  monitoring.
- **WARNING** – something unexpected happened but the pipeline continued: a
  fallback was used, a data quality check was marginal.
- **ERROR** – a recoverable failure occurred: a sub-task failed and was
  skipped.
- **CRITICAL** – a failure that prevents the pipeline from continuing.

Choose a level that matches your environment:

.. code-block:: python

   import logging

   # Development – see everything
   logging.basicConfig(level=logging.DEBUG)

   # Data-science notebooks – informational milestones only
   logging.basicConfig(level=logging.INFO)

   # Production services – warnings and above
   logging.basicConfig(level=logging.WARNING)

---

Logger Hierarchy
----------------

OpenSTEF packages follow Python's dot-separated logger hierarchy. The two
top-level namespaces you will encounter most often are:

- ``openstef`` – the core library (``openstef_core``, ``openstef_models``)
- ``openstef_beam`` – the Apache Beam integration layer

You can tune each namespace independently without affecting the other or the
rest of your application:

.. code-block:: python

   import logging

   # Verbose output from the modelling layer, quiet from the Beam runner
   logging.getLogger("openstef_models").setLevel(logging.DEBUG)
   logging.getLogger("openstef_beam").setLevel(logging.WARNING)

   # Silence a single noisy sub-module
   logging.getLogger("openstef_models.transforms").setLevel(logging.ERROR)

Inspecting the effective level of a logger is useful when something is
unexpectedly silent or unexpectedly verbose:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef_models")
   print("level        :", logger.level)
   print("effective    :", logger.getEffectiveLevel())
   print("handlers     :", logger.handlers)
   print("parent hdlrs :", logger.parent.handlers)

---

Custom Handlers
---------------

``logging.basicConfig`` is convenient for scripts, but production services
typically need more control. You can attach any combination of handlers
directly to the ``openstef`` namespace loggers.

**Rotating file handler**

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
       logging.Formatter("%(asctime)s  %(name)s  %(levelname)s  %(message)s")
   )

   logging.getLogger("openstef_models").addHandler(handler)
   logging.getLogger("openstef_beam").addHandler(handler)

**JSON handler for log aggregators**

Many production log aggregators (Elasticsearch, Loki, Splunk) prefer
newline-delimited JSON. A lightweight approach using only the standard library:

.. code-block:: python

   import json
   import logging
   import traceback

   class JsonFormatter(logging.Formatter):
       """Emit each log record as a single-line JSON object."""

       def format(self, record: logging.LogRecord) -> str:
           payload = {
               "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
               "logger": record.name,
               "level": record.levelname,
               "message": record.getMessage(),
           }
           if record.exc_info:
               payload["exc"] = traceback.format_exception(*record.exc_info)
           return json.dumps(payload)

   handler = logging.StreamHandler()
   handler.setFormatter(JsonFormatter())
   logging.getLogger("openstef_models").addHandler(handler)

---

Workflow Callbacks for Structured Logging
------------------------------------------

For fine-grained observability inside a training or forecasting run, OpenSTEF
exposes a callback interface (``ForecastingCallback``) that fires at key
lifecycle events. This is often a better fit than parsing log strings, because
you receive the actual Python objects rather than their text representations.

.. code-block:: python

   import logging
   from openstef_models.mixins.callbacks import ForecastingCallback

   logger = logging.getLogger(__name__)

   class ObservabilityCallback(ForecastingCallback):
       """Log structured information at key pipeline milestones."""

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
                   "Training finished",
                   extra={"metrics": result.metrics_full.to_dict()},
               )

       def on_predict_end(self, pipeline, dataset, forecasts):
           logger.info(
               "Forecast produced",
               extra={"n_rows": len(forecasts.data)},
           )

Attach the callback when constructing your workflow:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       ...,
       callbacks=[ObservabilityCallback()],
   )

The ``extra`` dictionary is passed through to the log record and is available
to any formatter or handler that knows how to consume it – including the
``JsonFormatter`` shown in the previous section.

---

Integration with structlog
--------------------------

If your application already uses `structlog <https://www.structlog.org/>`_,
you can route OpenSTEF's standard-library log records through structlog's
processor chain by bridging the two systems:

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

   # 2. Configure the standard-library root logger to feed into structlog
   logging.basicConfig(format="%(message)s", level=logging.INFO)

With this configuration every ``logging.getLogger(...)`` call – including those
inside OpenSTEF – will produce structured JSON output processed by structlog.
See the `structlog standard-library integration guide
<https://www.structlog.org/en/stable/standard-library.html>`_ for advanced
processor options.

---

Production Logging Patterns
----------------------------

**Separate OpenSTEF logs from application logs**

In a service that embeds OpenSTEF, you may want to route library logs to a
dedicated sink while keeping your application logs elsewhere:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Application logger writes to stdout
   app_handler = logging.StreamHandler()
   app_handler.setLevel(logging.INFO)
   logging.getLogger("myapp").addHandler(app_handler)

   # OpenSTEF loggers write to a dedicated file
   lib_handler = RotatingFileHandler("openstef.log", maxBytes=5_000_000, backupCount=3)
   lib_handler.setLevel(logging.WARNING)
   for ns in ("openstef_models", "openstef_beam"):
       lg = logging.getLogger(ns)
       lg.addHandler(lib_handler)
       lg.propagate = False  # prevent double-logging via root logger

Setting ``propagate = False`` is important: without it, records bubble up to
the root logger and may appear in both sinks.

**Using dictConfig for reproducible configuration**

For services where logging must be declared once and never changed at runtime,
:func:`logging.config.dictConfig` is the most maintainable approach:

.. code-block:: python

   import logging.config

   LOGGING = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "json": {
               "()": "myapp.logging.JsonFormatter",
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "formatter": "json",
               "level": "INFO",
           },
       },
       "loggers": {
           "openstef_models": {"level": "INFO", "handlers": ["console"], "propagate": False},
           "openstef_beam":   {"level": "WARNING", "handlers": ["console"], "propagate": False},
           "myapp":           {"level": "DEBUG", "handlers": ["console"], "propagate": False},
       },
   }

   logging.config.dictConfig(LOGGING)

---

Performance Considerations
--------------------------

Logging has negligible overhead at ``WARNING`` and above because Python skips
string formatting when the effective level filters the record out. At
``DEBUG``, however, the cost of formatting complex objects (DataFrames, model
parameters) can accumulate in tight loops.

Practical guidelines:

- Use ``logging.WARNING`` or ``logging.INFO`` in production; reserve
  ``logging.DEBUG`` for local diagnosis sessions.
- Prefer lazy ``%``-style formatting (``logger.debug("value: %s", obj)``)
  over f-strings (``logger.debug(f"value: {obj}")``). The ``%`` form defers
  ``str()`` conversion until the record is actually emitted.
- Apply a filter when you need to suppress a single noisy module without
  changing its level globally:

.. code-block:: python

   import logging

   class SuppressTransformDebug(logging.Filter):
       def filter(self, record: logging.LogRecord) -> bool:
           return not (
               record.name.startswith("openstef_models.transforms")
               and record.levelno == logging.DEBUG
           )

   logging.getLogger("openstef_models").addFilter(SuppressTransformDebug())

---

Debugging Tips
--------------

**No log output at all**

OpenSTEF ships with a ``NullHandler`` on every package logger. If you see
nothing, the most likely cause is that no handler has been attached anywhere in
the hierarchy. Run this diagnostic snippet:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef_models")
   print("effective level :", logger.getEffectiveLevel())
   print("handlers        :", logger.handlers)
   print("root handlers   :", logging.root.handlers)

If all handler lists are empty, add a handler as shown in `Basic Setup`_.

**Too much output**

Raise the level on the specific namespace that is flooding your console:

.. code-block:: python

   import logging

   logging.getLogger("openstef_models").setLevel(logging.WARNING)
   logging.getLogger("openstef_beam").setLevel(logging.WARNING)

**Records appearing twice**

Double-logging is almost always caused by ``propagate = True`` (the default)
when both the package logger and the root logger have handlers. Set
``propagate = False`` on the package logger as shown in the production pattern
above.

**Tracing a single forecast run**

Use a ``logging.Filter`` to tag every record with a run identifier, making it
easy to grep a single execution out of a shared log file:

.. code-block:: python

   import logging
   import uuid

   class RunIdFilter(logging.Filter):
       def __init__(self, run_id: str):
           super().__init__()
           self.run_id = run_id

       def filter(self, record: logging.LogRecord) -> bool:
           record.run_id = self.run_id
           return True

   run_id = str(uuid.uuid4())
   filt = RunIdFilter(run_id)
   logging.getLogger("openstef_models").addFilter(filt)

   # Update your formatter to include %(run_id)s
   handler = logging.StreamHandler()
   handler.setFormatter(
       logging.Formatter("%(asctime)s [%(run_id)s] %(name)s %(levelname)s %(message)s")
   )
   logging.getLogger("openstef_models").addHandler(handler)

---

.. note::

   For guidance on deploying OpenSTEF in containerised or cloud environments –
   including how to ship logs to external aggregators – see :doc:`deployment`.
   For examples of end-to-end forecasting pipelines where logging plays a role
   in observability, see :doc:`use_cases`.