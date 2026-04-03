Changelog
=========

This page documents the version history of OpenSTEF, including new features, bug fixes, breaking changes, and migration guidance. OpenSTEF follows `semantic versioning <https://semver.org/>`_ (MAJOR.MINOR.PATCH) to help you understand the impact of each release.

Understanding Version Numbers
------------------------------

OpenSTEF version numbers follow the pattern ``MAJOR.MINOR.PATCH``:

- **MAJOR**: Breaking changes that require code modifications
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes and minor improvements

For example, upgrading from 4.0.0 to 4.1.0 should work without code changes, but upgrading from 3.x to 4.0 may require migration work.

Release Channels
----------------

OpenSTEF provides different release channels:

- **Stable releases** (e.g., 4.0.0): Production-ready versions with full testing
- **Pre-releases** (e.g., 4.1.0rc1): Release candidates for testing new features
- **Development builds**: Latest changes from the main branch (not recommended for production)

Install the latest stable version with:

.. code-block:: bash

   pip install openstef

Or install a specific version:

.. code-block:: bash

   pip install openstef==4.0.0

Version 4.0.0 - Major Architecture Redesign
--------------------------------------------

Released: 2024

OpenSTEF 4.0 represents a complete architectural redesign with a modular package structure, improved type safety, and modern Python practices.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Structure**

The monolithic package has been split into specialized packages:

- ``openstef-core``: Shared utilities and dataset types
- ``openstef-models``: Core forecasting models
- ``openstef-beam``: Backtesting and evaluation tools
- ``openstef``: Meta-package that combines components

**Migration:** Update your imports to use the new package names:

.. code-block:: python

   # Old (3.x)
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import train_model
   
   # New (4.x)
   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.pipeline import train_model

**Python Version Requirement**

OpenSTEF 4.0 requires Python 3.12 or higher. Python 3.10 and 3.11 are no longer supported.

**Migration:** Upgrade your Python environment before installing OpenSTEF 4.0:

.. code-block:: bash

   # Using pyenv
   pyenv install 3.12
   pyenv local 3.12
   
   # Using conda
   conda create -n openstef python=3.12
   conda activate openstef

**State Serialization Changes**

Model serialization now includes version metadata for better forward and backward compatibility. Legacy models without version information trigger warnings.

.. code-block:: python

   import warnings
   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   
   # Loading legacy models (3.x) shows a warning
   with warnings.catch_warnings(record=True) as w:
       model = XGBQuantileOpenstfRegressor.load("legacy_model.pkl")
       if w:
           print(f"Warning: {w[0].message}")
           # "Loading legacy XGBQuantileOpenstfRegressor without version metadata."

**Migration:** Retrain and save models with OpenSTEF 4.0 to include version metadata. The library automatically migrates state from older versions when possible.

New Features
^^^^^^^^^^^^

**Versioned State Management**

All models now include version tracking for serialization:

.. code-block:: python

   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   
   model = XGBQuantileOpenstfRegressor()
   model.fit(X_train, y_train)
   
   # Save with version metadata
   model.save("model_v4.pkl")
   
   # Load with automatic migration if needed
   loaded_model = XGBQuantileOpenstfRegressor.load("model_v4.pkl")

**Improved Type Safety**

Enhanced type hints throughout the codebase improve IDE support and catch errors earlier:

.. code-block:: python

   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   import pandas as pd
   
   model = XGBQuantileOpenstfRegressor()
   
   # Type checkers now catch incorrect types
   X: pd.DataFrame = pd.DataFrame(...)
   y: pd.Series = pd.Series(...)
   
   model.fit(X, y)  # Type-safe

**Modular Installation**

Install only the components you need:

.. code-block:: bash

   # Core models only
   pip install openstef-models
   
   # Models + evaluation tools
   pip install "openstef[beam]"
   
   # Everything
   pip install "openstef[all]"

**Modern Development Tools**

The project now uses modern Python tooling:

