List after indented hyperlink target
====================================

Regression for a bug where a bullet list following an indented
embedded hyperlink target (the continuation body of a previous
item, separated only by a blank line from the target) was not
recognised as a list. The block-start predicate needs to treat
"previous output line is indented" as a block boundary too.

* First item with a continuation body.

  .. _target: https://example.com/path/to/resource
* Second item that is long enough to exceed the seventy-nine char width limit here.
* Third item.
