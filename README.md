# sql-rag-assistant
AI-powered SQL assistant using RAG — ask questions in plain English, get SQL + answers
# 🤖 SQL RAG Assistant

Ask questions in plain English. Get SQL + answers + charts — instantly.

Built with **LangChain**, **Groq**, **Streamlit**, and **ChromaDB**.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

- 💬 **Natural-language to SQL** — ask questions, get accurate SQLite queries
- 📊 **Auto-generated dashboards** — type a question, get a chart
- 🗄 **Schema explorer** — browse tables, see column types and sample data
- 📁 **Upload your own CSVs** — any CSV becomes a queryable table
- 🛡️ **Read-only by design** — destructive queries (DROP, DELETE, etc.) are blocked
- ⚡ **Free-tier friendly** — runs on Groq's free LLM API

## 🚀 Live Demo

[Coming soon — deploy on Streamlit Cloud]

## 🛠 Tech Stack

- **LLM**: Groq (Llama 3.1 8B Instant)
- **Framework**: LangChain + RAG (Retrieval-Augmented Generation)
- **Vector DB**: ChromaDB (in-memory)
- **Embeddings**: sentence-transformers (local, free)
- **Database**: SQLite
- **UI**: Streamlit
- **Charts**: Plotly

## 🏗 Architecture
User question ↓ [Streamlit UI] ↓ [RAG Pipeline] ├─→ ChromaDB (retrieves relevant schema chunks) └─→ Groq LLM (generates SQL) ↓ [SQL Executor] ├─→ Safety check (blocks DROP/DELETE/etc.) └─→ Runs against SQLite ↓ [Natural Language Answer] └─→ Groq LLM (interprets results) ↓ [Dashboard Generator] → Plotly chart (if asked) ↓ Display: Answer + SQL + Table + Chart
text

## 💻 Run Locally 1. Clone this repo 2. Get a free API key at [console.groq.com](https://console.groq.com) 3. Create `.env` file: `GROQ_API_KEY=your_key_here` 4. Install dependencies: `pip install -r requirements.txt` 5. Create sample database: `python -m src.database` 6. Launch: `streamlit run app.py` ## 🧪 Try These Questions - *"What's the total revenue from delivered orders?"* - *"Top 5 customers by total spending"* - *"Which city has the most customers?"* - *"Most popular product category"* ## 📁 Project Structure

sql-rag-assistant/ ├── app.py # Streamlit UI ├── src/ │ ├── database.py # SQLite + sample data │ ├── llm_setup.py # LLM configuration │ ├── rag_chain.py # RAG pipeline (SQL generation) │ ├── sql_executor.py # Safe SQL execution │ ├── dashboard.py # Chart generation │ └── csv_loader.py # CSV upload handling ├── data/ │ ├── sample.db # SQLite database │ └── schema_docs.txt # Schema for RAG ├── tests/ # Unit tests ├── docs/ # Documentation ├── requirements.txt # Dependencies ├── .env.example # API key template ├── .gitignore ├── .devcontainer/ # GitHub Codespaces config └── README.md
text

## 🔒 Security This assistant is **read-only by design**. The SQL executor: - Only allows SELECT and WITH queries - Blocks DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, REPLACE - Detects stacked statements - Detects comment-based attacks (`--`, `/* */`) Even if the LLM hallucinates a destructive query, it cannot execute. ## 📝 License MIT
