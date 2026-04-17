
---

Alternatively, if you want working hyperlinks, add explicit RST labels immediately before each target heading and use ``:ref:`` roles. Add a label line (with a blank line after) before each heading:

**Before "Breaking Change 1" heading**, add:

.. code-block:: rst

   .. _breaking-change-1:

   Breaking Change 1: Package Imports
   -----------------------------------

**Before "Breaking Change 4" heading**, add:

.. code-block:: rst

   .. _breaking-change-4:

   Breaking Change 4: Backtesting and Evaluation
   ----------------------------------------------

Then update the references to use ``:ref:``:

.. code-block:: rst

   # Line 331
   Use the table in :ref:`breaking-change-1` as a reference.

   # Line 341
   See :ref:`breaking-change-4` for the pattern.

The label approach is preferred for RST documents because ``:ref:`` links survive heading renames and work across files, while backtick-style anonymous references only work when the target name exactly matches the heading text with no special characters.