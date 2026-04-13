Logging
=======

OpenSTEF is a library, which means it deliberately stays out of your application's logging configuration. Every OpenSTEF package registers a ``NullHandler`` on its root logger by default, so importing OpenSTEF will never produce unexpected output or interfere with your existing logging setup. You are in full control: this page explains how to opt in to OpenSTEF's log output, tune verbosity, attach custom handlers, integrate with production logging systems, and diagnose common problems.

.. note::

   For guidance on deploying OpenSTEF in production environments, see :doc:`deployment`.
   For data pipeline patterns that generate their own log-worthy events, see :doc:`data_integration`.


Log Levels
----------

OpenSTEF uses the standard Python logging levels throughout its packages. Understanding what each level signals helps you choose the right verbosity for your environment.

- **DEBUG** – Fine-grained diagnostic detail: data shapes, intermediate computation results, feature names, model hyperparameters. Useful when tracking down unexpected forecast values.
- **INFO** – Operational milestones: pipeline stages starting and finishing, model training completed, forecast written. Safe for development and staging environments.
- **WARNING** – Something unexpected happened but execution continued: missing optional features, fallback behaviour triggered, data quality issues that were handled gracefully.
- **ERROR** – A specific operation failed: a model could not be trained, a prediction could not be produced. The surrounding pipeline may still continue.
- **CRITICAL** – A failure so severe that the process cannot meaningfully continue.

For most data-science workflows ``INFO`` is the right default. In production, ``WARNING`` keeps noise low while still surfacing actionable problems.


Basic Configuration
-------------------

The quickest way to see OpenSTEF log output is to configure the root logger before you import or call any OpenSTEF code:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

Because OpenSTEF loggers propagate to the root logger by default, this single call is enough to surface all ``INFO``-and-above messages from every OpenSTEF package.

If you only want output from specific packages, configure them individually instead:

.. code-block:: python

   import logging

   # Silence everything except OpenSTEF
   logging.getLogger().setLevel(logging.WARNING)

   # Then enable the packages you care about
   logging.getLogger("openstef").setLevel(logging.INFO)
   logging.getLogger("openstef_models").setLevel(logging.DEBUG)


Logger Hierarchy
----------------

OpenSTEF packages follow Python's dot-separated logger hierarchy. Each module creates its logger with ``logging.getLogger(__name__)``, so the names mirror the package structure:

.. code-block:: text

   openstef
   openstef.pipeline
   openstef.pipeline.train_model
   openstef_models
   openstef_models.forecasting.xgboost
   openstef_models.transforms
   openstef_beam

This hierarchy gives you precise control. Setting a level on a parent logger affects all children unless a child has its own explicit level set:

.. code-block:: python

   import logging

   # Quiet the entire models package …
   logging.getLogger("openstef_models").setLevel(logging.WARNING)

   # … but keep detailed output for the transform stage
   logging.getLogger("openstef_models.transforms").setLevel(logging.DEBUG)

To inspect the effective configuration of a logger at runtime:

.. code-block:: python

   import logging

   lg = logging.getLogger("openstef_models")
   print(f"Level set:       {lg.level}")
   print(f"Effective level: {lg.getEffectiveLevel()}")
   print(f"Own handlers:    {lg.handlers}")
   print(f"Parent handlers: {lg.parent.handlers}")


Custom Handlers
---------------

Because OpenSTEF is a library, it never installs handlers for you. You can attach any handler the standard library (or a third-party package) provides.

**Writing to a rotating file alongside the console:**

.. code-block:: python

   import logging
   from logging.handlers import RotatingFileHandler

   # Console handler
   console = logging.StreamHandler()
   console.setLevel(logging.INFO)
   console.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))

   # Rotating file handler – keeps last 5 × 10 MB
   file_handler = RotatingFileHandler(
       "openstef.log", maxBytes=10 * 1024 * 1024, backupCount=5
   )
   file_handler.setLevel(logging.DEBUG)
   file_handler.setFormatter(
       logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
   )

   # Attach to the OpenSTEF root loggers
   for name in ("openstef", "openstef_models", "openstef_beam"):
       lg = logging.getLogger(name)
       lg.setLevel(logging.DEBUG)
       lg.addHandler(console)
       lg.addHandler(file_handler)
       lg.propagate = False  # prevent double-logging to the root logger

Setting ``propagate = False`` stops messages from bubbling up to the root logger once you have attached your own handlers, which avoids duplicate lines in the console.

**Using a logging filter to suppress noisy modules:**

.. code-block:: python

   import logging

   class SuppressTransformDebug(logging.Filter):
       """Drop DEBUG records from the transforms sub-package."""

       def filter(self, record: logging.LogRecord) -> bool:
           if "transforms" in record.name and record.levelno == logging.DEBUG:
               return False
           return True

   logging.getLogger("openstef_models").addFilter(SuppressTransformDebug())


