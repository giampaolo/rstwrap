Bullets after indented content
==============================

Regression for a bug found in the Sphinx changelog docs. A list item
whose continuation line starts with ``+ `` (a valid bullet character)
accidentally matches ``_match_list_item()``, causing
``_handle_list_run`` to break early. All subsequent bullets then go
through ``_handle_prose`` one-by-one. If one of those bullets exceeds
the width the fidelity guard fails and multiple bullet items get
merged into a single prose paragraph.

* An item whose continuation looks like a ``+`` bullet:
  + or ^ selectors are used here
* #8791: linkcheck: The docname for each hyperlink is not displayed
* #7118: sphinx-quickstart: questionnaire got Mojibake if libreadline unavailable
* #8094: texinfo: image files on the different directory with document are not
  copied
* #8782: todo: Cross references in todolist get broken
