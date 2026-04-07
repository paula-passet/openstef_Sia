Installation
============

This page covers everything you need to install OpenSTEF and verify it is working correctly. OpenSTEF 4.0 uses a modular package architecture, so you can install exactly the components your project requires.

If you already have OpenSTEF installed and want to start forecasting right away, skip ahead to the :doc:`quickstart`.

System Requirements
-------------------

Before installing OpenSTEF, ensure your system meets these requirements:

- **Python 3.12 or higher** (Python 3.13 is also supported)
- **64-bit operating system** — Windows, macOS, or Linux
- **pip**, **uv**, or **conda** as your package manager

.. note::

   OpenSTEF 4.0 requires Python 3.12+ for modern type safety features and optimal performance. If you need Python 3.10 or 3.11 support, use OpenSTEF 3.x instead.

Check your Python version:

.. code-block:: bash

   python --version

If you need to manage multiple Python versions, we recommend `pyenv <https://github.com/pyenv/pyenv>`_ or `conda <https://conda.io/>`_.

Understanding the Package Structure
------------------------------------

OpenSTEF is organized as a family of modular packages. Understanding this structure helps you install only what you need:

- **openstef** — The meta-package that bundles ``openstef-core`` and ``openstef-models`` together. This is the default starting point for most users.
- **openstef-core** — Core data structures, datasets, utilities, and base model definitions.
- **openstef-models** — Machine learning models, feature engineering transforms, and explainability tools.
- **openstef-beam** — Backtesting, Evaluation, Analysis, and Metrics (BEAM) framework for comparing and validating models.

.. note:: [DIAGRAM: Package dependency tree showing openstef meta-package depending on openstef-core and openstef-models, with openstef-beam as an optional add-on]

Quick Installation
------------------

For most users, a single command is all you need:

.. code-block:: bash

   pip install openstef

This installs the ``openstef`` meta-package, which pulls in ``openstef-core`` and ``openstef-models`` — everything required to train models and generate forecasts.

If you prefer other package managers:

.. code-block:: bash

   # Using uv (fast, Rust-based package manager)
   uv add openstef

   # Using conda
   conda install -c conda-forge openstef

   # Using pixi
   pixi add openstef

Choosing What to Install
-------------------------

OpenSTEF's modularity means you can tailor the installation to your use case.

**Complete installation** — includes all packages, recommended for research and experimentation:

.. code-block:: bash

   pip install "openstef[all]"

**Individual packages** — install only what you need for a lighter footprint:

.. code-block:: bash

   # Core utilities and datasets only
   pip install openstef-core

   # Core forecasting models (includes openstef-core)
   pip install openstef-models

   # Backtesting and evaluation tools
   pip install openstef-beam

**Selective extras via the meta-package** — mix and match:

.. code-block:: bash

   # Models + BEAM for evaluation workflows
   pip install "openstef[beam]"

   # Models + foundational models (when available)
   pip install "openstef[foundational-models]"

   # Everything
   pip install "openstef[beam,foundational-models]"

The following table summarizes which installation fits common use cases:

.. list-table:: Installation by Use Case
   :header-rows: 1
   :widths: 30 40 30

   * - Use Case
     - Command
     - What You Get
   * - Production forecasting
     - ``pip install openstef-models``
     - Lightweight core models
   * - General development
     - ``pip install openstef``
     - Core + models
   * - Model evaluation & comparison
     - ``pip install "openstef[beam]"``
     - Models + evaluation tools
   * - Research & experimentation
     - ``pip install "openstef[all]"``
     - Full toolkit

Verifying Your Installation
----------------------------

After installation, open a Python interpreter and confirm everything is working:

.. code-block:: python

   import openstef_models
   print(f"OpenSTEF Models version: {openstef_models.__version__}")

   # If you installed openstef-beam
   try:
       import openstef_beam
       print(f"OpenSTEF BEAM version: {openstef_beam.__version__}")
   except ImportError:
       print("OpenSTEF BEAM not installed (optional)")

You should see version numbers printed without errors. If you installed the full suite, both packages will report their versions.

For a more thorough check, try loading one of the built-in datasets:

.. code-block:: python

   from openstef_core.datasets import load_dataset

   data = load_dataset("solar")
   print(data.head())

If this runs without errors, your installation is ready. Head to :doc:`quickstart` to generate your first forecast.

Development Installation
------------------------

If you plan to contribute to OpenSTEF or need to modify the source code, clone the repository and install in development mode. OpenSTEF uses `uv <https://docs.astral.sh/uv/>`_ as its primary development tool.

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef

   # Install in development mode with all dependencies
   uv sync --all-extras --dev

   # Run the test suite to verify
   uv run pytest

This gives you all OpenSTEF packages in editable mode, plus development tools for linting, testing, and building documentation.

To work on a single package in isolation:

.. code-block:: bash

   cd packages/openstef-models
   uv sync --dev

Platform-Specific Notes
-----------------------

**Windows**

- Use PowerShell or Command Prompt.
- Consider `Windows Subsystem for Linux (WSL) <https://docs.microsoft.com/en-us/windows/wsl/>`_ for the best compatibility with scientific Python packages.
- Some dependencies may require `Microsoft Visual C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_.

**macOS**

- Most installations work out of the box.
- On Apple Silicon (M1/M2/M3), ensure you are using native ARM Python and compatible wheel distributions.

**Linux**

- Most distributions work without additional setup.
- If compilation of C extensions is needed, install the Python development headers:

.. code-block:: bash

   # Ubuntu / Debian
   sudo apt-get install python3-dev

   # RHEL / CentOS / Fedora
   sudo yum install python3-devel

Troubleshooting
---------------

**Python version error**

.. code-block:: text

   ERROR: Package 'openstef' requires a different Python: 3.11.0 not in '>=3.12,<4.0'

You need Python 3.12 or higher. Use ``pyenv`` or ``conda`` to install and switch to a supported version.

**Package not found in conda**

.. code-block:: bash

   # Ensure the conda-forge channel is enabled
   conda config --add channels conda-forge
   conda install openstef

**Import errors after installation**

OpenSTEF packages use underscores in their Python import names, not dots:

.. code-block:: python

   # Correct
   from openstef_models.models import LinearModel
   from openstef_beam.backtesting import Backtester

   # Wrong — this will raise ImportError
   from openstef.models import LinearModel

**Memory issues with large datasets**

If you run out of memory during model training or backtesting, consider processing data in smaller chunks or using streaming approaches. See :doc:`advanced_customization` for guidance on configuring resource usage.

Staying Updated
---------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_. To upgrade to the latest release:

.. code-block:: bash

   pip install --upgrade openstef

   # Or check your current version first
   pip show openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions.

Getting Help
------------

If you run into issues not covered here:

1. Search the `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known problems and solutions.
2. Open a new issue with details about your environment (OS, Python version, package versions, and the full error traceback).
3. Reach out to the community at openstef@lfenergy.org.

Next Steps
----------

With OpenSTEF installed, you're ready to start forecasting:

- :doc:`quickstart` — the fastest path to your first forecast
- :doc:`first_forecast` — a step-by-step tutorial with detailed explanations
- :doc:`backtesting` — learn how to evaluate and compare models