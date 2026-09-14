"""
src/rag_chain.py

The RAG pipeline for the SQL assistant.

This module is the brain of the application. It:
    1. Loads schema documentation (data/schema_docs.txt)
    2. Splits it into chunks
    3. Embeds chunks into a Chroma vector store (in-memory)
    4. Builds a retriever that pulls relevant schema bits per question
    5. Uses the LLM to generate a SQLite query
    6. Generates a natural-language answer from the query results

Public functions:
    generate_sql(question) -> str
    generate_answer(question, columns, rows) -> str
    ask(question) -> dict
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.llm_setup import get_llm
from src.sql_executor import execute_sql

# Where the schema docs live
SCHEMA_DOCS_PATH = Path("data/schema_docs.txt")


# ---------- 1. Load schema docs ----------
def load_schema_docs() -> str:
    """Read the plain-English schema documentation from disk."""
    with open(SCHEMA_DOCS_PATH, "r") as f:
        return f.read()


# ---------- 2. Build the vector store (cached per session) ----------
_vectorstore_cache: Chroma | None = None


def get_vectorstore() -> Chroma:
    """
    Build (or reuse) a Chroma vector store from the schema docs.
    Uses a free local embedding model — no API key needed.

    The cache avoids re-embedding the docs on every question,
    which would be slow.
    """
    global _vectorstore_cache

    if _vectorstore_cache is not None:
        return _vectorstore_cache

    schema_text: str = load_schema_docs()

    # Split the long doc into overlapping chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks: List[str] = splitter.split_text(schema_text)

    # Local embeddings (free, no API).
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    _vectorstore_cache = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        collection_name="schema_docs",
    )
    return _vectorstore_cache


# ---------- 3. SQL generation prompt ----------
SQL_PROMPT = PromptTemplate.from_template("""
You are an expert SQLite query generator. Given the schema documentation
below and a user's question, write a SQLite query that answers it.

Rules:
- Use ONLY tables and columns mentioned in the schema.
- Return ONLY the SQL query — no explanation, no markdown, no code fences.
- For revenue/sales questions, only count orders with status = 'delivered'.
- Use proper JOINs when data spans multiple tables.

Schema documentation:
{schema}

User question: {question}

SQL query:
""")


# ---------- 4. The SQL chain ----------
def build_sql_chain():
    """Build a LangChain chain that turns a question into a SQL string."""
    llm = get_llm()
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {
            "schema": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | SQL_PROMPT
        | llm
        | StrOutputParser()
    )
    return chain


# ---------- 5. Generate SQL ----------
def generate_sql(question: str) -> str:
    """Take a natural-language question and return a SQL string."""
    chain = build_sql_chain()
    sql: str = chain.invoke(question)
    # Clean up: strip whitespace and any stray markdown fences
    sql = sql.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


# ---------- 6. Natural-language answer prompt ----------
ANSWER_PROMPT = PromptTemplate.from_template("""
You are a helpful data analyst assistant.

The user asked: "{question}"

The SQL query returned these results:
{results}

Write a clear, friendly answer to the user's question in 1-2 sentences.
Be conversational and specific. Don't repeat the SQL or column names.
If the result is empty, say so naturally.
""")


# ---------- 7. Generate natural-language answer ----------
def generate_answer(question: str, columns: List[str], rows: List[Tuple]) -> str:
    """
    Take the user's question and SQL result rows, return a friendly
    natural-language answer.
    """
    if not rows:
        results_text: str = "The query returned no results."
    else:
        header: str = " | ".join(columns)
        body_lines: List[str] = [
            " | ".join(str(c) for c in row) for row in rows[:20]
        ]
        results_text = header + "\n" + "\n".join(body_lines)

    llm = get_llm()
    chain = ANSWER_PROMPT | llm | StrOutputParser()
    answer: str = chain.invoke({"question": question, "results": results_text})
    return answer.strip()


# ---------- 8. End-to-end ask ----------
def ask(question: str) -> Dict[str, Any]:
    """
    Full pipeline: question -> SQL -> execute -> natural-language answer.

    Returns a dict with all intermediate results, useful for the UI layer.
    """
    sql: str = generate_sql(question)
    columns, rows = execute_sql(sql)
    answer: str = generate_answer(question, columns, rows)
    return {
        "question": question,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "answer": answer,
    }


# ---------- 9. Self-test ----------
if __name__ == "__main__":
    test_q: str = "How many customers do we have?"
    print(f"Question: {test_q}")
    result = ask(test_q)
    print(f"\nSQL: {result['sql']}")
    print(f"\nRows: {result['rows']}")
    print(f"\nAnswer: {result['answer']}")