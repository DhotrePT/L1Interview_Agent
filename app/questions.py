"""Question banks.

Every interview is 1 introduction + 3 theory + 3 coding = 7 items, and the weights add
up to 100 so the scorecard is naturally "out of 100". Which banks a post draws from is
decided in app/jobs.py.

Each question carries a "difficulty" of "easy" or "medium" (missing means "medium").
This is an L1 screen for freshers, so a paper is deliberately weighted towards easy:
see EASY_PER_SECTION in app/jobs.py. Difficulty is a sampling hint only - it never
reaches the browser and it does not change the marks, which stay 15 per question.
"""
from __future__ import annotations

from typing import Any

INTRO_QUESTION: dict[str, Any] = {
    "id": "q1_intro",
    "type": "intro",
    "weight": 10,
    "title": "Introduce yourself",
    "prompt": (
        "Please introduce yourself. Cover: your background and education, the Python work "
        "you have done (projects, internships or jobs), the libraries and tools you are "
        "comfortable with, and why you are interested in this role."
    ),
    "expectations": [
        "Clear, structured self-introduction (background -> experience -> skills -> motivation).",
        "Concrete Python work with named projects, libraries or tools.",
        "Relevance to the job description.",
        "Confident, understandable communication.",
    ],
    "suggested_minutes": 3,
}

