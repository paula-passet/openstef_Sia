Logging
=======

OpenSTEF is a library, and like any well-behaved Python library it ships with a ``NullHandler`` attached to its loggers by default. This means you — the application developer — retain full control over where log output goes and how it is formatted. This page explains how to configure that output, how to tune verbosity for different environments, and how to integrate OpenSTEF's logging into production systems.

.. note::

   For guidance on deploying OpenSTEF in production environments more broadly, see :doc:`deployment`. If you are tracing data pipeline issues rather than log output, :doc:`data_integration` covers debugging data source connections.

.. _logging-basics:

How OpenSTEF Uses Logging
--------------------------

OpenSTEF follows the standard Python logging conventions throughout. Every module creates its logger with ``logging.getLogger(__name__)``, which produces a hierarchy rooted at the top-level package name. Because no handlers are attached by default, running OpenSTEF without any logging configuration produces no output — this is intentional and prevents the library from interfering with your application's logging setup.

The logger hierarchy looks like this:

.. note:: [DIAGRAM: Tree showing root logger → ``openstef`` → ``openstef.pipeline`` → ``openstef.pipeline.train_model``, and separately ``openstef`` → ``openstef.model`` → ``openstef.model.regressors``]

This hierarchy is important: a level set on ``openstef`` propagates to all child loggers unless a child explicitly overrides it.

.. _logging-basic-config:

Basic Configuration
--------------------

The quickest way to see OpenSTEF log output is to configure the root logger before importing or calling any OpenSTEF code:

.. code-block:: python

   import logging

   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s",
       datefmt="%Y-%m-%d %H:%M:%S",
   )

   # OpenSTEF operations will now emit INFO-level messages
   from openstef.pipeline.train_model import train_model_pipeline

``logging.basicConfig`` is a one-shot call: it has no effect if any handler is already attached to the root logger. In scripts and notebooks this is usually fine. In larger applications, prefer explicit handler configuration (see below).

.. _logging-levels:

Choosing the Right Log Level
-----------------------------

OpenSTEF uses the five standard Python levels consistently across its codebase:

- **DEBUG** — fine-grained diagnostics: data shapes, intermediate feature values, model hyperparameters being evaluated. Expect high volume.
- **INFO** — normal operational milestones: pipeline stages starting and finishing, model training completed, forecast written.
- **WARNING** — something unexpected happened but the pipeline continued: missing features imputed, fallback model used.
- **ERROR** — a recoverable failure: a single prediction task failed while others succeeded.
- **CRITICAL** — unrecoverable failure that halts execution.

Recommended levels by context:

.. code-block:: python

   import logging

   # Interactive development — see everything
   logging.getLogger("openstef").setLevel(logging.DEBUG)

   # CI / automated testing — only failures
   logging.getLogger("openstef").setLevel(logging.WARNING)

   # Production service — operational milestones without noise
   logging.getLogger("openstef").setLevel(logging.INFO)

You can also silence a particularly noisy sub-module while keeping the rest verbose:

.. code-block:: python

   # Keep pipeline-level INFO but suppress transform-level DEBUG chatter
   logging.getLogger("openstef").setLevel(logging.DEBUG)
   logging.getLogger("openstef.feature_engineering").setLevel(logging.WARNING)

.. _logging-handlers:

Custom Handlers
----------------

For anything beyond a quick script you will want to attach handlers explicitly rather than relying on ``basicConfig``. The example below writes INFO messages to ``stdout`` and ERROR messages to a rotating file — a common pattern for containerised services:

.. code-block:: python

   import logging
   import sys
   from logging.handlers import RotatingFileHandler

   def configure_logging(log_file: str = "openstef.log") -> None:
       """Attach handlers to the openstef logger."""
       openstef_logger = logging.getLogger("openstef")
       openstef_logger.setLevel(logging.DEBUG)  # let handlers decide what to keep

       # Console handler — INFO and above
       console = logging.StreamHandler(sys.stdout)
       console.setLevel(logging.INFO)
       console.setFormatter(logging.Formatter(
           "%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s"
       ))

       # Rotating file handler — ERROR and above, 5 MB per file, keep 3 backups
       file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
       file_handler.setLevel(logging.ERROR)
       file_handler.setFormatter(logging.Formatter(
           "%(asctime)s  %(name)s  %(levelname)s  %(message)s  [%(filename)s:%(lineno)d]"
       ))

       openstef_logger.addHandler(console)
       openstef_logger.addHandler(file_handler)

   configure_logging()

.. warning::

   Avoid calling ``logging.basicConfig`` after attaching handlers manually — it will have no effect and can cause confusion. Pick one approach and stick with it.

.. _logging-json:

