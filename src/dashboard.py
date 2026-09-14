"""
src/dashboard.py

Auto-generates Plotly visualizations from SQL query results.
Uses the LLM to pick the best chart type based on data shape.
"""

from typing import Any, List, Tuple

import pandas as pd
import plotly.express as px

from src.llm_setup import get_llm


# Chart types we support
CHART_TYPES: List[str] = ["bar", "line", "pie", "scatter"]


def _first_two_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """Return (x_column, y_column) for charting."""
    return df.columns[0], df.columns[1]


def pick_chart_type(columns: List[str], sample_rows: List[Tuple]) -> str:
    """
    Use the LLM to pick the best chart type for the data shape.
    Returns one of: bar, line, pie, scatter.
    """
    llm = get_llm()

    sample_text: str = "Columns: " + ", ".join(columns) + "\n"
    sample_text += "Sample rows:\n"
    for row in sample_rows[:5]:
        sample_text += "  " + " | ".join(str(c) for c in row) + "\n"

    prompt: str = (
        "You are a data visualization expert.\n\n"
        "Given this data:\n"
        f"{sample_text}\n"
        "Pick the SINGLE best chart type from this list:\n"
        "- bar (for comparing categories)\n"
        "- line (for trends over time / ordered data)\n"
        "- pie (for proportions, max 7 categories)\n"
        "- scatter (for correlations between two numeric variables)\n\n"
        "Return ONLY the chart type name. Nothing else."
    )

    response: str = llm.invoke(prompt).content.strip().lower()

    for ct in CHART_TYPES:
        if ct in response:
            return ct
    return "bar"


def create_chart(df: pd.DataFrame, chart_type: str) -> Any:
    """
    Create a Plotly chart from a DataFrame.
    Uses the first column as x and second as y.
    """
    if df.empty or len(df.columns) < 2:
        return None

    x_col, y_col = _first_two_columns(df)

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col,
                         title=f"{y_col} distribution")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col,
                             title=f"{y_col} vs {x_col}")
        else:
            fig = px.bar(df, x=x_col, y=y_col)

        fig.update_layout(template="plotly_dark", height=400)
        return fig
    except Exception:
        # Fallback to a safe bar chart
        return px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")