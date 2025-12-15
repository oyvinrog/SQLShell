"""
DuckDB Documentation Lookup Module

This module provides a comprehensive searchable index of DuckDB SQL documentation,
including functions, syntax, and concepts. It enables dynamic lookup as users type
in the SQL editor.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DocEntry:
    """Represents a documentation entry."""
    name: str
    category: str
    syntax: str
    description: str
    examples: List[str]
    related: List[str]
    url: str


# Comprehensive DuckDB documentation database
DUCKDB_DOCS: Dict[str, DocEntry] = {}


def _build_docs_database():
    """Build the documentation database with DuckDB functions and syntax."""
    global DUCKDB_DOCS
    
    docs = [
        # ===== REGULAR EXPRESSIONS =====
        DocEntry(
            name="regexp_matches",
            category="Regular Expressions",
            syntax="regexp_matches(string, pattern[, options])",
            description="Returns true if the string contains the regex pattern, false otherwise. "
                       "Use 'i' option for case-insensitive matching.",
            examples=[
                "SELECT regexp_matches('hello', 'ell');  -- true",
                "SELECT regexp_matches('Hello', 'hello', 'i');  -- true (case-insensitive)",
                "SELECT regexp_matches('abc123', '\\d+');  -- true"
            ],
            related=["regexp_extract", "regexp_replace", "regexp_split_to_array", "LIKE", "SIMILAR TO"],
            url="https://duckdb.org/docs/sql/functions/regular_expressions.html"
        ),
        DocEntry(
            name="regexp_extract",
            category="Regular Expressions",
            syntax="regexp_extract(string, pattern[, group = 0][, options])",
            description="If string contains the regex pattern, returns the capturing group specified. "
                       "Group 0 returns the entire match. Returns NULL if no match.",
            examples=[
                "SELECT regexp_extract('abc123def', '\\d+');  -- '123'",
                "SELECT regexp_extract('John Smith', '(\\w+) (\\w+)', 1);  -- 'John'",
                "SELECT regexp_extract('John Smith', '(\\w+) (\\w+)', 2);  -- 'Smith'"
            ],
            related=["regexp_matches", "regexp_replace", "regexp_extract_all"],
            url="https://duckdb.org/docs/sql/functions/regular_expressions.html"
        ),
        DocEntry(
            name="regexp_replace",
            category="Regular Expressions",
            syntax="regexp_replace(string, pattern, replacement[, options])",
            description="Replaces occurrences of the regex pattern with the replacement string. "
                       "Use 'g' option for global replacement (all occurrences).",
            examples=[
                "SELECT regexp_replace('hello world', 'world', 'DuckDB');  -- 'hello DuckDB'",
                "SELECT regexp_replace('a1b2c3', '\\d', 'X', 'g');  -- 'aXbXcX'",
                "SELECT regexp_replace('HELLO', 'hello', 'hi', 'i');  -- 'hi'"
            ],
            related=["regexp_matches", "regexp_extract", "replace"],
            url="https://duckdb.org/docs/sql/functions/regular_expressions.html"
        ),
        DocEntry(
            name="regexp_split_to_array",
            category="Regular Expressions",
            syntax="regexp_split_to_array(string, pattern[, options])",
            description="Splits the string by the regex pattern and returns an array of substrings.",
            examples=[
                "SELECT regexp_split_to_array('a,b;c', '[,;]');  -- ['a', 'b', 'c']",
                "SELECT regexp_split_to_array('one  two   three', '\\s+');  -- ['one', 'two', 'three']"
            ],
            related=["string_split", "regexp_extract_all"],
            url="https://duckdb.org/docs/sql/functions/regular_expressions.html"
        ),
        DocEntry(
            name="regexp_extract_all",
            category="Regular Expressions",
            syntax="regexp_extract_all(string, pattern[, group = 0][, options])",
            description="Returns a list of all matches of the regex pattern in the string.",
            examples=[
                "SELECT regexp_extract_all('abc123def456', '\\d+');  -- ['123', '456']",
                "SELECT regexp_extract_all('cat bat rat', '\\w+at');  -- ['cat', 'bat', 'rat']"
            ],
            related=["regexp_extract", "regexp_matches"],
            url="https://duckdb.org/docs/sql/functions/regular_expressions.html"
        ),
        
        # ===== STRING FUNCTIONS =====
        DocEntry(
            name="concat",
            category="String Functions",
            syntax="concat(string, ...)",
            description="Concatenates multiple strings together. NULL values are ignored.",
            examples=[
                "SELECT concat('Hello', ' ', 'World');  -- 'Hello World'",
                "SELECT concat('a', NULL, 'b');  -- 'ab'"
            ],
            related=["concat_ws", "||"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="concat_ws",
            category="String Functions",
            syntax="concat_ws(separator, string, ...)",
            description="Concatenates strings with a separator between them. NULL values are skipped.",
            examples=[
                "SELECT concat_ws(', ', 'apple', 'banana', 'cherry');  -- 'apple, banana, cherry'",
                "SELECT concat_ws('-', '2024', '01', '15');  -- '2024-01-15'"
            ],
            related=["concat", "string_agg"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="length",
            category="String Functions",
            syntax="length(string)",
            description="Returns the number of characters in the string.",
            examples=[
                "SELECT length('hello');  -- 5",
                "SELECT length('');  -- 0"
            ],
            related=["octet_length", "bit_length"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="lower",
            category="String Functions",
            syntax="lower(string)",
            description="Converts the string to lowercase.",
            examples=[
                "SELECT lower('HELLO');  -- 'hello'",
                "SELECT lower('HeLLo WoRLD');  -- 'hello world'"
            ],
            related=["upper", "initcap"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="upper",
            category="String Functions",
            syntax="upper(string)",
            description="Converts the string to uppercase.",
            examples=[
                "SELECT upper('hello');  -- 'HELLO'",
                "SELECT upper('Hello World');  -- 'HELLO WORLD'"
            ],
            related=["lower", "initcap"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="trim",
            category="String Functions",
            syntax="trim(string[, characters])",
            description="Removes leading and trailing whitespace (or specified characters) from string.",
            examples=[
                "SELECT trim('  hello  ');  -- 'hello'",
                "SELECT trim('xxhelloxx', 'x');  -- 'hello'"
            ],
            related=["ltrim", "rtrim"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="ltrim",
            category="String Functions",
            syntax="ltrim(string[, characters])",
            description="Removes leading whitespace (or specified characters) from string.",
            examples=[
                "SELECT ltrim('  hello');  -- 'hello'",
                "SELECT ltrim('xxxhello', 'x');  -- 'hello'"
            ],
            related=["trim", "rtrim"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="rtrim",
            category="String Functions",
            syntax="rtrim(string[, characters])",
            description="Removes trailing whitespace (or specified characters) from string.",
            examples=[
                "SELECT rtrim('hello  ');  -- 'hello'",
                "SELECT rtrim('helloxxx', 'x');  -- 'hello'"
            ],
            related=["trim", "ltrim"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="substring",
            category="String Functions",
            syntax="substring(string, start[, length]) | substring(string FROM start [FOR length])",
            description="Extracts a substring from the given string. Start position is 1-based.",
            examples=[
                "SELECT substring('hello', 2, 3);  -- 'ell'",
                "SELECT substring('hello' FROM 2 FOR 3);  -- 'ell'",
                "SELECT substring('hello', 2);  -- 'ello'"
            ],
            related=["left", "right", "substr"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="replace",
            category="String Functions",
            syntax="replace(string, source, target)",
            description="Replaces all occurrences of source with target in the string.",
            examples=[
                "SELECT replace('hello world', 'world', 'DuckDB');  -- 'hello DuckDB'",
                "SELECT replace('aaa', 'a', 'b');  -- 'bbb'"
            ],
            related=["regexp_replace", "translate"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="split_part",
            category="String Functions",
            syntax="split_part(string, delimiter, index)",
            description="Splits the string by delimiter and returns the part at the specified index (1-based).",
            examples=[
                "SELECT split_part('a,b,c', ',', 2);  -- 'b'",
                "SELECT split_part('2024-01-15', '-', 1);  -- '2024'"
            ],
            related=["string_split", "regexp_split_to_array"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="string_split",
            category="String Functions",
            syntax="string_split(string, delimiter)",
            description="Splits the string by delimiter and returns an array of parts.",
            examples=[
                "SELECT string_split('a,b,c', ',');  -- ['a', 'b', 'c']",
                "SELECT string_split('hello world', ' ');  -- ['hello', 'world']"
            ],
            related=["split_part", "regexp_split_to_array", "unnest"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="reverse",
            category="String Functions",
            syntax="reverse(string)",
            description="Reverses the characters in the string.",
            examples=[
                "SELECT reverse('hello');  -- 'olleh'",
                "SELECT reverse('DuckDB');  -- 'BDkcuD'"
            ],
            related=["left", "right"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="left",
            category="String Functions",
            syntax="left(string, count)",
            description="Returns the leftmost count characters from the string.",
            examples=[
                "SELECT left('hello', 3);  -- 'hel'",
                "SELECT left('DuckDB', 4);  -- 'Duck'"
            ],
            related=["right", "substring"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="right",
            category="String Functions",
            syntax="right(string, count)",
            description="Returns the rightmost count characters from the string.",
            examples=[
                "SELECT right('hello', 3);  -- 'llo'",
                "SELECT right('DuckDB', 2);  -- 'DB'"
            ],
            related=["left", "substring"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="repeat",
            category="String Functions",
            syntax="repeat(string, count)",
            description="Repeats the string count times.",
            examples=[
                "SELECT repeat('ab', 3);  -- 'ababab'",
                "SELECT repeat('-', 10);  -- '----------'"
            ],
            related=["lpad", "rpad"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="lpad",
            category="String Functions",
            syntax="lpad(string, length[, fill])",
            description="Pads the string on the left to the specified length with the fill character (default space).",
            examples=[
                "SELECT lpad('42', 5, '0');  -- '00042'",
                "SELECT lpad('hi', 5);  -- '   hi'"
            ],
            related=["rpad", "repeat"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="rpad",
            category="String Functions",
            syntax="rpad(string, length[, fill])",
            description="Pads the string on the right to the specified length with the fill character (default space).",
            examples=[
                "SELECT rpad('hi', 5, '!');  -- 'hi!!!'",
                "SELECT rpad('42', 5, '0');  -- '42000'"
            ],
            related=["lpad", "repeat"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="position",
            category="String Functions",
            syntax="position(search IN string) | strpos(string, search)",
            description="Returns the position of the first occurrence of search in string (1-based). Returns 0 if not found.",
            examples=[
                "SELECT position('ll' IN 'hello');  -- 3",
                "SELECT strpos('hello', 'o');  -- 5",
                "SELECT position('x' IN 'hello');  -- 0"
            ],
            related=["instr", "contains"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="contains",
            category="String Functions",
            syntax="contains(string, search)",
            description="Returns true if string contains the search substring.",
            examples=[
                "SELECT contains('hello', 'ell');  -- true",
                "SELECT contains('hello', 'xyz');  -- false"
            ],
            related=["position", "starts_with", "ends_with"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="starts_with",
            category="String Functions",
            syntax="starts_with(string, prefix) | prefix(string, prefix)",
            description="Returns true if string starts with the given prefix.",
            examples=[
                "SELECT starts_with('hello', 'hel');  -- true",
                "SELECT starts_with('hello', 'ell');  -- false"
            ],
            related=["ends_with", "contains"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        DocEntry(
            name="ends_with",
            category="String Functions",
            syntax="ends_with(string, suffix) | suffix(string, suffix)",
            description="Returns true if string ends with the given suffix.",
            examples=[
                "SELECT ends_with('hello', 'llo');  -- true",
                "SELECT ends_with('hello', 'hel');  -- false"
            ],
            related=["starts_with", "contains"],
            url="https://duckdb.org/docs/sql/functions/text.html"
        ),
        
        # ===== AGGREGATE FUNCTIONS =====
        DocEntry(
            name="count",
            category="Aggregate Functions",
            syntax="count(*) | count(expression) | count(DISTINCT expression)",
            description="Returns the number of rows. count(*) counts all rows, count(expr) counts non-NULL values, "
                       "count(DISTINCT expr) counts unique non-NULL values.",
            examples=[
                "SELECT count(*) FROM table;",
                "SELECT count(column) FROM table;",
                "SELECT count(DISTINCT category) FROM products;"
            ],
            related=["sum", "avg", "min", "max"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="sum",
            category="Aggregate Functions",
            syntax="sum(expression)",
            description="Returns the sum of all non-NULL values in the expression.",
            examples=[
                "SELECT sum(amount) FROM sales;",
                "SELECT department, sum(salary) FROM employees GROUP BY department;"
            ],
            related=["avg", "count", "total"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="avg",
            category="Aggregate Functions",
            syntax="avg(expression)",
            description="Returns the average (arithmetic mean) of all non-NULL values.",
            examples=[
                "SELECT avg(price) FROM products;",
                "SELECT category, avg(rating) FROM reviews GROUP BY category;"
            ],
            related=["sum", "count", "median"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="min",
            category="Aggregate Functions",
            syntax="min(expression)",
            description="Returns the minimum value among all non-NULL values.",
            examples=[
                "SELECT min(price) FROM products;",
                "SELECT min(created_at) FROM orders;"
            ],
            related=["max", "arg_min"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="max",
            category="Aggregate Functions",
            syntax="max(expression)",
            description="Returns the maximum value among all non-NULL values.",
            examples=[
                "SELECT max(price) FROM products;",
                "SELECT max(updated_at) FROM records;"
            ],
            related=["min", "arg_max"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="string_agg",
            category="Aggregate Functions",
            syntax="string_agg(expression, separator [ORDER BY ...])",
            description="Concatenates non-NULL values into a string, separated by the given separator.",
            examples=[
                "SELECT string_agg(name, ', ') FROM employees;",
                "SELECT department, string_agg(name, ', ' ORDER BY name) FROM employees GROUP BY department;"
            ],
            related=["array_agg", "list_agg", "group_concat"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="array_agg",
            category="Aggregate Functions",
            syntax="array_agg(expression) | list(expression)",
            description="Collects all non-NULL values into an array/list.",
            examples=[
                "SELECT array_agg(name) FROM employees;",
                "SELECT department, list(salary) FROM employees GROUP BY department;"
            ],
            related=["string_agg", "list_agg"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="median",
            category="Aggregate Functions",
            syntax="median(expression)",
            description="Returns the median (middle value) of all non-NULL values.",
            examples=[
                "SELECT median(salary) FROM employees;",
                "SELECT department, median(age) FROM employees GROUP BY department;"
            ],
            related=["avg", "percentile_cont", "quantile"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="mode",
            category="Aggregate Functions",
            syntax="mode(expression)",
            description="Returns the most frequent value (mode) among all values.",
            examples=[
                "SELECT mode(category) FROM products;",
                "SELECT mode(rating) FROM reviews;"
            ],
            related=["median", "count"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="stddev",
            category="Aggregate Functions",
            syntax="stddev(expression) | stddev_samp(expression)",
            description="Returns the sample standard deviation of all non-NULL values.",
            examples=[
                "SELECT stddev(price) FROM products;",
                "SELECT category, stddev(rating) FROM reviews GROUP BY category;"
            ],
            related=["variance", "stddev_pop"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="variance",
            category="Aggregate Functions",
            syntax="variance(expression) | var_samp(expression)",
            description="Returns the sample variance of all non-NULL values.",
            examples=[
                "SELECT variance(price) FROM products;",
                "SELECT variance(score) FROM tests;"
            ],
            related=["stddev", "var_pop"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="arg_min",
            category="Aggregate Functions",
            syntax="arg_min(arg, val) | min_by(arg, val)",
            description="Returns the value of arg for the row with the minimum val.",
            examples=[
                "SELECT arg_min(name, price) FROM products;  -- name of cheapest product",
                "SELECT min_by(employee_id, salary) FROM employees;"
            ],
            related=["arg_max", "min"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="arg_max",
            category="Aggregate Functions",
            syntax="arg_max(arg, val) | max_by(arg, val)",
            description="Returns the value of arg for the row with the maximum val.",
            examples=[
                "SELECT arg_max(name, price) FROM products;  -- name of most expensive product",
                "SELECT max_by(employee_id, salary) FROM employees;"
            ],
            related=["arg_min", "max"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="first",
            category="Aggregate Functions",
            syntax="first(expression)",
            description="Returns the first non-NULL value in the group. Order is not guaranteed unless ORDER BY is used.",
            examples=[
                "SELECT first(name ORDER BY created_at) FROM employees;",
                "SELECT department, first(name) FROM employees GROUP BY department;"
            ],
            related=["last", "any_value"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        DocEntry(
            name="last",
            category="Aggregate Functions",
            syntax="last(expression)",
            description="Returns the last non-NULL value in the group.",
            examples=[
                "SELECT last(name ORDER BY created_at) FROM employees;",
                "SELECT department, last(status) FROM orders GROUP BY department;"
            ],
            related=["first", "any_value"],
            url="https://duckdb.org/docs/sql/functions/aggregates.html"
        ),
        
        # ===== WINDOW FUNCTIONS =====
        DocEntry(
            name="row_number",
            category="Window Functions",
            syntax="row_number() OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Assigns a unique sequential integer to rows within a partition, starting at 1.",
            examples=[
                "SELECT name, row_number() OVER (ORDER BY salary DESC) as rank FROM employees;",
                "SELECT *, row_number() OVER (PARTITION BY department ORDER BY hire_date) FROM employees;"
            ],
            related=["rank", "dense_rank", "ntile"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="rank",
            category="Window Functions",
            syntax="rank() OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the rank of each row within partition, with gaps for ties (e.g., 1, 2, 2, 4).",
            examples=[
                "SELECT name, salary, rank() OVER (ORDER BY salary DESC) FROM employees;",
                "SELECT *, rank() OVER (PARTITION BY department ORDER BY score DESC) FROM scores;"
            ],
            related=["row_number", "dense_rank", "percent_rank"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="dense_rank",
            category="Window Functions",
            syntax="dense_rank() OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the rank without gaps (e.g., 1, 2, 2, 3).",
            examples=[
                "SELECT name, salary, dense_rank() OVER (ORDER BY salary DESC) FROM employees;",
                "SELECT *, dense_rank() OVER (PARTITION BY category ORDER BY rating DESC) FROM products;"
            ],
            related=["row_number", "rank"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="lead",
            category="Window Functions",
            syntax="lead(expression[, offset[, default]]) OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the value of expression from the row that is offset rows after the current row. "
                       "Default offset is 1.",
            examples=[
                "SELECT date, sales, lead(sales) OVER (ORDER BY date) as next_day_sales FROM daily_sales;",
                "SELECT *, lead(price, 1, 0) OVER (ORDER BY date) FROM prices;"
            ],
            related=["lag", "first_value", "last_value"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="lag",
            category="Window Functions",
            syntax="lag(expression[, offset[, default]]) OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the value of expression from the row that is offset rows before the current row. "
                       "Default offset is 1.",
            examples=[
                "SELECT date, sales, lag(sales) OVER (ORDER BY date) as prev_day_sales FROM daily_sales;",
                "SELECT *, sales - lag(sales, 1, 0) OVER (ORDER BY date) as daily_change FROM sales;"
            ],
            related=["lead", "first_value", "last_value"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="first_value",
            category="Window Functions",
            syntax="first_value(expression) OVER ([PARTITION BY ...] ORDER BY ... [ROWS/RANGE ...])",
            description="Returns the first value in the window frame.",
            examples=[
                "SELECT *, first_value(salary) OVER (PARTITION BY dept ORDER BY hire_date) as first_salary FROM emp;",
                "SELECT date, price, first_value(price) OVER (ORDER BY date) as initial_price FROM stocks;"
            ],
            related=["last_value", "nth_value", "lead", "lag"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="last_value",
            category="Window Functions",
            syntax="last_value(expression) OVER ([PARTITION BY ...] ORDER BY ... [ROWS/RANGE ...])",
            description="Returns the last value in the window frame. Note: default frame may not include all rows.",
            examples=[
                "SELECT *, last_value(price) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) FROM prices;",
                "SELECT *, last_value(status) OVER (PARTITION BY order_id ORDER BY updated_at) FROM order_history;"
            ],
            related=["first_value", "nth_value"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="ntile",
            category="Window Functions",
            syntax="ntile(n) OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Divides rows into n roughly equal groups and returns the group number (1 to n).",
            examples=[
                "SELECT *, ntile(4) OVER (ORDER BY score) as quartile FROM students;",
                "SELECT *, ntile(10) OVER (ORDER BY revenue DESC) as decile FROM customers;"
            ],
            related=["row_number", "percent_rank"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="percent_rank",
            category="Window Functions",
            syntax="percent_rank() OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the relative rank as a percentage (0 to 1).",
            examples=[
                "SELECT name, score, percent_rank() OVER (ORDER BY score) as pct FROM students;",
                "SELECT *, percent_rank() OVER (PARTITION BY category ORDER BY sales DESC) FROM products;"
            ],
            related=["rank", "cume_dist", "ntile"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        DocEntry(
            name="cume_dist",
            category="Window Functions",
            syntax="cume_dist() OVER ([PARTITION BY ...] ORDER BY ...)",
            description="Returns the cumulative distribution (fraction of rows with values <= current row's value).",
            examples=[
                "SELECT name, score, cume_dist() OVER (ORDER BY score) as cumulative FROM students;",
                "SELECT *, cume_dist() OVER (PARTITION BY region ORDER BY sales) FROM sales;"
            ],
            related=["percent_rank", "ntile"],
            url="https://duckdb.org/docs/sql/functions/window_functions.html"
        ),
        
        # ===== DATE/TIME FUNCTIONS =====
        DocEntry(
            name="current_date",
            category="Date/Time Functions",
            syntax="current_date | today()",
            description="Returns the current date.",
            examples=[
                "SELECT current_date;",
                "SELECT * FROM orders WHERE order_date = current_date;"
            ],
            related=["current_timestamp", "now"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="current_timestamp",
            category="Date/Time Functions",
            syntax="current_timestamp | now()",
            description="Returns the current date and time (timestamp).",
            examples=[
                "SELECT current_timestamp;",
                "SELECT now();",
                "INSERT INTO logs (created_at) VALUES (current_timestamp);"
            ],
            related=["current_date", "current_time"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="date_trunc",
            category="Date/Time Functions",
            syntax="date_trunc(part, date/timestamp)",
            description="Truncates a date/timestamp to the specified precision. "
                       "Parts: microsecond, millisecond, second, minute, hour, day, week, month, quarter, year.",
            examples=[
                "SELECT date_trunc('month', DATE '2024-03-15');  -- 2024-03-01",
                "SELECT date_trunc('hour', TIMESTAMP '2024-03-15 14:30:45');  -- 2024-03-15 14:00:00"
            ],
            related=["date_part", "extract"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="date_part",
            category="Date/Time Functions",
            syntax="date_part(part, date/timestamp) | extract(part FROM date/timestamp)",
            description="Extracts the specified part from a date/timestamp. "
                       "Parts: year, month, day, hour, minute, second, dayofweek, dayofyear, week, quarter.",
            examples=[
                "SELECT date_part('year', DATE '2024-03-15');  -- 2024",
                "SELECT extract(month FROM current_date);",
                "SELECT date_part('dow', DATE '2024-03-15');  -- day of week"
            ],
            related=["date_trunc", "year", "month", "day"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="date_diff",
            category="Date/Time Functions",
            syntax="date_diff(part, start_date, end_date) | datediff(part, start, end)",
            description="Returns the number of part boundaries between two dates. "
                       "Parts: year, month, day, hour, minute, second, etc.",
            examples=[
                "SELECT date_diff('day', DATE '2024-01-01', DATE '2024-03-15');  -- 74",
                "SELECT date_diff('month', DATE '2024-01-15', DATE '2024-05-20');  -- 4"
            ],
            related=["date_add", "date_sub", "age"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="date_add",
            category="Date/Time Functions",
            syntax="date_add(date, INTERVAL value part) | date + INTERVAL",
            description="Adds an interval to a date/timestamp.",
            examples=[
                "SELECT date_add(DATE '2024-01-01', INTERVAL 30 DAY);",
                "SELECT DATE '2024-01-01' + INTERVAL '1 month';",
                "SELECT current_date + INTERVAL '1 week';"
            ],
            related=["date_sub", "date_diff"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="strftime",
            category="Date/Time Functions",
            syntax="strftime(format, date/timestamp)",
            description="Formats a date/timestamp as a string. Common: %Y=year, %m=month, %d=day, %H=hour, %M=min, %S=sec.",
            examples=[
                "SELECT strftime('%Y-%m-%d', current_date);  -- '2024-03-15'",
                "SELECT strftime('%B %d, %Y', DATE '2024-03-15');  -- 'March 15, 2024'",
                "SELECT strftime('%H:%M:%S', current_timestamp);"
            ],
            related=["strptime", "format"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="strptime",
            category="Date/Time Functions",
            syntax="strptime(string, format)",
            description="Parses a string into a timestamp using the specified format.",
            examples=[
                "SELECT strptime('2024-03-15', '%Y-%m-%d');",
                "SELECT strptime('March 15, 2024', '%B %d, %Y');",
                "SELECT strptime('15/03/2024 14:30', '%d/%m/%Y %H:%M');"
            ],
            related=["strftime", "cast"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="age",
            category="Date/Time Functions",
            syntax="age(timestamp1, timestamp2) | age(timestamp)",
            description="Returns the interval between two timestamps. Single argument returns interval from current_date.",
            examples=[
                "SELECT age(DATE '2024-01-01', DATE '2020-06-15');",
                "SELECT age(birth_date) FROM employees;  -- age from today"
            ],
            related=["date_diff", "date_sub"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="epoch",
            category="Date/Time Functions",
            syntax="epoch(timestamp) | epoch_ms(timestamp)",
            description="Converts timestamp to Unix epoch (seconds since 1970-01-01). epoch_ms returns milliseconds.",
            examples=[
                "SELECT epoch(TIMESTAMP '2024-01-01 00:00:00');",
                "SELECT epoch_ms(current_timestamp);"
            ],
            related=["to_timestamp", "make_timestamp"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        DocEntry(
            name="make_date",
            category="Date/Time Functions",
            syntax="make_date(year, month, day)",
            description="Creates a date from year, month, and day components.",
            examples=[
                "SELECT make_date(2024, 3, 15);  -- DATE '2024-03-15'",
                "SELECT make_date(year_col, month_col, 1) FROM sales;"
            ],
            related=["make_timestamp", "make_time"],
            url="https://duckdb.org/docs/sql/functions/date.html"
        ),
        
        # ===== NUMERIC FUNCTIONS =====
        DocEntry(
            name="round",
            category="Numeric Functions",
            syntax="round(value[, decimal_places])",
            description="Rounds a number to the specified decimal places (default 0).",
            examples=[
                "SELECT round(3.14159, 2);  -- 3.14",
                "SELECT round(1234.5);  -- 1235",
                "SELECT round(1234.5, -2);  -- 1200"
            ],
            related=["floor", "ceil", "trunc"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="floor",
            category="Numeric Functions",
            syntax="floor(value)",
            description="Rounds down to the nearest integer.",
            examples=[
                "SELECT floor(3.7);  -- 3",
                "SELECT floor(-3.2);  -- -4"
            ],
            related=["ceil", "round", "trunc"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="ceil",
            category="Numeric Functions",
            syntax="ceil(value) | ceiling(value)",
            description="Rounds up to the nearest integer.",
            examples=[
                "SELECT ceil(3.2);  -- 4",
                "SELECT ceil(-3.7);  -- -3"
            ],
            related=["floor", "round"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="abs",
            category="Numeric Functions",
            syntax="abs(value)",
            description="Returns the absolute (non-negative) value.",
            examples=[
                "SELECT abs(-42);  -- 42",
                "SELECT abs(price_change) FROM stocks;"
            ],
            related=["sign"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="power",
            category="Numeric Functions",
            syntax="power(base, exponent) | pow(base, exponent)",
            description="Returns base raised to the power of exponent.",
            examples=[
                "SELECT power(2, 10);  -- 1024",
                "SELECT pow(10, 3);  -- 1000"
            ],
            related=["sqrt", "exp", "ln"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="sqrt",
            category="Numeric Functions",
            syntax="sqrt(value)",
            description="Returns the square root of the value.",
            examples=[
                "SELECT sqrt(16);  -- 4",
                "SELECT sqrt(2);  -- 1.414..."
            ],
            related=["power", "cbrt"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="log",
            category="Numeric Functions",
            syntax="log(value) | log10(value) | log2(value) | ln(value)",
            description="log/log10: base-10 logarithm. log2: base-2. ln: natural logarithm (base e).",
            examples=[
                "SELECT log(100);  -- 2 (log base 10)",
                "SELECT ln(2.718);  -- ~1 (natural log)",
                "SELECT log2(8);  -- 3"
            ],
            related=["exp", "power"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="mod",
            category="Numeric Functions",
            syntax="mod(a, b) | a % b",
            description="Returns the remainder of a divided by b.",
            examples=[
                "SELECT mod(10, 3);  -- 1",
                "SELECT 17 % 5;  -- 2"
            ],
            related=["div", "floor"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="greatest",
            category="Numeric Functions",
            syntax="greatest(value1, value2, ...)",
            description="Returns the largest value among the arguments.",
            examples=[
                "SELECT greatest(1, 5, 3);  -- 5",
                "SELECT greatest(a, b, c) FROM table;"
            ],
            related=["least", "max"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="least",
            category="Numeric Functions",
            syntax="least(value1, value2, ...)",
            description="Returns the smallest value among the arguments.",
            examples=[
                "SELECT least(1, 5, 3);  -- 1",
                "SELECT least(a, b, c) FROM table;"
            ],
            related=["greatest", "min"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        DocEntry(
            name="random",
            category="Numeric Functions",
            syntax="random()",
            description="Returns a random number between 0 and 1.",
            examples=[
                "SELECT random();  -- e.g., 0.7234...",
                "SELECT * FROM table ORDER BY random() LIMIT 10;  -- random sample"
            ],
            related=["setseed"],
            url="https://duckdb.org/docs/sql/functions/numeric.html"
        ),
        
        # ===== CONDITIONAL FUNCTIONS =====
        DocEntry(
            name="case",
            category="Conditional Functions",
            syntax="CASE WHEN condition THEN result [WHEN ... THEN ...] [ELSE default] END",
            description="Conditional expression that returns different values based on conditions.",
            examples=[
                "SELECT CASE WHEN score >= 90 THEN 'A' WHEN score >= 80 THEN 'B' ELSE 'C' END FROM students;",
                "SELECT CASE status WHEN 'active' THEN 1 WHEN 'inactive' THEN 0 ELSE -1 END FROM users;"
            ],
            related=["if", "coalesce", "nullif"],
            url="https://duckdb.org/docs/sql/expressions/case.html"
        ),
        DocEntry(
            name="if",
            category="Conditional Functions",
            syntax="if(condition, true_result, false_result)",
            description="Returns true_result if condition is true, otherwise false_result.",
            examples=[
                "SELECT if(price > 100, 'expensive', 'affordable') FROM products;",
                "SELECT if(is_active, 'Yes', 'No') FROM users;"
            ],
            related=["case", "ifnull"],
            url="https://duckdb.org/docs/sql/functions/conditional.html"
        ),
        DocEntry(
            name="coalesce",
            category="Conditional Functions",
            syntax="coalesce(value1, value2, ...)",
            description="Returns the first non-NULL value from the argument list.",
            examples=[
                "SELECT coalesce(nickname, name, 'Unknown') FROM users;",
                "SELECT coalesce(preferred_phone, home_phone, mobile_phone) FROM contacts;"
            ],
            related=["ifnull", "nullif"],
            url="https://duckdb.org/docs/sql/functions/conditional.html"
        ),
        DocEntry(
            name="nullif",
            category="Conditional Functions",
            syntax="nullif(value1, value2)",
            description="Returns NULL if value1 equals value2, otherwise returns value1.",
            examples=[
                "SELECT nullif(status, 'unknown') FROM records;",
                "SELECT 1/nullif(divisor, 0) FROM data;  -- avoids division by zero"
            ],
            related=["coalesce", "ifnull"],
            url="https://duckdb.org/docs/sql/functions/conditional.html"
        ),
        DocEntry(
            name="ifnull",
            category="Conditional Functions",
            syntax="ifnull(value, default)",
            description="Returns default if value is NULL, otherwise returns value. Shorthand for coalesce(value, default).",
            examples=[
                "SELECT ifnull(middle_name, '') FROM users;",
                "SELECT ifnull(discount, 0) FROM products;"
            ],
            related=["coalesce", "nullif"],
            url="https://duckdb.org/docs/sql/functions/conditional.html"
        ),
        
        # ===== TYPE CONVERSION =====
        DocEntry(
            name="cast",
            category="Type Conversion",
            syntax="CAST(expression AS type) | expression::type",
            description="Converts an expression to a different data type.",
            examples=[
                "SELECT CAST('123' AS INTEGER);  -- 123",
                "SELECT '3.14'::DOUBLE;  -- 3.14",
                "SELECT CAST(date_column AS VARCHAR) FROM table;"
            ],
            related=["try_cast", "typeof"],
            url="https://duckdb.org/docs/sql/expressions/cast.html"
        ),
        DocEntry(
            name="try_cast",
            category="Type Conversion",
            syntax="TRY_CAST(expression AS type)",
            description="Like CAST, but returns NULL instead of error if conversion fails.",
            examples=[
                "SELECT TRY_CAST('abc' AS INTEGER);  -- NULL (instead of error)",
                "SELECT TRY_CAST('2024-01-01' AS DATE);  -- DATE '2024-01-01'"
            ],
            related=["cast", "typeof"],
            url="https://duckdb.org/docs/sql/expressions/cast.html"
        ),
        DocEntry(
            name="typeof",
            category="Type Conversion",
            syntax="typeof(expression)",
            description="Returns the data type of the expression as a string.",
            examples=[
                "SELECT typeof(42);  -- 'INTEGER'",
                "SELECT typeof(current_date);  -- 'DATE'",
                "SELECT typeof(column_name) FROM table LIMIT 1;"
            ],
            related=["cast", "try_cast"],
            url="https://duckdb.org/docs/sql/functions/utility.html"
        ),
        
        # ===== LIST/ARRAY FUNCTIONS =====
        DocEntry(
            name="list_value",
            category="List Functions",
            syntax="list_value(value1, value2, ...) | [value1, value2, ...]",
            description="Creates a list/array from the given values.",
            examples=[
                "SELECT list_value(1, 2, 3);  -- [1, 2, 3]",
                "SELECT [1, 2, 3];  -- [1, 2, 3]",
                "SELECT ['a', 'b', 'c'];"
            ],
            related=["array_agg", "unnest", "list_concat"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="unnest",
            category="List Functions",
            syntax="unnest(list)",
            description="Expands a list into individual rows.",
            examples=[
                "SELECT unnest([1, 2, 3]);  -- Returns 3 rows: 1, 2, 3",
                "SELECT id, unnest(tags) FROM articles;"
            ],
            related=["array_agg", "list_value"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="list_concat",
            category="List Functions",
            syntax="list_concat(list1, list2) | list1 || list2",
            description="Concatenates two lists together.",
            examples=[
                "SELECT list_concat([1, 2], [3, 4]);  -- [1, 2, 3, 4]",
                "SELECT [1, 2] || [3, 4];  -- [1, 2, 3, 4]"
            ],
            related=["list_value", "array_agg"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="list_element",
            category="List Functions",
            syntax="list_element(list, index) | list[index]",
            description="Returns the element at the specified index (1-based).",
            examples=[
                "SELECT list_element([10, 20, 30], 2);  -- 20",
                "SELECT ['a', 'b', 'c'][1];  -- 'a'"
            ],
            related=["list_slice", "len"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="list_contains",
            category="List Functions",
            syntax="list_contains(list, element) | list_has(list, element)",
            description="Returns true if the list contains the element.",
            examples=[
                "SELECT list_contains([1, 2, 3], 2);  -- true",
                "SELECT list_has(['a', 'b'], 'c');  -- false"
            ],
            related=["list_position", "array_has"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="list_filter",
            category="List Functions",
            syntax="list_filter(list, lambda)",
            description="Filters list elements using a lambda function.",
            examples=[
                "SELECT list_filter([1, 2, 3, 4, 5], x -> x > 2);  -- [3, 4, 5]",
                "SELECT list_filter(['apple', 'banana', 'apricot'], x -> x LIKE 'a%');"
            ],
            related=["list_transform", "list_reduce"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="list_transform",
            category="List Functions",
            syntax="list_transform(list, lambda) | list_apply(list, lambda)",
            description="Applies a lambda function to each element in the list.",
            examples=[
                "SELECT list_transform([1, 2, 3], x -> x * 2);  -- [2, 4, 6]",
                "SELECT list_apply(['hello', 'world'], x -> upper(x));  -- ['HELLO', 'WORLD']"
            ],
            related=["list_filter", "list_reduce"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="len",
            category="List Functions",
            syntax="len(list) | length(list) | array_length(list)",
            description="Returns the number of elements in the list.",
            examples=[
                "SELECT len([1, 2, 3]);  -- 3",
                "SELECT length([]);  -- 0"
            ],
            related=["list_element", "list_contains"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        
        # ===== JSON FUNCTIONS =====
        DocEntry(
            name="json_extract",
            category="JSON Functions",
            syntax="json_extract(json, path) | json -> path | json ->> path",
            description="Extracts a value from JSON. -> returns JSON, ->> returns text.",
            examples=[
                "SELECT json_extract('{\"name\": \"John\"}', '$.name');  -- '\"John\"'",
                "SELECT '{\"a\": 1}' -> '$.a';  -- 1",
                "SELECT '{\"name\": \"John\"}' ->> '$.name';  -- 'John' (as text)"
            ],
            related=["json_extract_string", "json_array_length"],
            url="https://duckdb.org/docs/sql/functions/json.html"
        ),
        DocEntry(
            name="json_extract_string",
            category="JSON Functions",
            syntax="json_extract_string(json, path)",
            description="Extracts a value from JSON and returns it as a string.",
            examples=[
                "SELECT json_extract_string('{\"name\": \"John\"}', '$.name');  -- 'John'",
                "SELECT json_extract_string(data, '$.address.city') FROM users;"
            ],
            related=["json_extract", "json_value"],
            url="https://duckdb.org/docs/sql/functions/json.html"
        ),
        DocEntry(
            name="json_array_length",
            category="JSON Functions",
            syntax="json_array_length(json[, path])",
            description="Returns the number of elements in a JSON array.",
            examples=[
                "SELECT json_array_length('[1, 2, 3]');  -- 3",
                "SELECT json_array_length('{\"items\": [1, 2]}', '$.items');  -- 2"
            ],
            related=["json_extract", "len"],
            url="https://duckdb.org/docs/sql/functions/json.html"
        ),
        DocEntry(
            name="json_object",
            category="JSON Functions",
            syntax="json_object(key1, value1, key2, value2, ...)",
            description="Creates a JSON object from key-value pairs.",
            examples=[
                "SELECT json_object('name', 'John', 'age', 30);  -- '{\"name\":\"John\",\"age\":30}'",
                "SELECT json_object('id', id, 'name', name) FROM users;"
            ],
            related=["json_array", "to_json"],
            url="https://duckdb.org/docs/sql/functions/json.html"
        ),
        DocEntry(
            name="json_array",
            category="JSON Functions",
            syntax="json_array(value1, value2, ...)",
            description="Creates a JSON array from the given values.",
            examples=[
                "SELECT json_array(1, 2, 3);  -- '[1,2,3]'",
                "SELECT json_array('a', 'b', 'c');  -- '[\"a\",\"b\",\"c\"]'"
            ],
            related=["json_object", "list_value"],
            url="https://duckdb.org/docs/sql/functions/json.html"
        ),
        
        # ===== SQL SYNTAX =====
        DocEntry(
            name="select",
            category="SQL Syntax",
            syntax="SELECT [DISTINCT] columns FROM table [WHERE condition] [GROUP BY ...] [HAVING ...] [ORDER BY ...] [LIMIT n]",
            description="Retrieves data from one or more tables. The fundamental SQL query statement.",
            examples=[
                "SELECT * FROM users;",
                "SELECT name, email FROM users WHERE active = true;",
                "SELECT category, count(*) FROM products GROUP BY category;"
            ],
            related=["from", "where", "group by", "order by"],
            url="https://duckdb.org/docs/sql/query_syntax/select.html"
        ),
        DocEntry(
            name="where",
            category="SQL Syntax",
            syntax="WHERE condition",
            description="Filters rows based on a condition. Used with SELECT, UPDATE, DELETE.",
            examples=[
                "SELECT * FROM users WHERE age >= 18;",
                "SELECT * FROM orders WHERE status = 'pending' AND amount > 100;",
                "SELECT * FROM products WHERE name LIKE '%phone%';"
            ],
            related=["select", "and", "or", "like", "in", "between"],
            url="https://duckdb.org/docs/sql/query_syntax/where.html"
        ),
        DocEntry(
            name="join",
            category="SQL Syntax",
            syntax="table1 [INNER|LEFT|RIGHT|FULL] JOIN table2 ON condition",
            description="Combines rows from two or more tables based on a related column.",
            examples=[
                "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id;",
                "SELECT * FROM employees LEFT JOIN departments ON employees.dept_id = departments.id;",
                "SELECT * FROM a FULL OUTER JOIN b ON a.id = b.id;"
            ],
            related=["inner join", "left join", "cross join", "select"],
            url="https://duckdb.org/docs/sql/query_syntax/from.html"
        ),
        DocEntry(
            name="group by",
            category="SQL Syntax",
            syntax="GROUP BY column1[, column2, ...] | GROUP BY ALL",
            description="Groups rows with the same values for aggregate calculations. GROUP BY ALL groups by all non-aggregated columns.",
            examples=[
                "SELECT category, count(*) FROM products GROUP BY category;",
                "SELECT year, month, sum(sales) FROM revenue GROUP BY year, month;",
                "SELECT name, department, avg(salary) FROM employees GROUP BY ALL;"
            ],
            related=["having", "count", "sum", "avg"],
            url="https://duckdb.org/docs/sql/query_syntax/groupby.html"
        ),
        DocEntry(
            name="having",
            category="SQL Syntax",
            syntax="HAVING condition",
            description="Filters groups created by GROUP BY. Use HAVING for aggregate conditions, WHERE for row conditions.",
            examples=[
                "SELECT category, count(*) as cnt FROM products GROUP BY category HAVING count(*) > 5;",
                "SELECT dept, avg(salary) FROM employees GROUP BY dept HAVING avg(salary) > 50000;"
            ],
            related=["group by", "where"],
            url="https://duckdb.org/docs/sql/query_syntax/having.html"
        ),
        DocEntry(
            name="order by",
            category="SQL Syntax",
            syntax="ORDER BY column1 [ASC|DESC][, column2 [ASC|DESC], ...]",
            description="Sorts the result set by one or more columns. ASC is ascending (default), DESC is descending.",
            examples=[
                "SELECT * FROM products ORDER BY price DESC;",
                "SELECT * FROM users ORDER BY last_name, first_name;",
                "SELECT * FROM orders ORDER BY created_at DESC NULLS LAST;"
            ],
            related=["select", "limit", "nulls first", "nulls last"],
            url="https://duckdb.org/docs/sql/query_syntax/orderby.html"
        ),
        DocEntry(
            name="limit",
            category="SQL Syntax",
            syntax="LIMIT count [OFFSET skip]",
            description="Restricts the number of rows returned. OFFSET skips rows before returning results.",
            examples=[
                "SELECT * FROM products LIMIT 10;",
                "SELECT * FROM users LIMIT 10 OFFSET 20;  -- skip 20, return next 10",
                "SELECT * FROM orders ORDER BY date DESC LIMIT 5;"
            ],
            related=["order by", "select"],
            url="https://duckdb.org/docs/sql/query_syntax/limit.html"
        ),
        DocEntry(
            name="with",
            category="SQL Syntax",
            syntax="WITH cte_name AS (SELECT ...) SELECT ... FROM cte_name",
            description="Common Table Expression (CTE) - creates a named temporary result set. Improves readability for complex queries.",
            examples=[
                "WITH active_users AS (SELECT * FROM users WHERE active = true) SELECT * FROM active_users;",
                "WITH RECURSIVE nums AS (SELECT 1 AS n UNION ALL SELECT n+1 FROM nums WHERE n < 10) SELECT * FROM nums;"
            ],
            related=["select", "recursive"],
            url="https://duckdb.org/docs/sql/query_syntax/with.html"
        ),
        DocEntry(
            name="union",
            category="SQL Syntax",
            syntax="SELECT ... UNION [ALL] SELECT ...",
            description="Combines result sets from two queries. UNION removes duplicates, UNION ALL keeps all rows.",
            examples=[
                "SELECT name FROM employees UNION SELECT name FROM contractors;",
                "SELECT * FROM sales_2023 UNION ALL SELECT * FROM sales_2024;"
            ],
            related=["intersect", "except"],
            url="https://duckdb.org/docs/sql/query_syntax/setops.html"
        ),
        DocEntry(
            name="intersect",
            category="SQL Syntax",
            syntax="SELECT ... INTERSECT [ALL] SELECT ...",
            description="Returns only rows that appear in both result sets.",
            examples=[
                "SELECT customer_id FROM orders_2023 INTERSECT SELECT customer_id FROM orders_2024;",
                "SELECT name FROM table1 INTERSECT SELECT name FROM table2;"
            ],
            related=["union", "except"],
            url="https://duckdb.org/docs/sql/query_syntax/setops.html"
        ),
        DocEntry(
            name="except",
            category="SQL Syntax",
            syntax="SELECT ... EXCEPT [ALL] SELECT ...",
            description="Returns rows from the first query that don't appear in the second query.",
            examples=[
                "SELECT id FROM all_products EXCEPT SELECT id FROM discontinued_products;",
                "SELECT name FROM employees EXCEPT SELECT name FROM managers;"
            ],
            related=["union", "intersect"],
            url="https://duckdb.org/docs/sql/query_syntax/setops.html"
        ),
        DocEntry(
            name="distinct",
            category="SQL Syntax",
            syntax="SELECT DISTINCT column1[, column2, ...] FROM table | DISTINCT ON (column)",
            description="Removes duplicate rows from the result set. DISTINCT ON keeps first row for each distinct value.",
            examples=[
                "SELECT DISTINCT category FROM products;",
                "SELECT DISTINCT ON (customer_id) * FROM orders ORDER BY customer_id, date DESC;"
            ],
            related=["select", "count", "group by"],
            url="https://duckdb.org/docs/sql/query_syntax/select.html"
        ),
        DocEntry(
            name="like",
            category="SQL Syntax",
            syntax="column LIKE pattern | column ILIKE pattern",
            description="Pattern matching with wildcards. % matches any sequence, _ matches single char. ILIKE is case-insensitive.",
            examples=[
                "SELECT * FROM users WHERE name LIKE 'J%';  -- starts with J",
                "SELECT * FROM products WHERE name ILIKE '%phone%';  -- contains 'phone' (case-insensitive)",
                "SELECT * FROM codes WHERE code LIKE 'A__';  -- A followed by exactly 2 chars"
            ],
            related=["regexp_matches", "similar to", "where"],
            url="https://duckdb.org/docs/sql/expressions/pattern_matching.html"
        ),
        DocEntry(
            name="in",
            category="SQL Syntax",
            syntax="column IN (value1, value2, ...) | column IN (SELECT ...)",
            description="Tests if a value matches any value in a list or subquery.",
            examples=[
                "SELECT * FROM products WHERE category IN ('Electronics', 'Books', 'Toys');",
                "SELECT * FROM orders WHERE customer_id IN (SELECT id FROM vip_customers);"
            ],
            related=["not in", "any", "all", "where"],
            url="https://duckdb.org/docs/sql/expressions/in.html"
        ),
        DocEntry(
            name="between",
            category="SQL Syntax",
            syntax="column BETWEEN low AND high",
            description="Tests if a value is within a range (inclusive on both ends).",
            examples=[
                "SELECT * FROM orders WHERE amount BETWEEN 100 AND 500;",
                "SELECT * FROM events WHERE date BETWEEN '2024-01-01' AND '2024-12-31';"
            ],
            related=["where", "and"],
            url="https://duckdb.org/docs/sql/expressions/comparison_operators.html"
        ),
        DocEntry(
            name="exists",
            category="SQL Syntax",
            syntax="EXISTS (SELECT ...)",
            description="Tests if a subquery returns any rows. Often more efficient than IN for large datasets.",
            examples=[
                "SELECT * FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);",
                "SELECT * FROM products p WHERE NOT EXISTS (SELECT 1 FROM order_items WHERE product_id = p.id);"
            ],
            related=["in", "not exists", "where"],
            url="https://duckdb.org/docs/sql/expressions/exists.html"
        ),
        DocEntry(
            name="insert",
            category="SQL Syntax",
            syntax="INSERT INTO table [(columns)] VALUES (values) | INSERT INTO table SELECT ...",
            description="Inserts new rows into a table.",
            examples=[
                "INSERT INTO users (name, email) VALUES ('John', 'john@example.com');",
                "INSERT INTO archive SELECT * FROM orders WHERE date < '2023-01-01';",
                "INSERT INTO products VALUES (1, 'Widget', 9.99);"
            ],
            related=["update", "delete", "select"],
            url="https://duckdb.org/docs/sql/statements/insert.html"
        ),
        DocEntry(
            name="update",
            category="SQL Syntax",
            syntax="UPDATE table SET column1 = value1[, column2 = value2, ...] [WHERE condition]",
            description="Modifies existing rows in a table. Always use WHERE to avoid updating all rows.",
            examples=[
                "UPDATE users SET status = 'inactive' WHERE last_login < '2023-01-01';",
                "UPDATE products SET price = price * 1.1 WHERE category = 'Electronics';"
            ],
            related=["insert", "delete", "where"],
            url="https://duckdb.org/docs/sql/statements/update.html"
        ),
        DocEntry(
            name="delete",
            category="SQL Syntax",
            syntax="DELETE FROM table [WHERE condition]",
            description="Removes rows from a table. Always use WHERE to avoid deleting all rows.",
            examples=[
                "DELETE FROM users WHERE status = 'deleted';",
                "DELETE FROM logs WHERE created_at < current_date - INTERVAL '30 days';"
            ],
            related=["insert", "update", "truncate", "where"],
            url="https://duckdb.org/docs/sql/statements/delete.html"
        ),
        DocEntry(
            name="create table",
            category="SQL Syntax",
            syntax="CREATE TABLE [IF NOT EXISTS] name (column type [constraints], ...) | CREATE TABLE name AS SELECT ...",
            description="Creates a new table with specified columns and types, or from a query result.",
            examples=[
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, email VARCHAR UNIQUE);",
                "CREATE TABLE IF NOT EXISTS logs (id INTEGER, message TEXT, created_at TIMESTAMP DEFAULT current_timestamp);",
                "CREATE TABLE active_users AS SELECT * FROM users WHERE active = true;"
            ],
            related=["drop table", "alter table", "create view"],
            url="https://duckdb.org/docs/sql/statements/create_table.html"
        ),
        DocEntry(
            name="create view",
            category="SQL Syntax",
            syntax="CREATE [OR REPLACE] VIEW name AS SELECT ...",
            description="Creates a virtual table based on a query. Views don't store data, they execute the query when accessed.",
            examples=[
                "CREATE VIEW active_users AS SELECT * FROM users WHERE active = true;",
                "CREATE OR REPLACE VIEW revenue_summary AS SELECT date_trunc('month', date) as month, sum(amount) FROM sales GROUP BY 1;"
            ],
            related=["create table", "drop view"],
            url="https://duckdb.org/docs/sql/statements/create_view.html"
        ),
        DocEntry(
            name="alter table",
            category="SQL Syntax",
            syntax="ALTER TABLE name ADD [COLUMN] column type | ALTER TABLE name DROP [COLUMN] column | ALTER TABLE name RENAME [COLUMN] old TO new",
            description="Modifies the structure of an existing table.",
            examples=[
                "ALTER TABLE users ADD COLUMN phone VARCHAR;",
                "ALTER TABLE products DROP COLUMN deprecated_field;",
                "ALTER TABLE orders RENAME COLUMN qty TO quantity;"
            ],
            related=["create table", "drop table"],
            url="https://duckdb.org/docs/sql/statements/alter_table.html"
        ),
        DocEntry(
            name="drop table",
            category="SQL Syntax",
            syntax="DROP TABLE [IF EXISTS] name [CASCADE]",
            description="Removes a table and all its data. IF EXISTS prevents errors if table doesn't exist.",
            examples=[
                "DROP TABLE temp_data;",
                "DROP TABLE IF EXISTS old_logs;",
                "DROP TABLE parent_table CASCADE;  -- also drops dependent objects"
            ],
            related=["create table", "truncate"],
            url="https://duckdb.org/docs/sql/statements/drop.html"
        ),
        
        # ===== DUCKDB SPECIFIC =====
        DocEntry(
            name="read_csv",
            category="DuckDB Specific",
            syntax="read_csv('file.csv', [options]) | read_csv_auto('file.csv')",
            description="Reads a CSV file directly in a query. Supports auto-detection of schema and delimiters.",
            examples=[
                "SELECT * FROM read_csv('data.csv');",
                "SELECT * FROM read_csv_auto('data.csv');",
                "SELECT * FROM read_csv('data.csv', header=true, delim=';');"
            ],
            related=["read_parquet", "read_json", "copy"],
            url="https://duckdb.org/docs/data/csv/overview.html"
        ),
        DocEntry(
            name="read_parquet",
            category="DuckDB Specific",
            syntax="read_parquet('file.parquet') | read_parquet(['file1.parquet', 'file2.parquet'])",
            description="Reads Parquet files directly in a query. Supports reading multiple files with glob patterns.",
            examples=[
                "SELECT * FROM read_parquet('data.parquet');",
                "SELECT * FROM read_parquet('data/*.parquet');",
                "SELECT * FROM read_parquet(['2023.parquet', '2024.parquet']);"
            ],
            related=["read_csv", "read_json", "copy"],
            url="https://duckdb.org/docs/data/parquet/overview.html"
        ),
        DocEntry(
            name="read_json",
            category="DuckDB Specific",
            syntax="read_json('file.json', [options]) | read_json_auto('file.json')",
            description="Reads JSON files directly in a query. Supports newline-delimited JSON and nested structures.",
            examples=[
                "SELECT * FROM read_json('data.json');",
                "SELECT * FROM read_json_auto('data.json');",
                "SELECT * FROM read_json('data.ndjson', format='newline_delimited');"
            ],
            related=["read_csv", "read_parquet", "json_extract"],
            url="https://duckdb.org/docs/data/json/overview.html"
        ),
        DocEntry(
            name="copy",
            category="DuckDB Specific",
            syntax="COPY table TO 'file' [WITH (options)] | COPY (SELECT ...) TO 'file'",
            description="Exports data to a file. Supports CSV, Parquet, JSON formats.",
            examples=[
                "COPY users TO 'users.csv' (HEADER, DELIMITER ',');",
                "COPY (SELECT * FROM orders WHERE year = 2024) TO 'orders_2024.parquet' (FORMAT PARQUET);",
                "COPY table TO 'output.json' (FORMAT JSON);"
            ],
            related=["read_csv", "read_parquet", "export"],
            url="https://duckdb.org/docs/sql/statements/copy.html"
        ),
        DocEntry(
            name="describe",
            category="DuckDB Specific",
            syntax="DESCRIBE table | DESCRIBE SELECT ...",
            description="Shows the column names and types of a table or query result.",
            examples=[
                "DESCRIBE users;",
                "DESCRIBE SELECT * FROM orders WHERE amount > 100;"
            ],
            related=["show tables", "pragma table_info"],
            url="https://duckdb.org/docs/sql/statements/describe.html"
        ),
        DocEntry(
            name="show tables",
            category="DuckDB Specific",
            syntax="SHOW TABLES | SHOW ALL TABLES",
            description="Lists all tables in the current database/schema.",
            examples=[
                "SHOW TABLES;",
                "SHOW ALL TABLES;"
            ],
            related=["describe", "information_schema"],
            url="https://duckdb.org/docs/sql/statements/show.html"
        ),
        DocEntry(
            name="sample",
            category="DuckDB Specific",
            syntax="SELECT * FROM table USING SAMPLE n | USING SAMPLE n%",
            description="Returns a random sample of rows from a table. Can specify count or percentage.",
            examples=[
                "SELECT * FROM large_table USING SAMPLE 1000;  -- 1000 random rows",
                "SELECT * FROM data USING SAMPLE 10%;  -- 10% of rows",
                "SELECT * FROM orders USING SAMPLE 100 ROWS;"
            ],
            related=["random", "limit", "tablesample"],
            url="https://duckdb.org/docs/sql/query_syntax/sample.html"
        ),
        DocEntry(
            name="pivot",
            category="DuckDB Specific",
            syntax="PIVOT table ON column USING aggregate(value) [GROUP BY ...]",
            description="Transforms rows into columns. Creates a pivot table from data.",
            examples=[
                "PIVOT sales ON product USING sum(amount);",
                "PIVOT monthly_data ON month USING sum(revenue) GROUP BY year;",
                "FROM sales PIVOT (sum(amount) FOR product IN ('A', 'B', 'C'));"
            ],
            related=["unpivot", "group by"],
            url="https://duckdb.org/docs/sql/statements/pivot.html"
        ),
        DocEntry(
            name="unpivot",
            category="DuckDB Specific",
            syntax="UNPIVOT table ON columns INTO NAME name_col VALUE value_col",
            description="Transforms columns into rows. Opposite of PIVOT.",
            examples=[
                "UNPIVOT wide_table ON (col1, col2, col3) INTO NAME category VALUE amount;",
                "FROM monthly_sales UNPIVOT (jan, feb, mar) INTO NAME month VALUE revenue;"
            ],
            related=["pivot"],
            url="https://duckdb.org/docs/sql/statements/unpivot.html"
        ),
        DocEntry(
            name="qualify",
            category="DuckDB Specific",
            syntax="QUALIFY window_function_condition",
            description="Filters rows based on window function results. Like HAVING but for window functions.",
            examples=[
                "SELECT * FROM employees QUALIFY row_number() OVER (PARTITION BY dept ORDER BY salary DESC) = 1;",
                "SELECT * FROM data QUALIFY rank() OVER (ORDER BY score DESC) <= 10;"
            ],
            related=["window functions", "having", "row_number"],
            url="https://duckdb.org/docs/sql/query_syntax/qualify.html"
        ),
        DocEntry(
            name="exclude",
            category="DuckDB Specific",
            syntax="SELECT * EXCLUDE (column1, column2) FROM table | SELECT columns EXCLUDE column",
            description="Selects all columns except the specified ones. Useful for wide tables.",
            examples=[
                "SELECT * EXCLUDE (id, created_at) FROM users;",
                "SELECT columns(*) EXCLUDE (internal_field) FROM data;"
            ],
            related=["replace", "select"],
            url="https://duckdb.org/docs/sql/expressions/star.html"
        ),
        DocEntry(
            name="replace",
            category="DuckDB Specific",
            syntax="SELECT * REPLACE (expression AS column) FROM table",
            description="Selects all columns but replaces specified columns with new expressions.",
            examples=[
                "SELECT * REPLACE (upper(name) AS name) FROM users;",
                "SELECT * REPLACE (price * 1.1 AS price, lower(category) AS category) FROM products;"
            ],
            related=["exclude", "select"],
            url="https://duckdb.org/docs/sql/expressions/star.html"
        ),
        DocEntry(
            name="columns",
            category="DuckDB Specific",
            syntax="columns(*) | columns('regex') | columns(expression)",
            description="Dynamic column selection using patterns or expressions.",
            examples=[
                "SELECT columns('price_.*') FROM products;  -- columns starting with 'price_'",
                "SELECT columns(c -> c LIKE '%_id') FROM data;  -- columns ending with '_id'",
                "SELECT min(columns(*)) FROM table;  -- min of all columns"
            ],
            related=["exclude", "replace", "select"],
            url="https://duckdb.org/docs/sql/expressions/star.html"
        ),
        DocEntry(
            name="asof join",
            category="DuckDB Specific",
            syntax="table1 ASOF JOIN table2 ON condition AND time_condition",
            description="Joins tables based on the closest match in time. Useful for time-series data.",
            examples=[
                "SELECT * FROM trades ASOF JOIN prices ON trades.symbol = prices.symbol AND trades.time >= prices.time;",
                "SELECT * FROM events ASOF LEFT JOIN states ON events.id = states.id AND events.ts >= states.ts;"
            ],
            related=["join", "lateral join"],
            url="https://duckdb.org/docs/sql/query_syntax/from.html"
        ),
        DocEntry(
            name="generate_series",
            category="DuckDB Specific",
            syntax="generate_series(start, stop[, step])",
            description="Generates a series of values from start to stop (inclusive).",
            examples=[
                "SELECT * FROM generate_series(1, 10);  -- 1 to 10",
                "SELECT * FROM generate_series(DATE '2024-01-01', DATE '2024-12-31', INTERVAL '1 month');",
                "SELECT * FROM generate_series(0, 100, 5);  -- 0, 5, 10, ..., 100"
            ],
            related=["range", "unnest"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="range",
            category="DuckDB Specific",
            syntax="range(start, stop[, step])",
            description="Generates a list of values from start to stop (exclusive).",
            examples=[
                "SELECT range(1, 5);  -- [1, 2, 3, 4]",
                "SELECT unnest(range(0, 10, 2));  -- 0, 2, 4, 6, 8",
                "SELECT range(10);  -- [0, 1, 2, ..., 9]"
            ],
            related=["generate_series", "list_value"],
            url="https://duckdb.org/docs/sql/functions/list.html"
        ),
        DocEntry(
            name="struct_pack",
            category="DuckDB Specific",
            syntax="struct_pack(key1 := value1, key2 := value2, ...) | {'key1': value1, 'key2': value2}",
            description="Creates a struct (named tuple) from key-value pairs.",
            examples=[
                "SELECT struct_pack(name := 'John', age := 30);",
                "SELECT {'name': name, 'email': email} AS user_info FROM users;",
                "SELECT row(name, age) FROM users;"
            ],
            related=["struct_extract", "row"],
            url="https://duckdb.org/docs/sql/functions/struct.html"
        ),
        DocEntry(
            name="struct_extract",
            category="DuckDB Specific",
            syntax="struct_extract(struct, 'key') | struct.key | struct['key']",
            description="Extracts a field from a struct.",
            examples=[
                "SELECT struct_extract({'name': 'John', 'age': 30}, 'name');  -- 'John'",
                "SELECT user_struct.name FROM data;",
                "SELECT (struct_column)['field'] FROM table;"
            ],
            related=["struct_pack", "json_extract"],
            url="https://duckdb.org/docs/sql/functions/struct.html"
        ),
    ]
    
    for doc in docs:
        # Store by name (lowercase for case-insensitive lookup)
        DUCKDB_DOCS[doc.name.lower()] = doc
        
        # Also index common aliases and variations
        name_lower = doc.name.lower()
        if '_' in name_lower:
            # Also index without underscores
            DUCKDB_DOCS[name_lower.replace('_', '')] = doc
        if ' ' in name_lower:
            # Also index with underscores instead of spaces
            DUCKDB_DOCS[name_lower.replace(' ', '_')] = doc
            # And without spaces
            DUCKDB_DOCS[name_lower.replace(' ', '')] = doc


# Build the database on module load
_build_docs_database()


class DuckDBDocsSearcher:
    """Searches DuckDB documentation based on user input."""
    
    def __init__(self):
        self._last_search = ""
        self._last_results = []
    
    def search(self, query: str, max_results: int = 10) -> List[DocEntry]:
        """
        Search documentation for matching entries.
        
        Args:
            query: The search query (e.g., "regex", "date_trunc")
            max_results: Maximum number of results to return
            
        Returns:
            List of matching DocEntry objects, sorted by relevance
        """
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower().strip()
        
        # Cache identical searches
        if query_lower == self._last_search:
            return self._last_results[:max_results]
        
        results: List[Tuple[int, DocEntry]] = []
        
        for name, doc in DUCKDB_DOCS.items():
            score = self._calculate_relevance(query_lower, name, doc)
            if score > 0:
                results.append((score, doc))
        
        # Sort by relevance score (higher is better)
        results.sort(key=lambda x: -x[0])
        
        # Remove duplicates (same doc might be indexed multiple times)
        seen = set()
        unique_results = []
        for score, doc in results:
            if doc.name not in seen:
                seen.add(doc.name)
                unique_results.append(doc)
        
        self._last_search = query_lower
        self._last_results = unique_results
        
        return unique_results[:max_results]
    
    def _calculate_relevance(self, query: str, name: str, doc: DocEntry) -> int:
        """Calculate relevance score for a document."""
        score = 0
        
        # Exact name match is highest priority
        if name == query:
            score += 1000
        elif name.startswith(query):
            score += 500
        elif query in name:
            score += 200
        
        # Check category
        if query in doc.category.lower():
            score += 100
        
        # Check description
        if query in doc.description.lower():
            score += 50
        
        # Check syntax
        if query in doc.syntax.lower():
            score += 75
        
        # Check related
        for related in doc.related:
            if query in related.lower():
                score += 25
        
        # Check examples
        for example in doc.examples:
            if query in example.lower():
                score += 10
        
        return score
    
    def get_doc_by_name(self, name: str) -> Optional[DocEntry]:
        """Get a specific documentation entry by name."""
        return DUCKDB_DOCS.get(name.lower())
    
    def get_all_categories(self) -> List[str]:
        """Get all unique documentation categories."""
        categories = set()
        for doc in DUCKDB_DOCS.values():
            categories.add(doc.category)
        return sorted(categories)
    
    def get_docs_by_category(self, category: str) -> List[DocEntry]:
        """Get all documentation entries in a category."""
        results = []
        seen = set()
        for doc in DUCKDB_DOCS.values():
            if doc.category.lower() == category.lower() and doc.name not in seen:
                seen.add(doc.name)
                results.append(doc)
        return sorted(results, key=lambda d: d.name)


# Global searcher instance
_searcher: Optional[DuckDBDocsSearcher] = None


def get_docs_searcher() -> DuckDBDocsSearcher:
    """Get the global documentation searcher instance."""
    global _searcher
    if _searcher is None:
        _searcher = DuckDBDocsSearcher()
    return _searcher

