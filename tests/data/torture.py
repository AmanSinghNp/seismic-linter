"""
This file contains complex and edge-case Python syntax to stress-test the AST parser.
It is not intended to be executed or tested for logic, but merely to ensure the linter
does not crash when encountering valid and complex Python code (walrus operators,
match statements, async, etc.).
"""

import asyncio
import pandas as pd

# Walrus operator (Python 3.8+)
if (n := len([1, 2, 3])) > 2:
    x = n


# Nested classes and functions
class Outer:
    class Inner:
        def method(self):
            def inner_func():
                return 42

            return inner_func()


# Lambdas with complex args
def f(x, y=1, *args, **kwargs):
    return x + y


# List comprehensions with multiple clauses
result = [x * y for x in range(10) if x > 5 for y in range(5) if y < 2]

# Generator expressions
gen = (x for x in range(10))


# Async syntax
async def async_func():
    await asyncio.sleep(1)


# Match statements (Python 3.10+)
def match_test(status):
    match status:
        case 400:
            return "Bad Request"
        case 404:
            return "Not Found"
        case _:
            return "Something's wrong with the internet"


# Type aliasing (Modified to be 3.10 compatible)
Point = tuple[int, int]

# Complex slicing
df = pd.DataFrame({"a": range(10)})
subset = df.iloc[lambda d: d["a"] > 5]


# Function annotations with pipes (Python 3.10+)
def process(data: int | str) -> None:
    pass
