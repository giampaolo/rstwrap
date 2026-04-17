Nested bullet not merged into parent
====================================

Curated example for a bug where ``_handle_list_run``'s continuation
loop only broke on *sibling* list items at the same indent. A
deeper-indent bullet at the parent's text column (a malformed,
no-blank-line nested list) was slurped into the parent's
continuation buffer and re-flowed under ``join=True``, producing
``- Parent. - Nested.`` on a single line and visibly destroying the
bullet structure.

Note: docutils parses both source and the buggy output as a single
paragraph in one list item, so the existing ``TestDocutils`` and
``TestCorpus`` invariants (doctree equality, idempotency, width,
"only prose changed") all silently accept the regression. The real
catch lives in the unit test
``tests/test_lists.py::TestListItems::test_nested_bullet_not_merged_into_parent``;
this fixture is here for documentation and to keep the input
exercised by the integration pipeline.

- Parent line short.
  - Nested item.