- ``uv`` for fast dependency management
- ``ruff`` for linting and formatting
- ``pyright`` for static type checking
- ``poe`` for task automation

Improvements
^^^^^^^^^^^^

- **Performance**: Faster model training and prediction through optimized dependencies
- **Documentation**: Comprehensive restructure with practical examples and clear API reference
- **Testing**: Improved test coverage and CI/CD pipeline
- **Developer Experience**: Streamlined contribution workflow with automated checks

Bug Fixes
^^^^^^^^^

- Fixed state serialization issues with complex model configurations
- Resolved import errors in edge cases with optional dependencies
- Corrected type hints for better IDE support
- Fixed memory leaks in long-running forecasting pipelines

Migration Guide: 3.x to 4.0
----------------------------

Upgrading from OpenSTEF 3.x to 4.0 requires several changes due to the architectural redesign.

Step 1: Update Python Version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensure you're running Python 3.12 or higher:

.. code-block:: bash

   python --version  # Should show 3.12.0 or higher

Step 2: Update Package Names
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Uninstall the old package and install the new modular packages:

.. code-block:: bash

   pip uninstall openstef
   pip install "openstef[all]"  # Or specific packages you need

Step 3: Update Imports
^^^^^^^^^^^^^^^^^^^^^^^

Change all imports to use the new package structure:

.. code-block:: python

   # Models
   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.pipeline import train_model
   
   # Evaluation (if using BEAM)
   from openstef_beam.evaluation import evaluate_model

Step 4: Retrain Models
^^^^^^^^^^^^^^^^^^^^^^^

While OpenSTEF 4.0 can load legacy models, we recommend retraining to take advantage of new features:

.. code-block:: python

   from openstef_models.model.regressors import XGBQuantileOpenstfRegressor
   
   # Load legacy model (triggers warning)
   old_model = XGBQuantileOpenstfRegressor.load("legacy_model.pkl")
   
   # Retrain with same configuration
   new_model = XGBQuantileOpenstfRegressor(**old_model.get_params())
   new_model.fit(X_train, y_train)
   new_model.save("model_v4.pkl")

Step 5: Update Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Review your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # Old
   openstef>=3.0,<4.0
   
   # New
   openstef>=4.0,<5.0
   # Or specific packages
   openstef-models>=4.0,<5.0
   openstef-beam>=4.0,<5.0

Staying Updated
---------------

To check your current version:

.. code-block:: python

   import openstef_models
   print(openstef_models.__version__)

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade openstef

Subscribe to `GitHub releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications about new versions. Join the `LF Energy Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel) to discuss releases and get migration help.

Commit Conventions
------------------

OpenSTEF follows `Conventional Commits <https://www.conventionalcommits.org/>`_ for clear version history. Each commit type indicates the nature of changes:

- ``feat``: New features (triggers MINOR version bump)
- ``fix``: Bug fixes (triggers PATCH version bump)
- ``feat!`` or ``fix!``: Breaking changes (triggers MAJOR version bump)
- ``docs``: Documentation changes only
- ``refactor``: Code changes without functional impact
- ``perf``: Performance improvements
- ``test``: Test additions or corrections

Example commit messages:

.. code-block:: text

   feat(models): add transformer-based forecasting model
   
   fix(validation): handle missing weather data gracefully
   
   feat!: migrate to modular package architecture
   
   BREAKING CHANGE: Split into openstef-models and openstef-beam packages

This convention helps generate accurate changelogs and ensures semantic versioning is followed correctly.

Contributing to the Changelog
------------------------------

When contributing to OpenSTEF, your changes are automatically included in the changelog based on your commit messages. Follow these guidelines:

1. Use conventional commit format for all commits
2. Include clear descriptions of what changed and why
3. Mark breaking changes with ``!`` or ``BREAKING CHANGE:`` footer
4. Reference issue numbers when applicable (e.g., ``Fixes #123``)

For more details, see the :doc:`../contribute/development_workflow` page.