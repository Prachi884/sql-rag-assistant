"""
src/csv_loader.py

Loads user-uploaded CSV files into the SQLite database and
generates fresh schema documentation for them.

Workflow:
    1. User uploads CSVs via the Streamlit UI
    2. Each CSV becomes a table named after the file
    3. Schema docs are regenerated from the new tables
    4. The RAG vector store cache is reset so it picks up the new schema
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import sqlite3

from src.sql_executor import DB_PATH
from src.rag_chain import _vectorstore_cache


def reset_vector_cache() -> None:
    """
    Invalidate the cached Chroma vector store so the next question
    triggers re-embedding with the latest schema_docs.txt.
    """
    global _vectorstore_cache
    _vectorstore_cache = None


def _safe_table_name(filename: str) -> str:
    """Turn 'My Sales 2024.csv' into 'my_sales_2024'."""
    stem = Path(filename).stem
    return "".join(c if c.isalnum() else "_" for c in stem).lower()


def load_csvs_to_db(uploaded_files: List[Any]) -> Dict[str, Any]:
    """
    Load each uploaded CSV into the SQLite database as a table.

    Args:
        uploaded_files: A list of Streamlit UploadedFile objects.

    Returns:
        A dict with two keys:
            - 'tables': list of dicts with table info
            - 'errors': list of error strings
    """
    tables_created: List[Dict[str, Any]] = []
    errors: List[str] = []

    for uploaded_file in uploaded_files:
        try:
            df: pd.DataFrame = pd.read_csv(uploaded_file)
            table_name: str = _safe_table_name(uploaded_file.name)

            with sqlite3.connect(str(DB_PATH)) as conn:
                df.to_sql(table_name, conn, if_exists="replace", index=False)

            tables_created.append({
                "name": table_name,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            })
        except Exception as e:
            errors.append(f"{uploaded_file.name}: {str(e)}")

    if tables_created:
        schema_text: str = generate_schema_docs(tables_created)
        Path("data/schema_docs.txt").write_text(schema_text)
        reset_vector_cache()

    return {"tables": tables_created, "errors": errors}


def generate_schema_docs(tables: List[Dict[str, Any]]) -> str:
    """
    Auto-generate plain-English schema docs from loaded table info.
    The RAG pipeline uses this file to understand the database.
    """
    lines: List[str] = ["# Database Schema Documentation", ""]
    lines.append(f"This database currently contains {len(tables)} table(s).")
    lines.append("")
    lines.append("These tables were loaded from user-uploaded CSV files.")
    lines.append("All amounts are in their original units from the source data.")
    lines.append("")

    for table in tables:
        lines.append(f"## Table: {table['name']}")
        lines.append("")
        lines.append(f"Contains {table['rows']} rows.")
        lines.append("")
        lines.append("Columns:")
        for col in table["columns"]:
            dtype: str = table["dtypes"].get(col, "unknown")
            lines.append(f"- {col} : {dtype}")
        lines.append("")

    lines.append("## Query Patterns")
    lines.append("")
    lines.append("- For 'top N' questions, use ORDER BY ... DESC LIMIT N")
    lines.append("- For aggregation, use SUM, AVG, COUNT, MIN, MAX")
    lines.append("- For filtering, use WHERE with appropriate column names")
    lines.append("")

    return "\n".join(lines)


def reset_to_sample_database() -> None:
    """Reset the database to the sample e-commerce data."""
    from src.database import create_database
    create_database()
    reset_vector_cache()