PYTHON_THEORY: list[dict[str, Any]] = [
    {
        "id": "t_mutability",
        "type": "theory",
        "weight": 15,
        "title": "Mutable vs immutable types",
        "prompt": (
            "Explain the difference between mutable and immutable types in Python. Give at "
            "least two examples of each, and explain what happens when a mutable object is "
            "used as the default argument of a function."
        ),
        "expectations": [
            "list/dict/set are mutable; int/str/tuple/frozenset are immutable.",
            "Rebinding vs in-place mutation and the effect on shared references.",
            "A mutable default is evaluated once at def time and shared across calls; the "
            "fix is `def f(x=None): x = [] if x is None else x`.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_collections",
        "type": "theory",
        "weight": 15,
        "title": "list vs tuple vs set vs dict",
        "prompt": (
            "Compare list, tuple, set and dict. When would you pick each one? What is the "
            "average time complexity of a membership test (`x in collection`) for a list "
            "versus a set or dict, and why is there a difference?"
        ),
        "expectations": [
            "Ordered mutable list, immutable tuple, unique unordered set, key-value dict.",
            "O(n) membership for list, O(1) average for set/dict.",
            "Hashing explains the difference; keys must be hashable.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_exceptions",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Exception handling",
        "prompt": (
            "Explain Python exception handling: try / except / else / finally. What is the "
            "difference between catching `Exception` and catching a specific exception? "
            "When would you define a custom exception?"
        ),
        "expectations": [
            "else runs when no exception was raised; finally always runs (cleanup).",
            "A broad except hides bugs; bare except also swallows KeyboardInterrupt.",
            "Custom exceptions carry domain meaning and let callers handle selectively.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_oop",
        "type": "theory",
        "weight": 15,
        "title": "OOP in Python",
        "prompt": (
            "What is the difference between a class attribute and an instance attribute? "
            "Explain `__init__` and `self`, give an example of inheritance with method "
            "overriding, and say what `super()` does."
        ),
        "expectations": [
            "Class attribute shared by all instances; instance attribute is per object.",
            "__init__ initialises (does not construct) an instance; self is the instance.",
            "super() delegates to the next class in the MRO.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_generators",
        "type": "theory",
        "weight": 15,
        "title": "Comprehensions and generators",
        "prompt": (
            "What is a list comprehension, and how does a generator expression differ from "
            "it? What does the `yield` keyword do? Give a case where a generator is clearly "
            "the better choice."
        ),
        "expectations": [
            "A comprehension builds the whole list in memory; a generator is lazy.",
            "yield turns a function into a generator that resumes where it left off.",
            "Large files, streams and infinite sequences favour generators.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_copy",
        "type": "theory",
        "weight": 15,
        "title": "Shallow vs deep copy",
        "prompt": (
            "For a nested list, explain the difference between assignment (`b = a`), a "
            "shallow copy and a deep copy. How do you create each one, and what breaks if "
            "you pick the wrong one?"
        ),
        "expectations": [
            "Assignment binds the same object; id() is unchanged.",
            "copy.copy / a[:] copies the outer container only; inner objects stay shared.",
            "copy.deepcopy recurses; needed for nested mutable structures.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_basic_types",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Basic data types and conversion",
        "prompt": (
            "Name the basic data types you use in Python and give one example value of each. "
            "What does `type(x)` tell you? What happens when you run `int('12')`, `int('abc')` "
            "and `'5' + 5`, and how would you fix the last two?"
        ),
        "expectations": [
            "int, float, str, bool, list, dict (tuple/set a bonus) with sensible examples.",
            "int('12') -> 12; int('abc') raises ValueError; '5' + 5 raises TypeError.",
            "Fix by converting explicitly: int('5') + 5, or str(5) to concatenate.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_loops_conditionals",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Loops and conditionals",
        "prompt": (
            "Explain the difference between a `for` loop and a `while` loop, and give one "
            "situation where each is the natural choice. What does `range(2, 10, 2)` produce? "
            "What is the difference between `break` and `continue`?"
        ),
        "expectations": [
            "for iterates a known sequence; while repeats until a condition changes.",
            "range(2, 10, 2) -> 2, 4, 6, 8 (stop is excluded).",
            "break leaves the loop entirely; continue skips to the next iteration.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_functions_basics",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Functions and arguments",
        "prompt": (
            "What is a function and why would you write one instead of repeating code? "
            "Explain the difference between a parameter and an argument, what a default "
            "argument is, and what a function returns if it has no `return` statement."
        ),
        "expectations": [
            "Reuse, naming a step, testing it in isolation.",
            "Parameter is the name in the def; argument is the value passed in.",
            "A function with no return gives back None.",
        ],
        "suggested_minutes": 3,
    },
]

PYTHON_CODING: list[dict[str, Any]] = [
    {
        "id": "c_second_largest",
        "type": "coding",
        "weight": 15,
        "title": "Second largest number",
        "prompt": (
            "Write a function `second_largest(nums)` that returns the second largest "
            "DISTINCT number in a list of integers, or None if there isn't one.\n\n"
            "Examples:\n"
            "    second_largest([4, 1, 9, 9, 7]) -> 7\n"
            "    second_largest([3, 3, 3])       -> None\n"
            "    second_largest([5])             -> None\n\n"
            "Try to do it in a single pass instead of sorting, and state the time complexity "
            "of your solution when you explain it."
        ),
        "starter_code": (
            "def second_largest(nums):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(second_largest([4, 1, 9, 9, 7]))  # 7\n"
            "print(second_largest([3, 3, 3]))        # None\n"
            "print(second_largest([5]))              # None\n"
        ),
        "expectations": [
            "Handles duplicates and inputs with fewer than 2 distinct values.",
            "Single pass O(n) with two trackers, or a defensible set/sorted solution.",
            "Returns None instead of raising on the edge cases.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_top_words",
        "type": "coding",
        "weight": 15,
        "title": "Word frequency",
        "prompt": (
            "Write a function `top_words(text, n)` that returns the `n` most frequent words "
            "in `text` as a list of (word, count) tuples, sorted by count descending and "
            "then alphabetically. Words are case-insensitive and punctuation is ignored.\n\n"
            "Example:\n"
            "    top_words('The cat the hat. A CAT!', 2) -> [('cat', 2), ('the', 2)]\n\n"
            "Mention which standard-library helpers you used and why."
        ),
        "starter_code": (
            "def top_words(text, n):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(top_words('The cat the hat. A CAT!', 2))  # [('cat', 2), ('the', 2)]\n"
        ),
        "expectations": [
            "Normalises case and strips punctuation (regex or str.translate).",
            "Counts with a dict or collections.Counter.",
            "Correct tie-breaking: count descending, then word ascending.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_group_anagrams",
        "type": "coding",
        "weight": 15,
        "title": "Group anagrams",
        "prompt": (
            "Write a function `group_anagrams(words)` that groups words which are anagrams "
            "of each other. Return a list of groups; each group is sorted alphabetically, "
            "and the groups themselves are sorted by their first word.\n\n"
            "Example:\n"
            "    group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat'])\n"
            "    -> [['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]\n\n"
            "Explain the grouping key you chose and the complexity."
        ),
        "starter_code": (
            "def group_anagrams(words):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(group_anagrams(['eat', 'tea', 'tan', 'ate', 'nat', 'bat']))\n"
        ),
        "expectations": [
            "Uses a dict keyed by sorted letters (or a letter-count tuple).",
            "Applies the required sorting inside groups and across groups.",
            "Explains the O(n * k log k) complexity.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_flatten",
        "type": "coding",
        "weight": 15,
        "title": "Flatten a nested list",
        "prompt": (
            "Write a function `flatten(items)` that flattens an arbitrarily nested list of "
            "integers into one flat list, preserving order.\n\n"
            "Example:\n"
            "    flatten([1, [2, [3, 4], 5], [], [[6]]]) -> [1, 2, 3, 4, 5, 6]\n\n"
            "Explain whether your solution is recursive or iterative and what happens with "
            "very deep nesting."
        ),
        "starter_code": (
            "def flatten(items):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(flatten([1, [2, [3, 4], 5], [], [[6]]]))  # [1, 2, 3, 4, 5, 6]\n"
        ),
        "expectations": [
            "Correct recursion (or an explicit stack) with an isinstance check.",
            "Handles empty lists and deep nesting.",
            "Mentions Python's recursion limit for the recursive version.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_dept_summary",
        "type": "coding",
        "weight": 15,
        "title": "Summarise records",
        "prompt": (
            "You are given a list of dicts such as\n"
            "    records = [{'dept': 'eng', 'name': 'A', 'salary': 100}, ...]\n\n"
            "Write `dept_summary(records)` that returns a dict mapping each department to "
            "{'count': int, 'total': int, 'avg': float}, where avg is rounded to 2 decimals. "
            "Departments with no records must not appear.\n\n"
            "Then explain how you would change the code if the input were a 2 GB CSV file."
        ),
        "starter_code": (
            "records = [\n"
            "    {'dept': 'eng', 'name': 'A', 'salary': 100},\n"
            "    {'dept': 'eng', 'name': 'B', 'salary': 150},\n"
            "    {'dept': 'hr',  'name': 'C', 'salary': 90},\n"
            "]\n\n\n"
            "def dept_summary(records):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(dept_summary(records))\n"
        ),
        "expectations": [
            "Single-pass accumulation into a dict (or defaultdict).",
            "Correct rounding and no division by zero.",
            "For the 2 GB file: stream row by row with csv.reader / generators.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_count_vowels",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Count the vowels",
        "prompt": (
            "Write a function `count_vowels(text)` that returns how many vowels (a, e, i, o, u) "
            "are in `text`. Upper case and lower case both count.\n\n"
            "Examples:\n"
            "    count_vowels('Hello World') -> 3\n"
            "    count_vowels('xyz')         -> 0\n"
            "    count_vowels('')            -> 0\n\n"
            "Walk through your loop out loud as you write it."
        ),
        "starter_code": (
            "def count_vowels(text):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(count_vowels('Hello World'))  # 3\n"
            "print(count_vowels('xyz'))          # 0\n"
            "print(count_vowels(''))             # 0\n"
        ),
        "expectations": [
            "Loops over the characters and compares against a vowel set or string.",
            "Handles upper case, e.g. by lowercasing first.",
            "Empty string returns 0 without crashing.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_sum_even",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Sum the even numbers",
        "prompt": (
            "Write a function `sum_even(nums)` that returns the sum of only the even numbers "
            "in a list of integers. An empty list gives 0.\n\n"
            "Examples:\n"
            "    sum_even([1, 2, 3, 4, 5, 6]) -> 12\n"
            "    sum_even([1, 3, 5])          -> 0\n"
            "    sum_even([])                 -> 0\n\n"
            "Explain how you test whether a number is even."
        ),
        "starter_code": (
            "def sum_even(nums):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(sum_even([1, 2, 3, 4, 5, 6]))  # 12\n"
            "print(sum_even([1, 3, 5]))           # 0\n"
            "print(sum_even([]))                  # 0\n"
        ),
        "expectations": [
            "Uses n % 2 == 0 to test evenness.",
            "Accumulates in a loop, or sum() with a comprehension/filter.",
            "Empty list returns 0, not None or an error.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_fizzbuzz",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "FizzBuzz",
        "prompt": (
            "Write a function `fizzbuzz(n)` that returns a LIST of strings for the numbers "
            "1 to n: 'Fizz' if the number divides by 3, 'Buzz' if it divides by 5, 'FizzBuzz' "
            "if it divides by both, otherwise the number as a string.\n\n"
            "Example:\n"
            "    fizzbuzz(5) -> ['1', '2', 'Fizz', '4', 'Buzz']\n\n"
            "Say out loud why the order of your checks matters."
        ),
        "starter_code": (
            "def fizzbuzz(n):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(fizzbuzz(5))   # ['1', '2', 'Fizz', '4', 'Buzz']\n"
            "print(fizzbuzz(15))  # ends with 'FizzBuzz'\n"
        ),
        "expectations": [
            "Checks the divisible-by-15 (or both) case FIRST, or builds the word by parts.",
            "Returns strings in a list, and the plain number is stringified.",
            "Loops over range(1, n + 1) - inclusive of n.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_is_palindrome",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Palindrome check",
        "prompt": (
            "Write a function `is_palindrome(text)` that returns True if `text` reads the same "
            "forwards and backwards, ignoring spaces and capital letters.\n\n"
            "Examples:\n"
            "    is_palindrome('Never odd or even') -> True\n"
            "    is_palindrome('hello')             -> False\n"
            "    is_palindrome('Madam')             -> True\n\n"
            "Explain how you reversed the text."
        ),
        "starter_code": (
            "def is_palindrome(text):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(is_palindrome('Never odd or even'))  # True\n"
            "print(is_palindrome('hello'))              # False\n"
            "print(is_palindrome('Madam'))              # True\n"
        ),
        "expectations": [
            "Normalises first: lowercases and removes spaces.",
            "Compares against the reverse, e.g. cleaned == cleaned[::-1].",
            "Returns a real True/False, not a string.",
        ],
        "suggested_minutes": 4,
    },
]

SQL_THEORY: list[dict[str, Any]] = [
    {
        "id": "t_sql_joins",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "SQL joins",
        "prompt": (
            "Explain INNER JOIN, LEFT JOIN and FULL OUTER JOIN. If table A has 10 rows and "
            "table B has 4 matching rows, how many rows does each join return? When does a "
            "LEFT JOIN silently hide a data problem?"
        ),
        "expectations": [
            "INNER keeps matches only; LEFT keeps all left rows with NULLs on the right.",
            "Row-count reasoning, including fan-out when the join key is not unique.",
            "NULLs from a LEFT JOIN can mask missing reference data or break aggregates.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_sql_group_by",
        "type": "theory",
        "weight": 15,
        "title": "GROUP BY, HAVING and WHERE",
        "prompt": (
            "What is the difference between WHERE and HAVING? In what order does SQL "
            "logically evaluate FROM, WHERE, GROUP BY, HAVING, SELECT and ORDER BY? Why can "
            "you not use a SELECT alias in a WHERE clause?"
        ),
        "expectations": [
            "WHERE filters rows before grouping; HAVING filters groups after aggregation.",
            "Logical order FROM -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY.",
            "Aliases are created at SELECT time, after WHERE has already run.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_sql_index",
        "type": "theory",
        "weight": 15,
        "title": "Indexes and slow queries",
        "prompt": (
            "What is a database index and how does it make a query faster? What does it cost "
            "you? Name two things that stop an index from being used, and say how you would "
            "find out why a query is slow."
        ),
        "expectations": [
            "B-tree lookup instead of a full scan; index on the filtered/joined column.",
            "Cost: slower writes and extra storage.",
            "Functions on the column, leading wildcards, type mismatch; EXPLAIN / query plan.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_pandas_basics",
        "type": "theory",
        "weight": 15,
        "title": "pandas fundamentals",
        "prompt": (
            "What is the difference between a pandas Series and a DataFrame? Explain `loc` "
            "versus `iloc`. How would you handle missing values, and why is chained indexing "
            "(`df[df.a > 1]['b'] = 0`) a problem?"
        ),
        "expectations": [
            "Series is 1-D labelled; DataFrame is 2-D with labelled columns.",
            "loc is label-based, iloc is position-based.",
            "dropna / fillna with a justification; chained indexing writes to a copy "
            "(SettingWithCopyWarning) - use .loc instead.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_sql_select_basics",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "SELECT, WHERE and ORDER BY",
        "prompt": (
            "Write, in words or SQL, how you would get the names and salaries of employees in "
            "the 'Sales' department, highest paid first, showing only the top 5. Explain what "
            "each clause in your query does, and what `SELECT *` returns."
        ),
        "expectations": [
            "SELECT name, salary FROM employees WHERE department = 'Sales' "
            "ORDER BY salary DESC LIMIT 5 (or TOP 5).",
            "Explains WHERE filters rows, ORDER BY sorts, DESC is descending, LIMIT caps.",
            "SELECT * returns every column - and knows why naming columns is better.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_sql_keys_null",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Primary keys, foreign keys and NULL",
        "prompt": (
            "What is a primary key and what is a foreign key? Can a primary key be NULL? "
            "What does NULL actually mean in SQL, and why does `WHERE salary = NULL` return "
            "nothing even when there are rows with no salary?"
        ),
        "expectations": [
            "Primary key uniquely identifies a row; it cannot be NULL or duplicated.",
            "Foreign key points at another table's primary key and enforces the link.",
            "NULL means unknown, so comparisons are never true - use IS NULL / IS NOT NULL.",
        ],
        "suggested_minutes": 3,
    },
]

SQL_CODING: list[dict[str, Any]] = [
    {
        "id": "c_join_dicts",
        "type": "coding",
        "weight": 15,
        "title": "Join two datasets in Python",
        "prompt": (
            "You have two lists of dicts:\n"
            "    users  = [{'id': 1, 'name': 'A'}, ...]\n"
            "    orders = [{'user_id': 1, 'amount': 250}, ...]\n\n"
            "Write `user_totals(users, orders)` returning a list of\n"
            "{'name': str, 'orders': int, 'total': int} for EVERY user - including users "
            "with no orders (0 and 0) - sorted by total descending, then name ascending.\n\n"
            "This is a LEFT JOIN written in Python. Explain why you should not loop over "
            "orders inside a loop over users."
        ),
        "starter_code": (
            "users = [{'id': 1, 'name': 'Asha'}, {'id': 2, 'name': 'Bo'}, {'id': 3, 'name': 'Cy'}]\n"
            "orders = [{'user_id': 1, 'amount': 250}, {'user_id': 1, 'amount': 100},\n"
            "          {'user_id': 3, 'amount': 700}]\n\n\n"
            "def user_totals(users, orders):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(user_totals(users, orders))\n"
        ),
        "expectations": [
            "Builds a dict index of orders by user_id - O(n + m), not O(n * m).",
            "Users with no orders still appear, with zeros.",
            "Correct two-key sorting (total desc, then name asc).",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_clean_rows",
        "type": "coding",
        "weight": 15,
        "title": "Clean a messy dataset",
        "prompt": (
            "Rows arrive as dicts with dirty values:\n"
            "    {'name': '  asha  ', 'email': 'A@X.COM', 'amount': '1,250', 'city': ''}\n\n"
            "Write `clean(rows)` that strips and title-cases `name`, lower-cases `email`, "
            "converts `amount` to an int (commas removed; blank or unparseable becomes 0), "
            "and replaces any remaining empty string with None. Rows with no email are "
            "dropped entirely.\n\n"
            "Explain how you decided what to drop versus what to default."
        ),
        "starter_code": (
            "rows = [\n"
            "    {'name': '  asha  ', 'email': 'A@X.COM', 'amount': '1,250', 'city': ''},\n"
            "    {'name': 'bo', 'email': '', 'amount': '90', 'city': 'Pune'},\n"
            "    {'name': 'cy', 'email': 'cy@x.com', 'amount': 'n/a', 'city': 'Goa'},\n"
            "]\n\n\n"
            "def clean(rows):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "for row in clean(rows):\n"
            "    print(row)\n"
        ),
        "expectations": [
            "Per-field normalisation with a safe int conversion (try/except).",
            "Empty strings become None; the row without an email is dropped.",
            "Does not mutate the caller's rows, or explains why that is acceptable here.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_running_total",
        "type": "coding",
        "weight": 15,
        "title": "Running total per group",
        "prompt": (
            "Given transactions already sorted by date:\n"
            "    [{'account': 'A', 'date': '2026-01-01', 'amount': 100}, ...]\n\n"
            "Write `running_balance(txns)` that adds a 'balance' key to each transaction: the "
            "running total for THAT account up to and including that row. Return the list in "
            "its original order.\n\n"
            "This is a SQL window function written in Python - say which one."
        ),
        "starter_code": (
            "txns = [\n"
            "    {'account': 'A', 'date': '2026-01-01', 'amount': 100},\n"
            "    {'account': 'B', 'date': '2026-01-01', 'amount': 50},\n"
            "    {'account': 'A', 'date': '2026-01-02', 'amount': -30},\n"
            "    {'account': 'A', 'date': '2026-01-03', 'amount': 10},\n"
            "]\n\n\n"
            "def running_balance(txns):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "for row in running_balance(txns):\n"
            "    print(row)\n"
        ),
        "expectations": [
            "A dict of per-account accumulators in a single pass.",
            "Original order preserved.",
            "Recognises SUM(amount) OVER (PARTITION BY account ORDER BY date).",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_filter_rows",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Filter rows (a WHERE clause in Python)",
        "prompt": (
            "You have a list of employee dicts. Write `high_earners(rows, minimum)` that "
            "returns the NAMES of everyone earning at least `minimum`, in the order they "
            "appear.\n\n"
            "Example:\n"
            "    high_earners(rows, 50000) -> ['Asha', 'Ravi']\n\n"
            "Then say which SQL query does the same thing."
        ),
        "starter_code": (
            "rows = [\n"
            "    {'name': 'Asha', 'salary': 62000},\n"
            "    {'name': 'Ravi', 'salary': 50000},\n"
            "    {'name': 'Meena', 'salary': 41000},\n"
            "]\n\n\n"
            "def high_earners(rows, minimum):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(high_earners(rows, 50000))  # ['Asha', 'Ravi']\n"
        ),
        "expectations": [
            "Loops the rows and compares row['salary'] >= minimum (>= not >).",
            "Collects only the name, keeping the original order.",
            "Maps it to SELECT name FROM employees WHERE salary >= 50000.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_count_by_key",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Count per group (a GROUP BY in Python)",
        "prompt": (
            "Write `count_by_city(rows)` that returns a dict mapping each city to how many "
            "people live there.\n\n"
            "Example:\n"
            "    count_by_city(rows) -> {'Pune': 2, 'Delhi': 1}\n\n"
            "Then say which SQL query does the same thing."
        ),
        "starter_code": (
            "rows = [\n"
            "    {'name': 'Asha', 'city': 'Pune'},\n"
            "    {'name': 'Ravi', 'city': 'Delhi'},\n"
            "    {'name': 'Meena', 'city': 'Pune'},\n"
            "]\n\n\n"
            "def count_by_city(rows):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(count_by_city(rows))  # {'Pune': 2, 'Delhi': 1}\n"
        ),
        "expectations": [
            "Builds a dict, starting a city at 0/1 the first time it is seen.",
            "Uses dict.get, defaultdict or Counter - any is fine if explained.",
            "Maps it to SELECT city, COUNT(*) FROM people GROUP BY city.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_highest_paid",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Find the maximum row",
        "prompt": (
            "Write `highest_paid(rows)` that returns the name of the person with the biggest "
            "salary. If `rows` is empty, return None.\n\n"
            "Example:\n"
            "    highest_paid(rows) -> 'Asha'\n\n"
            "Explain what your code does if two people earn exactly the same."
        ),
        "starter_code": (
            "rows = [\n"
            "    {'name': 'Asha', 'salary': 62000},\n"
            "    {'name': 'Ravi', 'salary': 50000},\n"
            "    {'name': 'Meena', 'salary': 41000},\n"
            "]\n\n\n"
            "def highest_paid(rows):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(highest_paid(rows))  # Asha\n"
            "print(highest_paid([]))    # None\n"
        ),
        "expectations": [
            "Tracks the best row in a loop, or uses max(rows, key=...).",
            "Returns None for an empty list instead of raising ValueError.",
            "Says which of two tied rows wins (the first one seen).",
        ],
        "suggested_minutes": 4,
    },
]

AUTOMATION_THEORY: list[dict[str, Any]] = [
    {
        "id": "t_test_types",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Unit vs integration tests",
        "prompt": (
            "What is the difference between a unit test and an integration test? What is a "
            "mock and when should you use one? What makes a test 'flaky', and why is a flaky "
            "test worse than no test at all?"
        ),
        "expectations": [
            "Unit tests one piece in isolation; integration tests components together.",
            "Mocks replace slow or external dependencies; over-mocking tests the mock.",
            "Flaky = non-deterministic (timing, ordering, shared state); it erodes trust.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_pytest",
        "type": "theory",
        "weight": 15,
        "title": "pytest basics",
        "prompt": (
            "How does pytest discover tests? What is a fixture, and what does its `scope` "
            "control? What does `@pytest.mark.parametrize` do, and why is it better than a "
            "for-loop of asserts inside one test?"
        ),
        "expectations": [
            "test_*.py files, test_* functions, Test* classes.",
            "Fixtures provide setup/teardown; scope = function/class/module/session.",
            "parametrize reports one test per case, so a failure names the failing case.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_http_status",
        "type": "theory",
        "weight": 15,
        "title": "REST APIs and status codes",
        "prompt": (
            "Explain the difference between GET, POST, PUT and DELETE, and which of them are "
            "idempotent. What do 200, 201, 400, 401, 403, 404 and 500 mean? If an API call "
            "fails intermittently, how do you make your automation resilient?"
        ),
        "expectations": [
            "GET/PUT/DELETE are idempotent; POST is not.",
            "401 is 'who are you', 403 is 'I know you and no'; 4xx client, 5xx server.",
            "Retry with backoff on 5xx/timeouts only, with a cap - never blindly on 4xx.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_logging",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "Logging and debugging",
        "prompt": (
            "Why is `logging` better than `print` in an automation script? Explain the log "
            "levels and when you would use each. How would you debug a script that fails "
            "only on the production server?"
        ),
        "expectations": [
            "Levels, handlers, formatting, routing to file/stdout; silence without code edits.",
            "DEBUG/INFO/WARNING/ERROR/CRITICAL with sensible examples.",
            "Reproduce with prod-like data, raise the log level, check env/permissions/versions.",
        ],
        "suggested_minutes": 3,
    },
    {
        "id": "t_manual_vs_automation",
        "type": "theory",
        "difficulty": "easy",
        "weight": 15,
        "title": "What to automate, and what a good test looks like",
        "prompt": (
            "What is the difference between manual and automated testing, and which kinds of "
            "test are worth automating first? What are the parts of a good test case, and what "
            "do 'positive' and 'negative' test cases mean? Give one example of each for a "
            "login page."
        ),
        "expectations": [
            "Automate repetitive, stable, frequently-run checks (regression, smoke) first.",
            "A test case has a clear input, the steps, and one expected result.",
            "Positive = correct password logs in; negative = wrong password is rejected.",
        ],
        "suggested_minutes": 3,
    },
]

AUTOMATION_CODING: list[dict[str, Any]] = [
    {
        "id": "c_parse_logs",
        "type": "coding",
        "weight": 15,
        "title": "Parse a log file",
        "prompt": (
            "Log lines look like:\n"
            "    2026-01-04 10:12:01 ERROR payment timeout for order 8891\n\n"
            "Write `error_summary(lines)` that returns a dict mapping each log level to the "
            "number of lines at that level, ignoring blank and malformed lines. A valid line "
            "has at least a date, a time, a level and a message, and the level must be one "
            "of DEBUG/INFO/WARNING/ERROR/CRITICAL.\n\n"
            "Explain how you would handle a 5 GB log file."
        ),
        "starter_code": (
            "lines = [\n"
            "    '2026-01-04 10:12:01 ERROR payment timeout for order 8891',\n"
            "    '2026-01-04 10:12:02 INFO retrying order 8891',\n"
            "    'garbage line',\n"
            "    '',\n"
            "    '2026-01-04 10:12:09 ERROR payment failed for order 8891',\n"
            "]\n\n\n"
            "def error_summary(lines):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(error_summary(lines))  # {'ERROR': 2, 'INFO': 1}\n"
        ),
        "expectations": [
            "Splits with maxsplit or a regex and validates the level against a known set.",
            "Malformed and blank lines are skipped, not counted and not crashed on.",
            "For 5 GB: iterate the file object line by line, never readlines().",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_retry",
        "type": "coding",
        "weight": 15,
        "title": "Retry with backoff",
        "prompt": (
            "Write `retry(func, attempts=3, delay=0.1)` that calls `func()` and, if it "
            "raises, retries up to `attempts` times in total, doubling the delay each time. "
            "If every attempt fails, re-raise the LAST exception. Return the value on "
            "success.\n\n"
            "Explain which kinds of exceptions should NOT be retried."
        ),
        "starter_code": (
            "import time\n\n\n"
            "def retry(func, attempts=3, delay=0.1):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "calls = {'n': 0}\n\n\n"
            "def flaky():\n"
            "    calls['n'] += 1\n"
            "    if calls['n'] < 3:\n"
            "        raise ConnectionError('boom')\n"
            "    return 'ok'\n\n\n"
            "print(retry(flaky), 'after', calls['n'], 'calls')  # ok after 3 calls\n"
        ),
        "expectations": [
            "Loop with try/except, doubling the delay, re-raising the last exception.",
            "Does not retry for ever and does not swallow the error.",
            "Knows that 4xx / ValueError / auth failures should not be retried.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_validate_payload",
        "type": "coding",
        "weight": 15,
        "title": "Validate an API payload",
        "prompt": (
            "Write `validate(payload)` that checks an API response dict and returns a list "
            "of error strings (an empty list means valid). Rules: 'id' must be present and "
            "an int; 'email' must be present and contain '@'; 'age', if present, must be an "
            "int between 18 and 99; any key other than id/email/age is an error.\n\n"
            "Explain why you return all the errors instead of raising on the first one."
        ),
        "starter_code": (
            "def validate(payload):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(validate({'id': 1, 'email': 'a@b.com'}))               # []\n"
            "print(validate({'id': 'x', 'email': 'nope', 'age': 5}))      # 3 errors\n"
            "print(validate({'id': 1, 'email': 'a@b.com', 'extra': 1}))   # 1 error\n"
        ),
        "expectations": [
            "Collects every error instead of returning on the first failure.",
            "isinstance checks, handling the bool-is-an-int trap safely.",
            "Optional field handled correctly; unexpected keys detected.",
        ],
        "suggested_minutes": 5,
    },
    {
        "id": "c_write_asserts",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Write tests with assert",
        "prompt": (
            "Below is a function `discount(price, percent)`. Write at least THREE `assert` "
            "statements that test it: one normal case, one edge case (0%), and one that shows "
            "the behaviour you think is wrong or risky.\n\n"
            "Run it - if an assert fails, say out loud whether the test or the function is "
            "wrong."
        ),
        "starter_code": (
            "def discount(price, percent):\n"
            "    return price - (price * percent / 100)\n\n\n"
            "# Write your asserts below.\n"
            "assert discount(100, 10) == 90\n"
            "# your code here\n\n\n"
            "print('all tests passed')\n"
        ),
        "expectations": [
            "Three or more asserts covering a normal case and an edge case such as 0 or 100%.",
            "Spots a real risk: a percent above 100 or below 0 is not rejected.",
            "Explains that a failing assert means one of the two is wrong, and says which.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_count_results",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Summarise a test run",
        "prompt": (
            "Write `summarise(results)` that takes a list of 'PASS'/'FAIL'/'SKIP' strings and "
            "returns a dict with the count of each, always including all three keys even when "
            "one did not occur.\n\n"
            "Example:\n"
            "    summarise(['PASS', 'FAIL', 'PASS']) -> {'PASS': 2, 'FAIL': 1, 'SKIP': 0}\n\n"
            "Explain why you include a key whose count is zero."
        ),
        "starter_code": (
            "def summarise(results):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(summarise(['PASS', 'FAIL', 'PASS']))  # {'PASS': 2, 'FAIL': 1, 'SKIP': 0}\n"
            "print(summarise([]))                        # all zero\n"
        ),
        "expectations": [
            "Starts every key at 0 so absent outcomes still appear.",
            "Counts in a single loop; empty input gives all zeros, not an empty dict.",
            "Explains that a missing key breaks a report or a KeyError downstream.",
        ],
        "suggested_minutes": 4,
    },
    {
        "id": "c_clean_strings",
        "type": "coding",
        "difficulty": "easy",
        "weight": 15,
        "title": "Tidy up a list of strings",
        "prompt": (
            "Test data arrives messy. Write `clean(names)` that strips the spaces from each "
            "name, drops anything that is empty after stripping, and returns the rest in "
            "lower case.\n\n"
            "Example:\n"
            "    clean(['  Asha ', '', 'RAVI', '   ']) -> ['asha', 'ravi']\n\n"
            "Say why you strip before you check for empty."
        ),
        "starter_code": (
            "def clean(names):\n"
            "    # your code here\n"
            "    pass\n\n\n"
            "print(clean(['  Asha ', '', 'RAVI', '   ']))  # ['asha', 'ravi']\n"
        ),
        "expectations": [
            "Uses .strip() and .lower() on each item.",
            "Drops entries that are empty AFTER stripping - '   ' must go too.",
            "Builds a new list rather than mutating while iterating.",
        ],
        "suggested_minutes": 4,
    },
]

THEORY_BANKS: dict[str, list[dict[str, Any]]] = {
    "python_core": PYTHON_THEORY,
    "sql_data": SQL_THEORY,
    "automation": AUTOMATION_THEORY,
}

CODING_BANKS: dict[str, list[dict[str, Any]]] = {
    "python_core": PYTHON_CODING,
    "sql_data": SQL_CODING,
    "automation": AUTOMATION_CODING,
}
