# FinSight: Agentic Financial Research Platform

FinSight is a powerful, AI-driven financial research assistant built with a modern LangGraph agent architecture. It is designed to analyze Indian and US stock markets, combining live market data (via `yfinance`) with deep qualitative analysis (RAG over annual reports) into a single, seamless, streaming chat interface.

---

## 🏗 Architecture

### 1. The Agent (LangGraph)
The core of FinSight is a multi-node LangGraph agent designed to prevent hallucination and improve reasoning:
- **Planner Node**: Interprets user intent, handles ticker normalization (.NS for India), and orchestrates tool calls. It does *not* write the final response.
- **Tool Execution**: Resolves live API calls and vector database searches.
- **Responder Node**: Synthesizes the raw tool outputs into a polished, financial analyst-style prose response. It guarantees that any numbers cited come directly from the tools.

### 2. Live Data & RAG
- **Live Market Data**: Integrates with Yahoo Finance to pull real-time stock prices, P/E ratios, EPS, market caps, and 52-week highs/lows.
- **RAG Pipeline (Retrieval-Augmented Generation)**:
  - Supports large PDF annual reports and filings.
  - **Smart Filtering**: Pre-filters pages based on financial keywords (e.g., "Management Discussion", "Capex", "Risk Factors") to drop boilerplate and reduce embedding costs by ~70%.
  - **Embeddings**: Uses HuggingFace's Inference API (`BAAI/bge-base-en-v1.5`) to map chunks into 768-dimensional vectors.
  - **Vector DB**: PostgreSQL with `pgvector` hosted on Neon Serverless Postgres.

### 3. Real-Time Streaming
- **Backend (FastAPI)**: Uses a custom Server-Sent Events (SSE) protocol to stream intermediate state.
- **Frontend (Next.js)**: Consumes the SSE stream to display live tool-call badges (e.g., "Fetching TCS financials..."), rich UI components (Metric Cards, Filing Excerpts), and streaming prose simultaneously.

---

## 🚀 Tech Stack

**Frontend:**
- Next.js 15 (React 19)
- TailwindCSS (Premium, whitespace-heavy editorial design)
- Custom SSE client (`src/lib/sse.ts`)

**Backend:**
- FastAPI & Uvicorn
- LangGraph & LangChain
- Groq (LLM provider)
- HuggingFace (Embeddings provider)
- PostgreSQL (Neon) with `pgvector` & SQLAlchemy
- Alembic (Migrations)
- `pdfplumber` (Document extraction)

---

## 🛠 Setup & Installation

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- A [Neon Postgres](https://neon.tech/) database URL.
- API Keys for **Groq** and **HuggingFace**.

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql://user:pass@ep-host.aws.neon.tech/neondb?sslmode=require
GROQ_API_KEY=gsk_your_groq_key
HUGGINGFACE_API_KEY=hf_your_hf_key
```

Run database migrations to initialize tables and `pgvector`:
```bash
alembic upgrade head
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

*(No `.env` is strictly required for the frontend if running locally on port 3000, as it defaults to `http://localhost:8000`)*.

---

## 🏃‍♂️ Running the Application

Start the backend:
```bash
cd backend
uvicorn app.main:app --reload
```

Start the frontend:
```bash
cd frontend
npm run dev
```
Navigate to `http://localhost:3000` to use the application.

---

## 📚 Seeding the RAG Database

To chat about company-specific strategic insights, you must first ingest their annual reports.

1. Place PDF reports in a directory (e.g., `seed_filings/`).
2. Run the ingestion script:
```bash
cd backend
python -m scripts.seed_documents
```

**Features of the ingestion script:**
- **Rate-limit resilient**: Automatically batches requests and uses exponential backoff.
- **Idempotent**: Safe to re-run. It will skip previously completed documents and resume/retry failed ones.
- **Optimized**: Drops pages that don't match critical financial keywords before embedding.

---

## 💡 Key Design Philosophies

- **No Placeholders**: If the agent needs to show a metric card, it streams a tool block and the UI renders a rich React component natively, completely avoiding markdown table hallucinations.
- **Fail Gracefully**: If a provider rate-limits or a tool fails, the agent surfaces the error cleanly in the UI and continues the conversation.
- **Serverless-Ready**: Includes SQLAlchemy `pool_pre_ping=True` and `pool_recycle` to safely survive Neon scale-to-zero connection drops.

---

## 🚀 Future Improvements

- **Deeper Fundamental Analysis**: Expand tool capabilities to retrieve and process a wider array of fundamental metrics and historical financial statements.
- **Investment Frameworks**: Introduce multiple analysis lenses (Value, Growth, Quality, etc.) based on publicly documented investment methodologies.
- **Advanced RAG Optimization**: Further refine ingestion for massive financial filings through even smarter section filtering, hierarchical chunking, and semantic routing.
- **Valuation Sandbox**: Build an interactive UI module with configurable financial assumptions (WACC, terminal growth) for live, agent-assisted fair-value estimation.
- **Market Dashboard**: Add a lightweight, cached homepage dashboard displaying real-time market indices, sector performance, and top movers.
