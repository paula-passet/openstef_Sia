Logging
=======

OpenSTEF is a library, which means it follows the standard Python convention of
shipping with a ``NullHandler`` attached to its root logger. This is intentional:
the library emits log records, but it is entirely up to *your* application to
decide where those records go, what format they take, and which levels are
visible. This page explains how to wire up that configuration correctly, how to
tune verbosity for different environments, and how to connect OpenSTEF's logs to
production logging systems.

.. note::

   For guidance on running OpenSTEF in production environments, see
   :doc:`deployment`. If you are integrating external data sources and want to
   trace data-pipeline issues through logs, see :doc:`data_integration`.

.. _logging-basic-setup:

Basic Setup
-----------

Because OpenSTEF registers only a ``NullHandler`` by default, you will see no
output at all until you configure a handler in your own code. The simplest way
to get started is Python's built-in ``logging.basicConfig``:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

Call this **once**, before you import or call anything from OpenSTEF, and all
``INFO``-level (and above) messages from the library will appear on ``stderr``.

If you only want to see OpenSTEF messages without changing the root logger's
level — useful when embedding the library inside a larger application — target
the package logger directly:

.. code-block:: python

   import logging

   handler = logging.StreamHandler()
   handler.setFormatter(
       logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
   )

   openstef_logger = logging.getLogger("openstef")
   openstef_logger.setLevel(logging.INFO)
   openstef_logger.addHandler(handler)
   # Prevent records from propagating to the root logger
   openstef_logger.propagate = False

.. _logging-levels:

Log Levels
----------

OpenSTEF uses the five standard Python log levels with the following intent:

- **DEBUG** — fine-grained diagnostics: feature engineering steps, intermediate
  model scores, individual pipeline stages. Expect high volume.
- **INFO** — normal operational milestones: training started/completed,
  forecast generated, data retrieved.
- **WARNING** — something unexpected happened but the pipeline continued: a
  missing feature was imputed, a fallback model was used.
- **ERROR** — a pipeline stage failed and could not recover; the forecast may be
  incomplete or absent.
- **CRITICAL** — a condition so severe that the process cannot continue at all.

Choosing the right level for your environment:

.. code-block:: python

   import logging

   # Interactive development — see everything
   logging.getLogger("openstef").setLevel(logging.DEBUG)

   # Data-science notebooks — useful milestones without noise
   logging.getLogger("openstef").setLevel(logging.INFO)

   # Production services — only actionable events
   logging.getLogger("openstef").setLevel(logging.WARNING)

.. _logging-hierarchy:

Logger Hierarchy
----------------

OpenSTEF loggers follow Python's dot-separated hierarchy under the ``openstef``
namespace. This lets you tune individual sub-packages without touching the rest:

.. code-block:: python

   import logging

   # Quiet down the feature-engineering module specifically
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

   # But keep the training pipeline at INFO
   logging.getLogger("openstef.pipeline").setLevel(logging.INFO)

You can inspect the effective level of any logger at runtime to verify your
configuration:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef")
   print(f"Level set on logger : {logger.level}")
   print(f"Effective level     : {logger.getEffectiveLevel()}")
   print(f"Handlers            : {logger.handlers}")
   print(f"Propagates          : {logger.propagate}")

.. _logging-custom-handlers:

Custom Handlers
---------------

Any standard Python ``logging.Handler`` subclass works with OpenSTEF. Below are
two patterns that come up frequently.

**Rotating file handler** — keeps a bounded log archive on disk:

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   file_handler = RotatingFileHandler(
       "openstef.log",
       maxBytes=10 * 1024 * 1024,  # 10 MB per file
       backupCount=5,
   )
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(
       logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
   )

   logging.getLogger("openstef").addHandler(file_handler)

**JSON handler** — machine-readable lines suitable for log aggregators:

.. code-block:: python

   import json
   import logging

   class JsonHandler(logging.StreamHandler):
       """Emit each log record as a single JSON line."""

       def emit(self, record: logging.LogRecord) -> None:
           payload = {
               "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
           }
           if record.exc_info:
               payload["exception"] = self.formatException(record.exc_info)
           self.stream.write(json.dumps(payload) + "\n")
           self.flush()

   json_handler = JsonHandler()
   json_handler.setLevel(logging.INFO)
   logging.getLogger("openstef").addHandler(json_handler)

.. _logging-production:

Integration with Production Logging Systems
-------------------------------------------

Production deployments typically centralise logs in a platform such as
Elasticsearch/Kibana, Datadog, or Azure Monitor. The recommended approach is to
keep OpenSTEF's own logging configuration minimal and let your platform's agent
or SDK collect from a common sink (a file, ``stdout``, or a socket).

**structlog** is a popular structured-logging library that bridges cleanly to
Python's standard ``logging`` module. Configuring it once causes OpenSTEF's
records to pass through structlog's processor chain automatically:

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

   # Standard logging still needs a handler — structlog routes through it
   logging.basicConfig(format="%(message)s", level=logging.INFO)

