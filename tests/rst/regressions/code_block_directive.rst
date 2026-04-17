..
    Regression: a ``.. code-block::`` directive body with long lines
    and blank lines must be preserved byte-for-byte. The tool must
    not wrap, merge, or alter any line inside the block.

Some prose before.

.. code-block:: python

   response = requests.get("https://api.example.com/v1/users", headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})

   EXPECTED_OUTPUT = "This is a very long string that definitely exceeds seventy-nine characters and should never be wrapped by the tool"

   def some_function_with_a_long_signature(first_argument, second_argument, third_argument, fourth_argument, fifth_argument):
       return first_argument + second_argument + third_argument + fourth_argument + fifth_argument

Some prose after.
