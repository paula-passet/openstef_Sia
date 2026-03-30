Changelog
=========

This page contains the complete version history for OpenSTEF, automatically generated from our CHANGELOG.md file and GitHub release notes. OpenSTEF follows semantic versioning and uses conventional commits to maintain a clear, structured changelog that tracks all breaking changes, new features, and bug fixes.

About This Changelog
---------------------

OpenSTEF's changelog is automatically generated using our conventional commit system. Each entry includes:

- **Version number** following semantic versioning (MAJOR.MINOR.PATCH)
- **Release date** and GitHub release link
- **Breaking changes** clearly marked with ⚠️ BREAKING CHANGE
- **New features** introduced in each version
- **Bug fixes** and improvements
- **Documentation updates** and other changes

The changelog combines information from:

- CHANGELOG.md file maintained in the repository
- GitHub release notes with detailed descriptions
- Conventional commit messages that enable automated categorization

.. note::
   This changelog is programmatically generated and updated with each release. For the most current information, visit our `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Understanding Version Numbers
-----------------------------

OpenSTEF uses semantic versioning (SemVer) to communicate the impact of changes:

- **Major versions** (e.g., 3.0.0 → 4.0.0): Breaking changes that require code updates
- **Minor versions** (e.g., 4.0.0 → 4.1.0): New features that are backward compatible  
- **Patch versions** (e.g., 4.1.0 → 4.1.1): Bug fixes and small improvements

Breaking changes are always clearly marked and include migration guidance where applicable.

Release Categories
------------------

Each release entry is organized by change type:

**🚀 Features**
   New functionality and capabilities added to the library

**🐛 Bug Fixes**
   Issues resolved and stability improvements

**⚠️ Breaking Changes**
   Changes that require updates to existing code

**📚 Documentation**
   Updates to guides, API documentation, and examples

**🔧 Internal Changes**
   Refactoring, performance improvements, and development tooling

**🧪 Testing**
   Test coverage improvements and testing infrastructure

Migration Guidance
------------------

For major version upgrades, we provide detailed migration guides:

- **OpenSTEF 3.x to 4.0**: See our :doc:`../guides/how_to_guides` for step-by-step migration instructions
- **Breaking change details**: Each breaking change includes specific guidance for updating your code
- **Deprecation warnings**: Features scheduled for removal are marked with deprecation notices

.. warning::
   Always review breaking changes before upgrading major versions. Test your code thoroughly in a development environment before deploying to production.

Staying Updated
---------------

To stay informed about new releases:

- **Watch the repository**: Enable notifications for releases on `GitHub <https://github.com/OpenSTEF/openstef>`_
- **Check regularly**: Review this changelog before upgrading
- **Follow semantic versioning**: Patch and minor updates are generally safe to apply

.. code-block:: bash

   # Check your current version
   pip show openstef
   
   # Upgrade to latest version
   pip install --upgrade openstef
   
   # Upgrade to specific version
   pip install openstef==4.1.0

Version History
---------------

.. note::
   [AUTOMATED CONTENT: This section is automatically populated from CHANGELOG.md and GitHub releases. The content includes all version entries with their respective changes, dates, and detailed descriptions. Each version entry follows the format above with proper categorization of changes.]

For the complete, up-to-date changelog with all version details, please visit our `GitHub releases page <https://github.com/OpenSTEF/openstef/releases>`_ or view the `CHANGELOG.md file <https://github.com/OpenSTEF/openstef/blob/main/CHANGELOG.md>`_ in our repository.

Related Documentation
---------------------

- :doc:`../getting_started/quickstart` - Get started with the latest version
- :doc:`../guides/how_to_guides` - Migration guides and upgrade instructions  
- :doc:`architecture` - Understanding OpenSTEF's modular architecture
- :doc:`../project/support` - Getting help with upgrades and issues