Integration with Production Logging Systems
-------------------------------------------

**JSON logging for log aggregators (ELK, Loki, CloudWatch)**

Structured JSON logs are easy to index and query in centralised logging platforms. The ``structlog`` library integrates cleanly with Python's standard logging, so OpenSTEF's output flows through it automatically:

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

   logging.basicConfig(
       format="%(message)s",
       level=logging.INFO,
   )

   # All OpenSTEF log output is now emitted as JSON lines,
   # ready for ingestion by Fluentd, Logstash, or a cloud collector.

Each log record will include ``logger``, ``level``, ``event``, and ``timestamp`` fields, making it straightforward to filter by package name or severity in your aggregator's query language.

**Forwarding to a remote syslog endpoint:**

.. code-block:: python

   import logging
   from logging.handlers import SysLogHandler

   syslog = SysLogHandler(address=("logs.example.internal", 514))
   syslog.setLevel(logging.WARNING)
   syslog.setFormatter(logging.Formatter("openstef: %(name)s %(levelname)s %(message)s"))

   logging.getLogger("openstef").addHandler(syslog)
   logging.getLogger("openstef_models").addHandler(syslog)

**Using Python's ``logging.config.dictConfig`` for reproducible setups:**

For production services it is good practice to define the entire logging configuration declaratively and load it at startup, rather than scattering ``getLogger`` calls through the codebase:

.. code-block:: python

   import logging.config

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "detailed": {
               "format": "%(asctime)s %(name)-40s %(levelname)-8s %(message)s",
               "datefmt": "%Y-%m-%dT%H:%M:%S",
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
               "formatter": "detailed",
               "stream": "ext://sys.stdout",
           },
           "json_file": {
               "class": "logging.handlers.RotatingFileHandler",
               "level": "DEBUG",
               "formatter": "json",
               "filename": "openstef.jsonl",
               "maxBytes": 10485760,
               "backupCount": 3,
           },
       },
       "loggers": {
           "openstef": {"level": "INFO", "handlers": ["console", "json_file"], "propagate": False},
           "openstef_models": {"level": "INFO", "handlers": ["console", "json_file"], "propagate": False},
           "openstef_beam": {"level": "WARNING", "handlers": ["console"], "propagate": False},
       },
   }

   logging.config.dictConfig(LOGGING_CONFIG)


Debugging Tips
--------------

**No log output appearing**

OpenSTEF registers ``NullHandler`` by default. If you see nothing, the most likely cause is that no handler has been attached to either the root logger or the OpenSTEF package loggers. The fastest fix:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

If output still does not appear, inspect the effective level and handler chain:

.. code-block:: python

   import logging

   for name in ("openstef", "openstef_models", "openstef_beam"):
       lg = logging.getLogger(name)
       print(name, "effective level:", lg.getEffectiveLevel(), "handlers:", lg.handlers)

**Too much output**

Pull back verbosity at the package level rather than raising the root logger level, which would silence your own application code too:

.. code-block:: python

   import logging

   logging.getLogger("openstef_models").setLevel(logging.WARNING)
   logging.getLogger("openstef_beam").setLevel(logging.WARNING)

   # Silence a particularly noisy sub-module entirely
   logging.getLogger("openstef_models.transforms").setLevel(logging.ERROR)

**Performance impact**

Logging in tight loops can measurable slow down a pipeline. OpenSTEF internally avoids string formatting until a message is confirmed to be emitted, but you can add an extra safeguard with a filter:

.. code-block:: python

   import logging

   class ProductionFilter(logging.Filter):
       """Only pass WARNING and above during performance-critical runs."""

       def filter(self, record: logging.LogRecord) -> bool:
           return record.levelno >= logging.WARNING

   logging.getLogger("openstef_models").addFilter(ProductionFilter())

**Tracing a specific forecast run**

When running multiple forecasts concurrently it is useful to tag log records with a run identifier. Python's ``logging.LoggerAdapter`` is the cleanest way to do this without modifying OpenSTEF's own code:

.. code-block:: python

   import logging
   import uuid

   base_logger = logging.getLogger("openstef.pipeline")

   run_id = str(uuid.uuid4())[:8]
   adapter = logging.LoggerAdapter(base_logger, extra={"run_id": run_id})

   adapter.info("Starting forecast run")  # emits: ... [run_id=abc12345] Starting forecast run

   # Use a formatter that includes the extra field:
   formatter = logging.Formatter("%(asctime)s [run_id=%(run_id)s] %(levelname)s %(message)s")

.. note::

   For guidance on structuring a full production deployment—including process management, environment variables, and health checks—see :doc:`deployment`.