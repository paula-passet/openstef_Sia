Changelog
=========

OpenSTEF follows `semantic versioning <https://semver.org/>`_. This page documents the version history of OpenSTEF releases, including new features, bug fixes, improvements, and breaking changes.

For detailed migration instructions when upgrading between major versions, see the :doc:`Migration Guide <user_guide/migration_guide>`.

.. note::

   OpenSTEF 4.0 introduced a modular architecture with separate packages. Version numbers may differ across packages (``openstef-core``, ``openstef-models``, ``openstef-beam``), but the meta-package ``openstef`` coordinates compatible versions.

Version 4.0.0 (2024)
--------------------

**Release Date:** 2024

OpenSTEF 4.0 represents a major architectural redesign focused on modularity, modern Python standards, and improved developer experience.

Breaking Changes
^^^^^^^^^^^^^^^^

**Modular Package Architecture**

OpenSTEF is now split into multiple specialized packages:

- ``openstef-core``: Shared data types, utilities, and dataset definitions
- ``openstef-models``: Core forecasting models and feature engineering
- ``openstef-beam``: Backtesting, evaluation, and model analysis tools
- ``openstef``: Meta-package that coordinates compatible versions

**Migration impact:** All import paths have changed. Code using OpenSTEF 3.x will need updates.

.. code-block:: python

   # OpenSTEF 3.x
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering import apply_features
   
   # OpenSTEF 4.0
   from openstef_models.regressors import XGBQuantileRegressor
   from openstef_models.transforms import FeatureAdder

**Python Version Requirements**

- Minimum Python version: 3.12 (previously 3.10)
- Python 3.13 is supported
- Python 3.10 and 3.11 are no longer supported

**Reason:** Modern type safety features, improved performance, and better async support.

**State Serialization**

Models now use versioned state serialization with automatic migration:

.. code-block:: python

   # Models implement VersionedStateful protocol
   from openstef_models.regressors import XGBQuantileRegressor
   
   model = XGBQuantileRegressor()
   model.fit(X_train, y_train)
   
   # Save with version metadata
   state = model.__getstate__()
   # {'__version__': 1, 'state': {...}}
   
   # Load automatically migrates from older versions
   model.__setstate__(state)

**Import Structure**

Package names now use underscores instead of hyphens in imports:

.. code-block:: python

   # Correct
   import openstef_models
   import openstef_core
   import openstef_beam
   
   # Incorrect
   import openstef-models  # SyntaxError

New Features
^^^^^^^^^^^^

**Flexible Installation Options**

Install only what you need:

.. code-block:: bash

   # Minimal installation (core + models)
   pip install openstef
   
   # Full installation
   pip install "openstef[all]"
   
   # Specific packages
   pip install openstef-models
   pip install openstef-beam
   
   # Selective extras
   pip install "openstef[beam,foundational-models]"

**Modern Development Tooling**

- ``uv`` workspace support for fast dependency management
- Unified task runner with ``poethedev`` (``poe`` command)
- Pre-commit hooks for code quality
- Improved CI/CD pipelines

**Enhanced Type Safety**

- Comprehensive type hints throughout the codebase
- Runtime type validation with Pydantic v2
- Better IDE support and autocomplete

**Improved Feature Engineering**

New transform-based feature engineering pipeline:

