"""
app.py

The Streamlit UI for the SQL RAG Assistant.

Three tabs:
    1. SQL Chat       — ask questions, get SQL + answers + tables
    2. Dashboard      — auto-generate charts from natural-language queries
    3. Schema Explorer — browse tables, see column types, sample data
"""

from pathlib import Path
from typing import List

import pandas as pd
import sqlite3
import streamlit as st

from src.rag_chain import ask
from src.csv_loader import load_csvs_to_db, reset_to_sample_database
from src.dashboard import pick_chart_type, create_chart
from src.sql_executor import DB_PATH


# ---------- Page config ----------
st.set_page_config(
    page_title="SQL RAG Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Custom CSS ----------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0e1117 0%, #161a23 100%);
    }
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 28px 32px;
        border-radius: 18px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px rgba(102, 126, 234, 0.25);
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0;
    }
    .hero-sub {
        font-size: 1.05rem;
        margin-top: 6px;
        opacity: 0.92;
    }
    .stat-card {
        background: #1a1d29;
        padding: 16px 18px;
        border-radius: 12px;
        border: 1px solid #2a2f44;
        margin-bottom: 10px;
    }
    .stat-num {
        font-size: 1.7rem;
        font-weight: 700;
        color: #8b9eff;
        margin: 0;
    }
    .stat-label {
        color: #8a93a6;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        margin: 0;
    }
    .badge {
        display: inline-block;
        background: #1f2940;
        color: #8b9eff;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    code {
        background: #1a1d29 !important;
        color: #c5d4ff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Helpers ----------
def get_db_tables() -> List[dict]:
    """Return current tables with row counts."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        tables_df: pd.DataFrame = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            conn,
        )
    if tables_df.empty:
        return []

    result: List[dict] = []
    with sqlite3.connect(str(DB_PATH)) as conn:
        for t_name in tables_df["name"].tolist():
            count_df: pd.DataFrame = pd.read_sql(
                f"SELECT COUNT(*) as cnt FROM '{t_name}'", conn
            )
            result.append({"name": t_name, "rows": int(count_df["cnt"].iloc[0])})
    return result


def get_table_schema(table_name: str) -> pd.DataFrame:
    """Return column info for a table."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        return pd.read_sql(f"PRAGMA table_info('{table_name}')", conn)


def get_sample_rows(table_name: str, n: int = 5) -> pd.DataFrame:
    """Return first n rows of a table."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        return pd.read_sql(f"SELECT * FROM '{table_name}' LIMIT {n}", conn)


# ---------- Hero ----------
st.markdown(
    """
    <div class="hero">
        <p class="hero-title">🤖 SQL RAG Assistant</p>
        <p class="hero-sub">
            Your AI data workspace — chat, visualize, and explore.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 📂 Your data")

    uploaded_files = st.file_uploader(
        "Upload 2–3 CSV files",
        type=["csv"],
        accept_multiple_files=True,
        help="Each file becomes a table.",
    )
    if uploaded_files and st.button(
        "🔄 Load CSVs into database",
        use_container_width=True,
        type="primary",
    ):
        with st.spinner("Loading and re-indexing schema…"):
            result = load_csvs_to_db(uploaded_files)
            if result["tables"]:
                st.success(f"✅ Loaded {len(result['tables'])} table(s)")
            for err in result["errors"]:
                st.error(err)
            st.rerun()

    st.divider()
    st.markdown("### 🗄 Current database")
    tables: List[dict] = get_db_tables()
    if tables:
        for t in tables:
            st.markdown(
                f"<span class='badge'>{t['name']}</span> "
                f"<small style='color:#8a93a6'>{t['rows']} rows</small>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No tables found.")

    st.divider()
    if st.button("♻️ Reset to sample data", use_container_width=True):
        with st.spinner("Resetting…"):
            reset_to_sample_database()
            st.success("Reset complete!")
            st.rerun()

    st.divider()
    st.caption("Built with LangChain · Groq · Streamlit")


# ---------- Tabs ----------
tab_chat, tab_dash, tab_schema = st.tabs([
    "💬 SQL Chat",
    "📊 Dashboard",
    "🗄 Schema Explorer",
])


# ============ TAB 1: SQL CHAT ============
with tab_chat:
    st.markdown("### Ask questions in plain English")
    examples: List[str] = [
        "How many customers do we have?",
        "What's the total revenue?",
        "Which city has the most customers?",
        "Top 5 most expensive products?",
    ]
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["pending_question"] = ex

    question: str = st.chat_input("Ask anything about your data…", key="chat_input")
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    if question:
        with st.chat_message("user", avatar="🧑‍💻"):
            st.write(question)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                try:
                    result: dict = ask(question)
                    st.markdown("### 💬 Answer")
                    st.write(result["answer"])
                    with st.expander("🔍 View generated SQL", expanded=False):
                        st.code(result["sql"], language="sql")
                    st.markdown("### 📊 Results")
                    if result["rows"]:
                        df = pd.DataFrame(result["rows"], columns=result["columns"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.caption(f"{len(result['rows'])} row(s) returned")
                    else:
                        st.info("Query returned no rows.")
                except Exception as e:
                    st.error(f"❌ {e}")


# ============ TAB 2: DASHBOARD ============
with tab_dash:
    st.markdown("### 📊 Auto-generate charts from your data")
    st.caption(
        "Ask a question — we'll pick the right chart type and render it."
    )

    dash_examples: List[str] = [
        "Total revenue by category",
        "Top 10 cities by number of customers",
        "Orders per status",
        "Top 5 most expensive products",
    ]
    cols = st.columns(len(dash_examples))
    for i, ex in enumerate(dash_examples):
        if cols[i].button(ex, key=f"dash_ex_{i}", use_container_width=True):
            st.session_state["pending_dash_question"] = ex

    dash_question: str = st.text_input(
        "Ask a question to visualize:",
        key="dash_input",
        placeholder="e.g. Revenue by category",
    )
    if "pending_dash_question" in st.session_state:
        dash_question = st.session_state.pop("pending_dash_question")

    if dash_question:
        with st.spinner("Generating chart…"):
            try:
                result: dict = ask(dash_question)
                if result["rows"]:
                    df = pd.DataFrame(result["rows"], columns=result["columns"])
                    chart_type: str = pick_chart_type(
                        result["columns"], result["rows"]
                    )
                    fig = create_chart(df, chart_type)

                    st.success(f"✨ Rendered as: **{chart_type}** chart")
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander("📋 View data + SQL"):
                        st.code(result["sql"], language="sql")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.warning("Query returned no rows — try another question.")
            except Exception as e:
                st.error(f"❌ {e}")


# ============ TAB 3: SCHEMA EXPLORER ============
with tab_schema:
    st.markdown("### 🗄 Browse your tables")
    if not tables:
        st.info("No tables found. Upload CSVs or reset to sample data.")
    else:
        selected: str = st.selectbox(
            "Select a table:",
            [t["name"] for t in tables],
        )
        if selected:
            schema_df: pd.DataFrame = get_table_schema(selected)
            sample_df: pd.DataFrame = get_sample_rows(selected, n=5)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Schema**")
                st.dataframe(
                    schema_df[["name", "type", "notnull", "dflt_value"]],
                    use_container_width=True,
                    hide_index=True,
                )
            with col_b:
                st.markdown(f"**Sample rows ({len(sample_df)} of many)**")
                st.dataframe(sample_df, use_container_width=True, hide_index=True)

            # Quick stats
            st.markdown("**Quick stats**")
            with sqlite3.connect(str(DB_PATH)) as conn:
                count: int = int(pd.read_sql(
                    f"SELECT COUNT(*) as c FROM '{selected}'", conn
                )["c"].iloc[0])
            st.metric("Total rows", f"{count:,}")