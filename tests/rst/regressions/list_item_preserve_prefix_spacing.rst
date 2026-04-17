..
    Regression: when a bullet-list item uses two spaces between the
    bullet and the text (``*  text``), the text column is 3 rather
    than 2. A nested sibling-looking bullet at column 2 is then *less
    than* the text column, so docutils parses it as a separate block
    (wrapping it in a ``<block_quote>``) rather than as nested inside
    the outer item.

    ``_handle_list_run`` normalized the bullet prefix to one space
    (``* text``), shifting the text column to 2. The nested bullet at
    column 2 then became *equal to* the text column, and docutils
    re-parsed it as nested inside the outer item -- changing the
    doctree. The bug only manifests when the outer item is long
    enough to be re-wrapped (otherwise it is kept verbatim and the
    text column is preserved). Encountered in Ansible's
    ``community/collection_contributors/collection_reviewing.rst``.

Intro.

*  Outer item one. This sentence is long enough that it will be re-wrapped by the tool at width 79.
*  Outer item two. This one is also long enough to be re-wrapped by the tool when the width is 79 characters.

  * Nested-looking bullet at column 2 -- parsed as a block_quote because its indent is below the outer item's text column (3).

*  Outer item three, also long enough to be re-wrapped by the tool when the width is 79 characters.

Trailing paragraph.
