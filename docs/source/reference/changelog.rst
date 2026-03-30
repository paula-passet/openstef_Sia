Changelog
=========

This page provides a comprehensive history of OpenSTEF releases, combining information from the project's CHANGELOG.md file with GitHub release notes. The changelog is automatically generated from conventional commit messages and GitHub releases to ensure accuracy and completeness.

.. note::
   This changelog is programmatically generated and updated with each release. For the most current information, see the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Version 4.0.0 (Current Release)
-------------------------------

**Release Date:** 2024-12-XX

**Major Release - Breaking Changes**

OpenSTEF 4.0 represents a complete architectural redesign of the library, focusing on modularity, type safety, and enterprise integration. This is a major breaking change from version 3.x.

**🎯 Key Highlights**

- **Modular Architecture:** Split into specialized packages (``openstef-core``, ``openstef-models``, ``openstef-beam``)
- **Type Safety:** Full type annotations throughout the codebase
- **Enhanced Performance:** Optimized for production use cases with 10,000+ daily forecasts
- **Improved Documentation:** Following the Diátaxis framework for better user experience
- **Enterprise Ready:** Flexible APIs for system integration and custom component development

**✨ New Features**

- Modular package structure allowing selective installation
- Enhanced feature engineering with ``openstef_models.transforms``
- Comprehensive backtesting framework in ``openstef_beam.backtesting``
- Advanced model explainability tools
- Flexible configuration mechanisms replacing hard-coded assumptions
- Support for diverse data formats and structures
- Customizable holiday calendars and regional settings

**💥 Breaking Changes**

.. warning::
   OpenSTEF 4.0 introduces significant breaking changes. Migration from 3.x requires code updates.

- **Package Structure:** Functionality split across multiple packages
- **Import Paths:** All import statements need updating (e.g., ``from openstef_models import forecasting``)
- **API Changes:** Many function signatures and class interfaces have changed
- **Dependencies:** Decoupled external dependencies (MLFlow, openstef-dbc, xgboost/gblinear)
- **Configuration:** New configuration system replaces previous approaches
- **Data Formats:** More flexible but different data input requirements

**📦 Package Changes**

- ``openstef-core``: Core data structures, datasets, and utilities
- ``openstef-models``: Machine learning models and feature engineering
- ``openstef-beam``: Backtesting, evaluation, analysis and metrics
- ``openstef`` (meta-package): Convenient installation of core functionality

**🔧 Technical Improvements**

- Increased test coverage and streamlined test execution
- Standardized coding practices and documentation styles
- Centralized data preprocessing logic
- Enhanced error handling and validation
- Improved performance optimizations
- Better memory management for large datasets

**📚 Documentation Updates**

- Complete documentation overhaul following Diátaxis framework
- New getting started guide with improved onboarding
- Comprehensive migration guide from 3.x to 4.0
- Enhanced API reference with detailed examples
- Use case-specific guides for different forecasting scenarios

**🐛 Bug Fixes**

- Resolved data preprocessing inconsistencies
- Fixed edge cases in model validation
- Improved handling of missing weather data
- Enhanced error messages and debugging information

**⚡ Performance Improvements**

- Optimized forecasting pipeline for production workloads
- Reduced memory footprint for large datasets
- Improved model training and inference speed
- Enhanced parallel processing capabilities

**🔄 Migration Guide**

For detailed migration instructions, see our `Migration Guide <../guides/how_to_guides.html>`_. Key migration steps:

1. Update package installations to new modular structure
2. Modify import statements to use new package names
3. Update configuration files to new format
4. Adapt data input formats if necessary
5. Review and update custom model implementations

Previous Versions
-----------------

Version 3.x Series
^^^^^^^^^^^^^^^^^^

**Version 3.7.x**

- Final stable release of the 3.x series
- Production-ready forecasting capabilities
- Integrated MLFlow support
- Comprehensive evaluation metrics

**Version 3.6.x**

- Enhanced model validation
- Improved weather data handling
- Performance optimizations
- Bug fixes and stability improvements

**Version 3.5.x**

- Extended forecasting horizons
- Additional model types
- Enhanced feature engineering
- Documentation improvements

**Version 3.0.x - 3.4.x**

- Initial stable releases
- Core forecasting functionality
- Basic evaluation and backtesting
- Foundation for production deployments

.. note::
   For detailed version 3.x changelogs, refer to the `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_ or the CHANGELOG.md file in the repository.

Version 2.x and Earlier
^^^^^^^^^^^^^^^^^^^^^^^

Earlier versions of OpenSTEF were primarily used within Alliander and are not recommended for new installations. These versions lacked the modularity and flexibility of the current architecture.

Release Process
---------------

OpenSTEF follows semantic versioning (SemVer) and uses conventional commits for automated changelog generation:

**Version Numbering**

- **Major (X.0.0):** Breaking changes, architectural updates
- **Minor (X.Y.0):** New features, backward-compatible changes  
- **Patch (X.Y.Z):** Bug fixes, security updates

**Commit Types**

- ``feat``: New features
- ``fix``: Bug fixes
- ``docs``: Documentation changes
- ``perf``: Performance improvements
- ``refactor``: Code refactoring
- ``test``: Test additions or corrections
- ``build``: Build system changes
- ``ci``: CI/CD configuration changes

**Release Schedule**

- **Major releases:** Annual or bi-annual for significant architectural changes
- **Minor releases:** Quarterly for new features and enhancements
- **Patch releases:** As needed for critical bug fixes and security updates

Getting Updates
---------------

To stay informed about new releases:

- **GitHub Releases:** Subscribe to `repository notifications <https://github.com/OpenSTEF/openstef/releases>`_
- **Community Channels:** Join our `Slack workspace <https://slack.lfenergy.org/>`_ (#openstef channel)
- **Mailing List:** Contact ``openstef@lfenergy.org`` for announcements

**Upgrading**

.. code-block:: bash

   # Check current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef
   
   # Or with uv
   uv upgrade openstef

For major version upgrades, always review the migration guide and test thoroughly in a development environment before upgrading production systems.

Support and Compatibility
--------------------------

**Supported Versions**

- **4.x:** Current stable series with active development and support
- **3.x:** Legacy support for critical security issues only (until 2025)
- **2.x and earlier:** No longer supported

**Python Compatibility**

- **4.x:** Python 3.12+ (Python 3.13 supported)
- **3.x:** Python 3.10+ (deprecated)

**Deprecation Policy**

Features marked as deprecated will be removed in the next major version. Deprecation warnings are issued for at least one minor release cycle before removal.

For questions about specific versions or upgrade paths, see our `Support page <../project/support.html>`_ or contact the development team.