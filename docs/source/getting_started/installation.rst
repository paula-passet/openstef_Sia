Installation
============

This page covers everything you need to get OpenSTEF installed and running on your
machine — from system requirements and package options through to verifying a working
installation and resolving the most common setup problems.

Once installation is complete, head over to :doc:`quickstart` to run your first
forecast in minutes, or follow the more detailed walkthrough in :doc:`first_forecast`.

.. contents:: On this page
   :local:
   :depth: 2

System Requirements
-------------------

Before installing, confirm your environment meets the following requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux are all supported
- **pip 23+** or `uv <https://docs.astral.sh/uv/>`_ (recommended)

.. note::
   OpenSTEF 4.0 requires Python 3.12+ for optimal performance and modern type safety
   features. If you need Python 3.10 or 3.11 support, consider using OpenSTEF 3.x.

Check your Python version before proceeding:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions, tools like
`pyenv <https://github.com/pyenv/pyenv>`_ or
`conda <https://conda.io/>`_ make this straightforward.

Choosing an Installation
------------------------

OpenSTEF 4.0 is built around a modular architecture. Rather than one monolithic
package, the library is split into focused sub-packages that you can install
independently or together. The three core packages are:

- **openstef-core** — shared types, dataset types, and base utilities used by all
  other packages
- **openstef-models** — forecasting models, feature engineering, and data processing
- **openstef-beam** — backtesting, evaluation, analysis, and metrics

The ``openstef`` meta-package ties these together and is the most convenient entry
point for most users.

Recommended: complete installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install everything at once using the ``[all]`` extra. This is the right choice if you
are new to OpenSTEF or want access to all functionality including backtesting:

.. code-block:: bash

   # pip
   pip install "openstef[all]"

   # uv (faster dependency resolution)
   uv add "openstef[all]"

Selective installation
^^^^^^^^^^^^^^^^^^^^^^

If you want a lighter footprint — for example in a production inference environment
where backtesting tools are unnecessary — install only what you need:

.. code-block:: bash

   # Core utilities and dataset types only
   pip install openstef-core

   # Forecasting models (includes openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools (includes openstef-core)
   pip install openstef-beam

   # Meta-package: models only (no BEAM)
   pip install openstef

You can also use the meta-package extras to mix and match:

.. code-block:: bash

   # Models + BEAM backtesting tools
   pip install "openstef[beam]"

.. note::
   When in doubt, use ``pip install "openstef[all]"``. You can always trim
   dependencies later once you know which parts of the library you actually use.

Using a Virtual Environment
---------------------------

It is strongly recommended to install OpenSTEF inside a dedicated virtual environment
to avoid conflicts with other packages. Here are the most common approaches:

**With venv (built-in):**

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   pip install "openstef[all]"

**With uv (recommended for speed):**

.. code-block:: bash

   uv venv
   source .venv/bin/activate        # Linux / macOS
   .venv\Scripts\activate           # Windows

   uv add "openstef[all]"

**With conda:**

.. code-block:: bash

   conda create -n openstef python=3.12
   conda activate openstef
   pip install "openstef[all]"

Development Installation
------------------------

If you intend to contribute to OpenSTEF or modify the source code, install the library
in editable mode directly from the repository:

.. code-block:: bash

   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install all packages in editable mode with development dependencies
   uv sync --all-extras --dev

   # Verify the development environment
   uv run pytest

This installs all OpenSTEF packages in editable mode alongside development tooling
(linting, testing, documentation). See the contributor guide for further details on
the repository structure.

Verifying the Installation
--------------------------

After installation, confirm everything is working by importing the relevant packages
in a Python session:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef[all] or openstef[beam], check BEAM too
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (install with 'pip install openstef[beam]')")

A successful run prints version strings for each installed package without raising any
errors. If you see an ``ImportError``, work through the troubleshooting steps below.

Troubleshooting
---------------

Python version error
^^^^^^^^^^^^^^^^^^^^

If installation fails with a message like:

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

Your active Python interpreter is too old. Upgrade to Python 3.12 or higher, or use
``pyenv`` / ``conda`` to create an environment with the correct version:

.. code-block:: bash

   # pyenv example
   pyenv install 3.12.4
   pyenv local 3.12.4
   pip install "openstef[all]"

Dependency conflicts
^^^^^^^^^^^^^^^^^^^^

If pip reports dependency conflicts, the most reliable fix is to install OpenSTEF into
a clean virtual environment rather than your system Python or an existing environment
with many pre-installed packages:

.. code-block:: bash

   python -m venv .venv-openstef
   source .venv-openstef/bin/activate
   pip install --upgrade pip
   pip install "openstef[all]"

Using ``uv`` instead of pip also helps here — its resolver is stricter and surfaces
conflicts more clearly before making any changes to your environment.

ImportError after installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Python can import ``openstef`` but not a specific sub-module, check that you
installed the right extras. For example, backtesting utilities live in
``openstef-beam`` and are not included in the default ``pip install openstef``:

.. code-block:: bash

   # Add the BEAM package to an existing installation
   pip install "openstef[beam]"
   # or
   uv add "openstef[beam]"

Slow installation
^^^^^^^^^^^^^^^^^

OpenSTEF has a number of scientific Python dependencies (NumPy, pandas, scikit-learn,
LightGBM, etc.) that can take time to resolve and download. Switching to ``uv``
typically reduces install time significantly due to its parallel resolver and
pre-built wheel cache:

.. code-block:: bash

   pip install uv
   uv add "openstef[all]"

Windows-specific issues
^^^^^^^^^^^^^^^^^^^^^^^

On Windows, some packages with compiled extensions (such as LightGBM) require the
`Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_.
If you see a compilation error during installation, install the Build Tools and retry.
Alternatively, using a conda environment often avoids this issue because conda
provides pre-compiled binaries.

Next Steps
----------

With OpenSTEF installed, you are ready to start forecasting:

- :doc:`quickstart` — run a complete forecast in under five minutes with minimal code
- :doc:`first_forecast` — a step-by-step tutorial that explains what is happening at
  each stage
- :doc:`backtesting` — learn how to evaluate and compare models using historical data
- :doc:`advanced_customization` — customise models, features, and pipelines for
  production use cases