"""
src/sql_executor.py

Validates and executes SQL queries against the sample SQLite database.

This module is the safety layer of the SQL RAG assistant. It ensures the
LLM can never accidentally (or maliciously) drop tables, delete data, or
run destructive operations. Only SELECT queries are allowed.

Functions:
    is_safe(sql) -> (bool, str)
    execute_sql(sql) -> (List[str], List[Tuple])
    format_results(columns, rows, max_rows=50) -> str
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

# ---------- Configuration ----------
DB_PATH = Path("data/sample.db")

# Keywords we REFUSE to allow in any query (case-insensitive).
# Using a tuple makes intent clear and prevents accidental mutation.
FORBIDDEN_KEYWORDS: Tuple[str, ...] = (
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "CREATE", "REPLACE", "ATTACH", "DETACH",
)


# ---------- Custom exception ----------
class UnsafeSQLError(Exception):
    """Raised when a generated SQL query fails the safety checks."""


# ---------- Safety check ----------
def is_safe(sql: str) -> Tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute.

    A query is considered safe if it:
        - is non-empty
        - starts with SELECT or WITH
        - contains no destructive keywords (DROP, DELETE, etc.)
        - has no stacked statements
        - has no comments

    Args:
        sql: The raw SQL query string.

    Returns:
        A tuple (is_safe, reason). reason is empty when is_safe is True.
    """
    if not sql or not sql.strip():
        return False, "Empty query"

    cleaned = sql.strip().upper()

    # Must be a read-only query
    starts_with_select = cleaned.startswith("SELECT")
    starts_with_with = cleaned.startswith("WITH")
    if not (starts_with_select or starts_with_with):
        first_word = cleaned.split()[0] if cleaned.split() else "nothing"
        return False, "Only SELECT queries are allowed. Got: " + first_word

    # Block any destructive keywords (word-boundary match so column names
    # like 'updated_at' don't false-positive on 'UPDATE').
    for kw in FORBIDDEN_KEYWORDS:
        pattern: str = r"\b" + kw + r"\b"
        if re.search(pattern, cleaned):
            return False, "Forbidden keyword detected: " + kw

    # Block stacked statements (multiple ; separated queries)
    statements: List[str] = [s for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple statements not allowed"

    # Block comment-based attacks (-- or /* */)
    if "--" in sql or "/*" in sql:
        return False, "Comments not allowed in generated SQL"

    return True, "OK"


# ---------- Execution ----------
def execute_sql(sql: str) -> Tuple[List[str], List[Tuple]]:
    """
    Validate and execute a SQL query, returning columns and rows.

    Args:
        sql: The SQL query to run.

    Returns:
        (column_names, rows) where rows is a list of tuples.

    Raises:
        UnsafeSQLError: if the query fails safety checks.
        sqlite3.Error: if SQLite rejects the query (syntax error, etc.).
    """
    safe, reason = is_safe(sql)
    if not safe:
        raise UnsafeSQLError("Query rejected: " + reason)

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns: List[str] = []
        if cursor.description is not None:
            columns = [desc[0] for desc in cursor.description]
        rows: List[Tuple] = cursor.fetchall()
        return columns, rows
    finally:
        conn.close()


# ---------- Pretty printing ----------
def format_results(
    columns: List[str],
    rows: List[Tuple],
    max_rows: int = 50,
) -> str:
    """
    Format query results as a readable text table.

    Args:
        columns: List of column names.
        rows: List of result rows (each a tuple).
        max_rows: Maximum number of rows to display before truncating.

    Returns:
        A formatted string with the results table.
    """
    if not rows:
        return "Query returned no rows."

    rows_to_show: List[Tuple] = rows[:max_rows]
    header: str = " | ".join(columns)
    separator: str = "-" * len(header)
    body_lines: List[str] = []
    for row in rows_to_show:
        body_lines.append(" | ".join(str(c) for c in row))

    output: str = header + "\n" + separator + "\n" + "\n".join(body_lines)

    if len(rows) > max_rows:
        output += "\n... (" + str(len(rows) - max_rows) + " more rows hidden)"
    return output


# ---------- Self-test ----------
if __name__ == "__main__":
    print("--- Test 1: Safe query ---")
    try:
        cols, rows = execute_sql("SELECT COUNT(*) FROM customers;")
        print("Columns:", cols)
        print("Result:", rows[0][0], "customers")
    except Exception as e:
        print("FAILED:", e)

    print("")
    print("--- Test 2: Unsafe DROP ---")
    try:
        execute_sql("DROP TABLE customers;")
        print("FAILED: dangerous query was allowed!")
    except UnsafeSQLError as e:
        print("Correctly blocked:", e)

    print("")
    print("--- Test 3: Unsafe DELETE ---")
    try:
        execute_sql("DELETE FROM customers;")
        print("FAILED: dangerous query was allowed!")
    except UnsafeSQLError as e:
        print("Correctly blocked:", e)
        