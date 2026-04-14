Bullet items after indented content
====================================

Bullet items that immediately follow indented content (no blank line
between them) must not be merged into a single prose run. This was
found in the Sphinx changelog docs where items like the ones below
appear right after a multi-line bullet's continuation line.

* A long bullet item that has a continuation line indented to the
  text column, immediately followed by more bullets.
* #8791: linkcheck: The docname for each hyperlink is not displayed
* #7118: sphinx-quickstart: questionnaire got Mojibake if libreadline unavailable
* #8094: texinfo: image files on the different directory with document are not
  copied
* #8782: todo: Cross references in todolist get broken