With this setup every OpenSTEF log message is serialised as JSON and can be
ingested by any log shipper that reads ``stdout``.

**dictConfig** for twelve-factor apps** — if your service reads its logging
configuration from a file or environment variable, ``logging.config.dictConfig``
is a clean way to express the full setup declaratively:

.. code-block:: python

   import logging.config

   LOGGING = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "json": {
               "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
               "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
           },
       },
       "handlers": {
           "stdout": {
               "class": "logging.StreamHandler",
               "stream": "ext://sys.stdout",
               "formatter": "json",
           },
       },
       "loggers": {
           "openstef": {
               "handlers": ["stdout"],
               "level": "INFO",
               "propagate": False,
           },
       },
   }

   logging.config.dictConfig(LOGGING)

.. note::

   The ``python-json-logger`` package (``pip install python-json-logger``) is
   required for the ``JsonFormatter`` above. Alternatively, use the
   ``JsonHandler`` shown in the previous section, which has no extra
   dependencies.

.. _logging-filters:

Using Filters for Fine-Grained Control
---------------------------------------

Filters let you suppress or enrich records without changing log levels globally.
A common use case is muting verbose sub-modules only during performance-critical
batch runs:

.. code-block:: python

   import logging

   class SuppressTransforms(logging.Filter):
       """Drop DEBUG records from the transforms sub-package."""

       def filter(self, record: logging.LogRecord) -> bool:
           if record.name.startswith("openstef.feature_engineering"):
               return record.levelno >= logging.WARNING
           return True

   logging.getLogger("openstef").addFilter(SuppressTransforms())

You can also use a filter to inject contextual metadata — for example, a
prediction-job identifier — into every record emitted during a forecast run:

.. code-block:: python

   import logging

   class JobContextFilter(logging.Filter):
       def __init__(self, job_id: str) -> None:
           super().__init__()
           self.job_id = job_id

       def filter(self, record: logging.LogRecord) -> bool:
           record.job_id = self.job_id
           return True

   # Attach before running a forecast pipeline
   job_filter = JobContextFilter(job_id="forecast-20240601-001")
   logging.getLogger("openstef").addFilter(job_filter)

   # Include %(job_id)s in your formatter to see it in output
   formatter = logging.Formatter(
       "%(asctime)s [%(job_id)s] %(levelname)s %(name)s: %(message)s"
   )

.. _logging-debugging:

Debugging Tips
--------------

**No output at all?**
OpenSTEF ships with ``NullHandler``, so if you have not added a handler yourself
nothing will appear. Run the inspection snippet from :ref:`logging-hierarchy` to
confirm the effective level and handler list.

**Too much output?**
Switch the ``openstef`` logger to ``WARNING`` and re-enable ``DEBUG`` only for
the specific sub-package you are investigating:

.. code-block:: python

   import logging

   logging.getLogger("openstef").setLevel(logging.WARNING)
   # Re-enable detail only for the pipeline module
   logging.getLogger("openstef.pipeline.train_model").setLevel(logging.DEBUG)

**Duplicate log lines?**
This usually means a handler has been added more than once (common in notebooks
where cells are re-run) or ``propagate`` is ``True`` while a handler also exists
on the root logger. Fix it by clearing handlers before adding new ones:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef")
   logger.handlers.clear()
   logger.addHandler(your_handler)

**Tracing a failing forecast?**
Set the level to ``DEBUG`` before calling the pipeline, capture the output to a
file, then search for ``ERROR`` and ``WARNING`` lines first. The ``DEBUG`` lines
immediately preceding an error usually identify the root cause:

.. code-block:: python

   import logging

   logging.basicConfig(
       filename="debug_run.log",
       level=logging.DEBUG,
       format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
   )

   # Run your pipeline here — full trace will be written to debug_run.log

.. note::

   Performance note: at ``DEBUG`` level, OpenSTEF may emit a large number of
   records during feature engineering and model training. Use ``DEBUG`` only
   for targeted investigations, not in steady-state production.

.. _logging-performance:

Performance Considerations
--------------------------

Logging has negligible overhead at ``WARNING`` and above because Python skips
string formatting when a record's level is below the effective threshold.
At ``DEBUG`` level the overhead is real, particularly inside tight loops.
OpenSTEF follows Python best practices — lazy formatting, conditional debug
blocks — but you can further reduce impact with a filter (see
:ref:`logging-filters`) or by raising the level on noisy sub-packages:

.. code-block:: python

   import logging

   # Silence the highest-volume sub-packages in production
   logging.getLogger("openstef.feature_engineering").setLevel(logging.WARNING)
   logging.getLogger("openstef.model").setLevel(logging.WARNING)

   # Keep pipeline-level milestones visible
   logging.getLogger("openstef.pipeline").setLevel(logging.INFO)

----

For deployment-specific concerns such as log aggregation in Kubernetes or cloud
environments, see :doc:`deployment`. For tracing data-ingestion issues end to
end, see :doc:`data_integration`.