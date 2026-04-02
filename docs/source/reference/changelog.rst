Changelog
=========

This page provides a complete version history of OpenSTEF, combining information from the project's CHANGELOG.md file and GitHub release notes. Each release includes details about new features, bug fixes, breaking changes, and improvements.

.. note:: This page is automatically generated from the project's version control history. For the most up-to-date information, see the `CHANGELOG.md file <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_ in the repository.


Understanding Version Numbers
------------------------------

OpenSTEF follows `Semantic Versioning <https://semver.org/>`_ (SemVer):

- **Major versions** (e.g., 4.0.0) introduce breaking changes that may require code updates
- **Minor versions** (e.g., 4.1.0) add new features while maintaining backward compatibility
- **Patch versions** (e.g., 4.1.1) fix bugs without changing functionality

Breaking changes are clearly marked in each release to help you plan upgrades.


How to Use This Page
---------------------

When upgrading OpenSTEF:

1. Review all versions between your current version and the target version
2. Pay special attention to breaking changes marked with ⚠️
3. Check the migration guide if upgrading across major versions (see :doc:`../guides/how_to_guides`)
4. Test your forecasting pipeline thoroughly after upgrading


Version History
---------------

The complete version history is maintained in the project repository. Below is the auto-generated changelog content:

.. note:: [CHANGELOG_CONTENT]
   
   This section is automatically populated during documentation build by parsing CHANGELOG.md and GitHub release notes. The build process extracts version numbers, release dates, feature descriptions, bug fixes, and breaking changes.


Recent Releases
^^^^^^^^^^^^^^^

.. note:: [RECENT_RELEASES]
   
   This section displays the 5 most recent releases with full details, automatically extracted from GitHub Releases API.


Migration Guides
----------------

When upgrading across major versions, additional migration steps may be required beyond the changelog entries.

**Upgrading from v3.x to v4.x**

OpenSTEF v4.0 introduced significant architectural changes. See :doc:`../guides/how_to_guides` for a comprehensive migration guide based on community feedback.

**Upgrading from v2.x to v3.x**

Earlier major version upgrades are documented in the CHANGELOG.md file with specific migration instructions for each breaking change.


Deprecation Policy
------------------

OpenSTEF follows a clear deprecation policy to give users time to adapt:

- Features are marked as deprecated at least one minor version before removal
- Deprecated features trigger warnings with clear migration instructions
- Deprecated features are removed only in major version releases

Watch for deprecation warnings in your logs when using OpenSTEF to stay ahead of breaking changes.


Contributing to the Changelog
------------------------------

The changelog is maintained through pull requests. When contributing to OpenSTEF:

- Add a changelog entry for user-facing changes
- Use clear, concise language describing the change's impact
- Categorize changes as features, bug fixes, or breaking changes
- Reference issue numbers where applicable

See the `contributing guidelines <https://github.com/OpenSTEF/openstef/blob/main/CONTRIBUTING.md>`_ for detailed instructions.


Related Documentation
---------------------

- :doc:`../getting_started/quickstart` - Get started with the latest OpenSTEF version
- :doc:`../guides/how_to_guides` - Migration guides for major version upgrades
- :doc:`architecture` - Understand how OpenSTEF components work together