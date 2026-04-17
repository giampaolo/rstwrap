..
    Regression: a bullet item whose continuation starts with ``+ ``
    breaks _handle_list_run early; the remaining bullets then fall
    into _handle_prose and get merged into a prose paragraph.
    Found in Sphinx changelog docs.

* An item whose continuation looks like a ``+`` bullet:
  + or ^ selectors are used here
* #8791: linkcheck: The docname for each hyperlink is not displayed
* #7118: sphinx-quickstart: questionnaire got Mojibake if libreadline unavailable
* #8094: texinfo: image files on the different directory with document are not
  copied
* #8782: todo: Cross references in todolist get broken
