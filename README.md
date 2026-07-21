# FinSight

FinSight is a financial research assistant built to answer questions about US and Indian equity markets. It uses a custom AI agent to fetch live data and surface relevant context without hallucinating figures.

This project is a work in progress and serves as a portfolio piece exploring agentic workflows and deterministic UI rendering.

## Features

- **Live Market Data**: Integrates with `yfinance` to pull real-time stock prices, historical trends, and key financial ratios (P/E, Market Cap, EPS) for both US tickers (e.g., AAPL) and Indian tickers (e.g., TCS.NS).
- **Agentic Workflow**: Built with **LangGraph**, the backend utilizes a multi-node architecture (Planner -> Tool Executor -> Responder) to intelligently route queries, call appropriate tools, and generate prose responses.
- **Deterministic UI**: Instead of relying on the LLM to format complex charts or tables in Markdown, the backend traces tool executions and emits structured UI blocks. The Next.js frontend renders these natively as React components (like `PriceChart` and `MetricCard`).
- **Document RAG (Work in Progress)**: Early implementation of Retrieval-Augmented Generation using **pgvector** to search through seeded annual reports and financial filings. When complete, this will allow the agent to pull verifiable, cited excerpts directly from primary sources.

## Tech Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS with a custom editorial-inspired theme
- **Typography**: Playfair Display & Inter

### Backend
- **Framework**: FastAPI
- **Agent Orchestration**: LangGraph & LangChain
- **LLM**: Google Gemini (via `langchain-google-genai`)
- **Database**: PostgreSQL (hosted on Neon) with `pgvector` extension for embeddings
- **Data Source**: `yfinance`

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.10+
- PostgreSQL database (with pgvector enabled)
- Google Gemini API Key

### Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend` folder and add your keys:
   ```env
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   GOOGLE_API_KEY=your_gemini_api_key
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
5. Run database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

## Roadmap

- [ ] Complete the RAG ingestion pipeline for automated document parsing.
- [ ] Add multi-provider LLM fallbacks (Groq, NVIDIA NIM) to handle API rate limits gracefully.
- [ ] Expand tool capabilities for deeper fundamental analysis.

## Disclaimer

*FinSight is an experimental project. It is not intended to provide financial advice. Always verify data independently before making investment decisions.*
