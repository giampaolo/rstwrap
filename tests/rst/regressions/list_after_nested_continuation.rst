List sibling after nested body and continuation
================================================

Regression for a bug where a sibling bullet at column 0, following
a parent item whose body contained a nested bullet list plus a
continuation paragraph (all indented), was not recognised as a new
list item. The block-start predicate needs to treat the indented
continuation line as a block boundary.

* Parent item:

  * Nested item one.
  * Nested item two.

  Continuation paragraph of the parent item.
* Sibling item that is long enough to exceed the seventy-nine char width limit here.
* Another sibling.
