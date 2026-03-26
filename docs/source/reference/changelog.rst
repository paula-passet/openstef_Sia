Changelog
=========

This page contains the complete version history for OpenSTEF, automatically generated from the CHANGELOG.md file and GitHub release notes. OpenSTEF follows semantic versioning and uses conventional commits to ensure clear, structured release notes.

Understanding Version Numbers
-----------------------------

OpenSTEF uses semantic versioning (SemVer) with the format MAJOR.MINOR.PATCH:

- **MAJOR** version changes include breaking changes that require code updates
- **MINOR** version changes add new features while maintaining backward compatibility  
- **PATCH** version changes include bug fixes and small improvements

Breaking changes are clearly marked with a ``!`` in commit messages and highlighted in release notes.

Changelog Format
----------------

Each release entry includes:

- **Version number** and release date
- **Breaking Changes** (if any) - marked with ⚠️ warning symbols
- **New Features** - new capabilities added to the library
- **Bug Fixes** - resolved issues and improvements
- **Documentation** - updates to guides, tutorials, and API reference
- **Internal Changes** - refactoring, testing, and build improvements

Release entries are generated from conventional commit messages following this format:

.. code-block:: text

   <type>[optional scope]: <description>
   
   [optional body]
   
   [optional footer(s)]

Common commit types include:

- ``feat``: New features for users
- ``fix``: Bug fixes
- ``docs``: Documentation changes
- ``refactor``: Code improvements without functional changes
- ``perf``: Performance improvements
- ``test``: Testing improvements
- ``build``: Build system changes
- ``ci``: Continuous integration changes

Migration Guides
----------------

For major version upgrades that include breaking changes, detailed migration guides are provided:

- **v3 to v4 Migration**: See :doc:`../guides/how_to_guides` for step-by-step upgrade instructions
- **Package Structure Changes**: OpenSTEF v4 introduced a modular package structure with separate ``openstef-core``, ``openstef-models``, and ``openstef-beam`` packages

.. note::
   
   When upgrading between major versions, always review the breaking changes section and follow the migration guide to ensure your code continues to work correctly.

GitHub Integration
------------------

This changelog combines information from multiple sources:

- **CHANGELOG.md** - maintained in the repository root
- **GitHub Releases** - created for each tagged version
- **Conventional Commits** - structured commit messages that enable automated changelog generation

All releases are tagged in Git and published to PyPI. You can view the complete release history and download specific versions from the `GitHub Releases page <https://github.com/OpenSTEF/openstef/releases>`_.

Automated Generation
--------------------

This changelog is automatically updated during the release process using tools that parse conventional commit messages. This ensures consistency and completeness while reducing manual maintenance overhead.

The automated system:

- Parses commit messages since the last release
- Groups changes by type (features, fixes, documentation, etc.)
- Identifies breaking changes from commit footers
- Generates formatted changelog entries
- Updates both CHANGELOG.md and GitHub release notes

.. warning::
   
   This page is programmatically generated and should not be edited manually. Changes will be overwritten during the next release. To suggest improvements to the changelog format, please open an issue on GitHub.

Version History
---------------

.. note::
   
   [GENERATED CONTENT] The complete version history with detailed release notes for each version will be automatically inserted here during the documentation build process.