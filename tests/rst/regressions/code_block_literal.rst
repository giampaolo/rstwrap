..
    Regression: a ``::`` literal block with long lines and blank lines
    must be preserved byte-for-byte. Lines exceeding the target width
    must not be wrapped or altered.

Here is an example::

   response = requests.get("https://api.example.com/v1/users", headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})

   EXPECTED_OUTPUT = "This is a very long string that definitely exceeds seventy-nine characters and should never be wrapped by the tool"

   def some_function_with_a_long_signature(first_argument, second_argument, third_argument, fourth_argument, fifth_argument):
       return first_argument + second_argument + third_argument + fourth_argument + fifth_argument

Trailing prose paragraph.
