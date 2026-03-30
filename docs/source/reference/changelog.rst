Changelog
=========

This page contains the complete version history of OpenSTEF, including all releases, features, bug fixes, and breaking changes. The changelog is automatically generated from the project's CHANGELOG.md file and GitHub release notes.

.. note::
   OpenSTEF follows `Semantic Versioning <https://semver.org/>`_. Version numbers follow the MAJOR.MINOR.PATCH format:
   
   - **MAJOR**: Incompatible API changes
   - **MINOR**: New functionality in a backwards-compatible manner
   - **PATCH**: Backwards-compatible bug fixes

Viewing the Changelog
----------------------

The full changelog is maintained in the repository and updated with each release. You can view it in two ways:

**In the repository:**

The CHANGELOG.md file is located in the root of the `OpenSTEF repository <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_.

**On GitHub:**

All releases are documented on the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ with detailed release notes, including:

- New features and enhancements
- Bug fixes and improvements
- Breaking changes and migration guidance
- Contributors to each release

Understanding Changelog Entries
--------------------------------

Changelog entries follow the `Conventional Commits <https://www.conventionalcommits.org/>`_ specification and are organized by type:

**feat**: New features
   New functionality added to the library, such as new models, feature engineering capabilities, or API endpoints.

**fix**: Bug fixes
   Corrections to existing functionality that resolve issues or unexpected behavior.

**docs**: Documentation changes
   Updates to documentation, examples, tutorials, or inline code comments.

**perf**: Performance improvements
   Changes that improve execution speed, memory usage, or computational efficiency.

**refactor**: Code refactoring
   Internal code improvements that don't change external behavior or add features.

**build**: Build system changes
   Updates to dependencies, build configuration, or packaging.

**ci**: Continuous integration changes
   Modifications to automated testing, deployment pipelines, or CI configuration.

**BREAKING CHANGE**: Breaking changes
   Changes that require user action when upgrading. These are clearly marked with a ``!`` in the commit type (e.g., ``feat!:``) or explicitly noted in the commit footer.

Breaking Changes
----------------

Breaking changes are prominently highlighted in release notes and changelog entries. When upgrading across major versions, review all breaking changes carefully.

.. warning::
   Always check for breaking changes before upgrading to a new major version. Migration guides are provided for significant API changes.

For detailed migration guidance when moving between major versions, see the :doc:`../guides/how_to_guides` page, which includes specific instructions for upgrading from OpenSTEF V3 to V4.

Recent Releases
---------------

The most recent releases include:

**Version 4.0.0** (Latest)
   Major release with significant architectural improvements, including:
   
   - Transition to uv-based workspace and monorepo structure
   - Improved modularity and package organization
   - Enhanced feature engineering capabilities
   - Updated dependencies and Python version support

For the complete list of changes in each version, visit the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_ or view the `CHANGELOG.md file <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_ in the repository.

Contributing to the Changelog
------------------------------

The changelog is automatically generated from commit messages and pull request information. When contributing to OpenSTEF:

1. Use conventional commit messages that clearly describe your changes
2. Include issue numbers in commit messages when applicable
3. Mark breaking changes explicitly with ``!`` or in the commit footer
4. Provide detailed descriptions for significant features or fixes

For more information on contributing, see the :doc:`../contribute/contributing_guide` page.

Release Schedule
----------------

OpenSTEF does not follow a fixed release schedule. Releases are made when:

- Significant new features are ready
- Critical bug fixes need to be deployed
- Breaking changes have been accumulated and documented

Minor releases (bug fixes and small improvements) are published more frequently than major releases. Subscribe to the `GitHub repository <https://github.com/OpenSTEF/openstef>`_ to receive notifications about new releases.