JSON / Structured Logging for Production
-----------------------------------------

Production log aggregation systems (ELK stack, Datadog, Google Cloud Logging, Azure Monitor) work best with structured JSON log records. The ``structlog`` library integrates cleanly with Python's standard ``logging`` module, so OpenSTEF's output flows through it without any changes to the library itself:

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
           structlog.processors.TimeStamper(fmt="iso"),
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

   # 2. Configure standard logging to emit the raw message produced by structlog
   logging.basicConfig(format="%(message)s", level=logging.INFO)

   # 3. OpenSTEF log records are now emitted as JSON lines, e.g.:
   # {"event": "Training pipeline finished", "logger": "openstef.pipeline.train_model",
   #  "level": "info", "timestamp": "2024-03-15T10:22:01.123456Z"}

Each log line becomes a self-contained JSON object that log shippers can parse without brittle regex patterns.

For more advanced structlog configurations, see the `structlog standard library integration guide <https://www.structlog.org/en/stable/standard-library.html>`_.

.. _logging-dictconfig:

Using ``logging.config.dictConfig``
-------------------------------------

In applications that already manage logging through a configuration file or dictionary (common in Django, Flask, or Airflow deployments), add an ``openstef`` entry to your existing config:

.. code-block:: python

   import logging.config

   LOGGING = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "standard": {
               "format": "%(asctime)s  %(name)-40s  %(levelname)-8s  %(message)s"
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "formatter": "standard",
               "stream": "ext://sys.stdout",
           },
       },
       "loggers": {
           "openstef": {
               "handlers": ["console"],
               "level": "INFO",
               "propagate": False,  # prevent double-logging if root is also configured
           },
       },
   }

   logging.config.dictConfig(LOGGING)

Setting ``propagate: False`` on the ``openstef`` logger prevents records from bubbling up to the root logger and being printed twice when the root logger also has a console handler.

.. _logging-debugging:

Debugging Tips
---------------

**No output at all**

OpenSTEF attaches a ``NullHandler`` by default. If you see nothing, the most likely cause is that no handler has been added. Verify with:

.. code-block:: python

   import logging

   logger = logging.getLogger("openstef")
   print(f"Level      : {logger.level} (effective: {logger.getEffectiveLevel()})")
   print(f"Handlers   : {logger.handlers}")
   print(f"Propagate  : {logger.propagate}")
   print(f"Root handlers: {logging.getLogger().handlers}")

If both ``logger.handlers`` and the root handlers list are empty, add a handler as shown in the sections above.

**Too much output**

Raise the level on the sub-packages that are flooding your console:

.. code-block:: python

   import logging

   # Silence verbose feature-engineering debug messages
   logging.getLogger("openstef.feature_engineering").setLevel(logging.ERROR)

**Filtering by prediction job**

When running multiple prediction jobs concurrently it can be useful to tag every log record with a job identifier. Python's ``logging.Filter`` mechanism makes this straightforward:

.. code-block:: python

   import logging

   class JobFilter(logging.Filter):
       """Inject a prediction job ID into every log record."""

       def __init__(self, job_id: str) -> None:
           super().__init__()
           self.job_id = job_id

       def filter(self, record: logging.LogRecord) -> bool:
           record.job_id = self.job_id
           return True  # never suppress — only annotate

   # Attach to the openstef logger for the duration of a job
   job_filter = JobFilter(job_id="pj-42")
   logging.getLogger("openstef").addFilter(job_filter)

   # Update your formatter to include %(job_id)s
   handler = logging.StreamHandler()
   handler.setFormatter(logging.Formatter(
       "%(asctime)s  [%(job_id)s]  %(name)s  %(levelname)s  %(message)s"
   ))

**Performance impact**

Logging in tight loops can add measurable overhead. OpenSTEF's own code uses lazy evaluation so that string formatting only happens when a message will actually be emitted. When writing application code that calls OpenSTEF in a loop, follow the same pattern:

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)

   for job in prediction_jobs:
       # Prefer %-style formatting — evaluated lazily by the logging framework
       logger.debug("Starting job %s with %d features", job.id, len(job.features))

       result = run_pipeline(job)

       logger.info("Job %s completed in %.2f seconds", job.id, result.elapsed)

You can also attach a ``logging.Filter`` that short-circuits processing for levels you do not need during a performance-critical batch run, then remove it afterwards.

.. _logging-related:

Related Pages
--------------

- :doc:`deployment` — how to structure OpenSTEF in production services, including containerisation and scheduling patterns.
- :doc:`data_integration` — debugging data source connections, which often requires DEBUG-level logging to diagnose.
- :doc:`use_cases` — end-to-end examples that include minimal logging setup.