..
    Regression: unindented doctest blocks at column 0 must be passed
    through verbatim. The tool was merging them into prose because
    ``>>>`` didn't match any special-case check in the main loop.
    Found in ``cpython/Doc/faq/programming.rst``.

This is illustrated by this example:

>>> very_long_variable_name = some_function_with_many_args(first_argument, second_argument, third_argument)
>>> another_long_line = dict(alpha="value1", bravo="value2", charlie="value3", delta="value4", echo="value5")
13901272

The two ids belong to different objects.