.. code-block:: python

   from openstef_models.transforms import (
       FeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_core.datasets import TimeSeriesDataset
   
   # Compose transforms
   feature_adder = FeatureAdder()
   lags_adder = LagsAdder(lags=[1, 2, 24])
   
   # Apply to dataset
   data = TimeSeriesDataset(...)
   data = feature_adder.fit_transform(data)
   data = lags_adder.fit_transform(data)

**Versioned State Management**

Models automatically handle version migrations:

.. code-block:: python

   from openstef_models.regressors import XGBQuantileRegressor
   
   class CustomRegressor(XGBQuantileRegressor):
       _VERSION = 2  # Increment when state format changes
       
       def _migrate_state(self, state, from_version, to_version):
           """Migrate state from older versions."""
           if from_version == 1 and to_version == 2:
               # Transform state format
               state['new_field'] = default_value
           return state

Improvements
^^^^^^^^^^^^

**Performance**

- Faster data loading with optimized pandas operations
- Reduced memory footprint in feature engineering
- Parallel processing utilities for batch operations

**Documentation**

- Completely rewritten documentation with practical examples
- Separate API reference for each package
- Improved tutorials and guides
- Better search functionality

**Testing**

- Increased test coverage across all packages
- Property-based testing with Hypothesis
- Improved integration tests
- Faster test execution

**Developer Experience**

- Simplified contribution workflow
- Better error messages with actionable guidance
- Consistent code style with Ruff
- Automated formatting and linting

Deprecations
^^^^^^^^^^^^

The following features from OpenSTEF 3.x are deprecated and will be removed:

- Monolithic package structure (replaced by modular packages)
- Legacy configuration formats (use Pydantic models)
- Old import paths (update to new package structure)

Bug Fixes
^^^^^^^^^

- Fixed edge cases in datetime alignment utilities
- Improved handling of missing weather data
- Corrected timezone handling in feature engineering
- Fixed memory leaks in long-running forecasting pipelines

Migration Guide
^^^^^^^^^^^^^^^

For detailed migration instructions, see :doc:`user_guide/migration_guide`. Key steps:

1. **Update Python version** to 3.12 or higher
2. **Update dependencies** in your ``requirements.txt`` or ``pyproject.toml``
3. **Update import statements** to use new package names
4. **Review breaking changes** in model APIs and configuration
5. **Test thoroughly** with your existing data and workflows

.. code-block:: bash

   # Check your Python version
   python --version  # Should be 3.12+
   
   # Upgrade OpenSTEF
   pip install --upgrade "openstef[all]"
   
   # Verify installation
   python -c "import openstef_models; print(openstef_models.__version__)"

Version 3.x
-----------

OpenSTEF 3.x was the last version with a monolithic package structure and support for Python 3.10/3.11.

For users still on OpenSTEF 3.x:

- Security updates will be provided for critical vulnerabilities
- No new features will be added
- Consider upgrading to 4.0 for new functionality and improvements

Version 2.x and Earlier
-----------------------

Historical versions prior to 3.0 are no longer maintained. Documentation for these versions is available in the `GitHub repository history <https://github.com/OpenSTEF/openstef/releases>`_.

Release Cadence
---------------

OpenSTEF follows a predictable release schedule:

- **Major releases** (X.0.0): Annual, with breaking changes and new features
- **Minor releases** (4.X.0): Quarterly, with new features and improvements (backward compatible)
- **Patch releases** (4.0.X): As needed, with bug fixes and security updates

Staying Updated
---------------

To stay informed about new releases:

**GitHub Releases**

Subscribe to `OpenSTEF releases <https://github.com/OpenSTEF/openstef/releases>`_ for notifications.

**Check Your Version**

.. code-block:: python

   import openstef_models
   import openstef_core
   import openstef_beam
   
   print(f"openstef-models: {openstef_models.__version__}")
   print(f"openstef-core: {openstef_core.__version__}")
   print(f"openstef-beam: {openstef_beam.__version__}")

**Upgrade**

.. code-block:: bash

   # Upgrade all packages
   pip install --upgrade "openstef[all]"
   
   # Or with uv
   uv upgrade openstef

**Version Compatibility**

The ``openstef`` meta-package ensures compatible versions across all packages. When you install ``openstef==4.0.0``, it automatically installs compatible versions of:

- ``openstef-core``
- ``openstef-models``
- ``openstef-beam`` (if using ``[all]`` or ``[beam]`` extras)

Semantic Versioning
-------------------

OpenSTEF follows `semantic versioning <https://semver.org/>`_ (SemVer):

**Major version** (X.0.0)
   Breaking changes that require code updates. Examples:

   - Removed or renamed APIs
   - Changed function signatures
   - New required dependencies
   - Python version requirement changes

**Minor version** (4.X.0)
   New features and improvements, backward compatible. Examples:

   - New models or transforms
   - Additional optional parameters
   - Performance improvements
   - New utility functions

**Patch version** (4.0.X)
   Bug fixes and security updates, backward compatible. Examples:

   - Fixed calculation errors
   - Corrected edge case handling
   - Security vulnerability patches
   - Documentation corrections

Deprecation Policy
------------------

When we deprecate features:

1. **Announcement**: Deprecation is announced in release notes
2. **Warning period**: Feature remains available with deprecation warnings for at least one minor version
3. **Removal**: Feature is removed in the next major version

.. code-block:: python

   # Deprecated feature shows warning
   import warnings
   
   def old_function():
       warnings.warn(
           "old_function is deprecated and will be removed in v5.0. "
           "Use new_function instead.",
           DeprecationWarning,
           stacklevel=2
       )

Contributing to Releases
------------------------

To contribute to OpenSTEF releases:

**Report Bugs**

Open an issue on `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ with:

- OpenSTEF version
- Python version
- Minimal reproduction example
- Expected vs actual behavior

**Suggest Features**

Feature requests are welcome! Describe:

- Use case and motivation
- Proposed API or interface
- Example usage code

**Submit Pull Requests**

Follow our :doc:`contribution guidelines <contribute/index>`:

- Use conventional commit messages (``feat:``, ``fix:``, ``docs:``)
- Include tests for new features
- Update documentation
- Ensure CI passes

**Commit Message Format**

.. code-block:: text

   <type>[optional scope]: <description>
   
   [optional body]
   
   [optional footer(s)]

Types: ``feat``, ``fix``, ``docs``, ``style``, ``refactor``, ``perf``, ``test``, ``build``, ``ci``, ``chore``

Example:

.. code-block:: text

   feat(models): add transformer-based forecasting model
   
   Implement attention mechanism for temporal dependencies.
   Add comprehensive tests with 95% coverage.
   Update documentation with usage examples.
   
   Closes #123

Support and Questions
---------------------

For questions about releases:

- **Slack**: Join `LF Energy Slack <https://slack.lfenergy.org/>`_ (#openstef channel)
- **Email**: openstef@lfenergy.org
- **GitHub Discussions**: `OpenSTEF Discussions <https://github.com/OpenSTEF/openstef/discussions>`_

See our :doc:`Support page <project/support>` for more resources.