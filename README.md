# FinSight

**An agentic financial research assistant covering US and Indian stock markets.**
A hand-built LangGraph agent (not a prebuilt chain) combining live market data with cited retrieval over real annual reports, streamed to a chat interface.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-custom%20agent-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)](https://neon.tech/)
[![License](https://img.shields.io/badge/status-active%20development-yellow)]()

🔗 **Live demo:** _add your Vercel URL here_
🔗 **API health check:** _add your Render URL here_ `/api/v1/health`

> **Status:** Backend (agent, tools, RAG pipeline, streaming API) is built and verified end-to-end. Frontend is specced — see [Known Limitations](#known-limitations--not-yet-implemented) for current implementation status.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Design Decisions Worth Noting](#design-decisions-worth-noting)
- [Known Limitations](#known-limitations--not-yet-implemented)
- [Roadmap](#roadmap)

---

## Overview

FinSight answers natural-language questions about US and Indian equities by reasoning over live market data and cited excerpts from real annual reports — not by prompting a generic chatbot with a system message. The agent graph, tool orchestration, and UI-payload construction are all hand-written; LangChain is used only for its model/tool/embedding wrapper interfaces, not as an off-the-shelf agent framework.

**At a glance:**
- 3-node LangGraph agent (planner → tool executor → responder), written from scratch
- 4 live market-data tools across US and Indian (NSE/BSE) exchanges via `yfinance`
- RAG over real annual filings — pgvector cosine retrieval with cited, relevance-scored excerpts
- SSE-streamed chat responses with structured, deterministically-built UI payloads
- A custom bidirectional WebSocket layer for live document-ingestion progress and mid-flight cancellation

---

## Architecture

### 1. The Agent (LangGraph)

A 3-node graph, written from scratch — not `create_react_agent` or a prebuilt `AgentExecutor`:

| Node | Responsibility |
|---|---|
| **Planner** | Decides which tools to call; normalizes tickers (`.NS`/`.BO` for Indian exchanges, no suffix for US tickers) |
| **Tool Executor** | Runs the planner's tool calls; catches per-tool failures into an error field instead of crashing the graph |
| **Responder** | Writes final prose from tool outputs only — the LLM never writes UI JSON. Deterministic Python code builds the `ui_block` payloads from tool results |

### 2. Live Market Data

Four tools, all backed by `yfinance`, covering both markets:

| Tool | Returns |
|---|---|
| `get_stock_price` | Current price + historical closes |
| `get_financials` | P/E, market cap, EPS, dividend yield, 52-week high/low |
| `get_company_info` | Sector, industry, business summary |
| `get_stock_news` | Recent headlines |

### 3. RAG Pipeline

- PDF ingestion via `pdfplumber`, chunked with `RecursiveCharacterTextSplitter`
- **Keyword pre-filtering** — drops pages that don't match financial-relevance terms (e.g. "management discussion," "risk factors," "capex") before chunking. Observed reduction: 0.6%–13.5% on seeded filings — varies by document structure; main cost/time savings come from batching and embedding fewer low-value pages, not a fixed universal percentage.
- **Embeddings** — HuggingFace Inference API, `BAAI/bge-base-en-v1.5` (768-dim, matches the `vector(768)` schema exactly — ingestion and query-time embedding use the identical model, required for valid cosine similarity)
- **Vector store** — PostgreSQL + pgvector on Neon, HNSW index (`vector_cosine_ops`) on `document_chunks.embedding`
- **Rate-limit resilience** — batched embedding calls with exponential backoff/retry on 429s and transient provider errors

### 4. Streaming API

FastAPI + `StreamingResponse` over SSE. Each chat turn emits, in order:

`status` (planning started) → zero or more `tool_call` events → `token` (complete prose) → zero or more `ui_block` events → `done`


The streaming endpoint opens its own DB session directly via `async_session_maker` rather than FastAPI's `Depends(get_db)`, since the latter tears down before a `StreamingResponse` finishes sending.

### 5. WebSockets — used where the protocol is actually required

- **Document ingestion** (`/api/v1/ws/documents/{id}`) — a custom, bidirectional WebSocket streams live pipeline-phase progress (extraction → filtering → chunking → embedding) and supports client-initiated cancellation of the running background task mid-ingestion. This is real two-way traffic, not one-way push — the client can send `{"action": "cancel"}` and the server acts on it immediately.
- **Finnhub integration** — the backend-to-Finnhub connection uses WebSockets because Finnhub's API is WebSocket-native; this is an upstream integration requirement, not a protocol choice made for its own sake.

---

## Tech Stack

**Backend (implemented & tested)**

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Agent | LangGraph + LangChain (wrappers only — planner logic, tool selection, and UI-block construction are hand-written) |
| Chat LLM | Groq (`llama-3.3-70b-versatile`) |
| Embeddings | HuggingFace Inference API (`BAAI/bge-base-en-v1.5`) |
| Database | PostgreSQL (Neon) + pgvector + SQLAlchemy (async) + Alembic |
| Document processing | `pdfplumber` |

**Frontend (spec complete — see status note above)**

| Layer | Technology |
|---|---|
| Framework | Next.js (App Router) + TypeScript + Tailwind — planned |
| Charts | recharts (`PriceChart`) |
| Validation | Zod-validated `ui_block` discriminated union |

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- A Neon Postgres database with the `vector` extension enabled
- API keys: Groq and HuggingFace (Inference-scoped token — the plain "Read" preset is not sufficient; use the "Inference" preset or a fine-grained token with "Make calls to Inference Providers" enabled)

### Backend

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://user:pass@ep-host.aws.neon.tech/neondb?sslmode=require
GROQ_API_KEY=gsk_your_groq_key
HUGGINGFACE_API_KEY=hf_your_hf_key
```

Run migrations:

```bash
alembic upgrade head
```

Start the server:

```bash
uvicorn app.main:app --reload
```

### Verifying the backend works

```bash
curl -s -X POST http://localhost:8000/api/v1/threads
# then, using the returned thread_id:
curl -N -X POST http://localhost:8000/api/v1/threads/{thread_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is Apple'\''s current stock price?"}'
```

Expect a stream ending in `event: done`, with a `PriceChart` `ui_block` containing real fetched data.

### Seeding the RAG database

1. Place PDF annual reports in `seed_filings/` (repo root)
2. Run:
```bash
   cd backend
   python -m scripts.seed_documents
```

This embeds each filing in batches with retry/backoff on rate limits. For large filings (300+ pages), expect this to take several minutes — the script logs per-batch progress.

> **Important:** if you change the embedding model or provider, existing `document_chunks` rows are in a different vector space and must be cleared before re-seeding:
> ```sql
> DELETE FROM document_chunks;
> DELETE FROM documents;
> ```

---

## Design Decisions Worth Noting

- **UI generation is deterministic, not model-written.** The LLM writes prose; a Python function (`_build_ui_blocks`) inspects verified tool output and constructs the `ui_block` JSON. Deliberate choice to keep structured UI payloads reliable regardless of which LLM is orchestrating.
- **Provider migration:** originally built on Gemini for both chat and embeddings. Migrated to Groq (chat) and HuggingFace (embeddings) after repeated free-tier quota/auth friction during development. The two are fully decoupled — LangChain's `bind_tools()` abstraction and the async embeddings interface meant swapping providers touched only the instantiation code, not the agent graph or ingestion logic.
- **Model-specific formatting drift:** switching chat providers surfaced that not all models honor "no markdown" instructions equally reliably (Gemini complied consistently; Llama-3.3 via Groq occasionally leaked markdown tables/bold syntax). Mitigated with a stricter system prompt plus a server-side markdown-stripping safety net, rather than relying on prompt compliance alone.

---

## Known Limitations / Not Yet Implemented

- **Frontend:** spec and component design complete; Next.js implementation status should be confirmed/updated here once built.
- **In-chat PDF upload:** the `POST /api/v1/documents/upload` backend endpoint exists; a frontend upload control that auto-triggers analysis after upload has been designed but not yet confirmed wired end-to-end.
- **Ingestion resumability:** the seed script retries within a batch on failure, but does not currently skip already-completed documents on a re-run — a killed run needs to be restarted from the top (or resumed manually by editing the PDF list).
- **DB connection resilience:** no `pool_pre_ping`/`pool_recycle` configured yet — worth adding given Neon's scale-to-zero behavior, but not yet done.
- **`MetricCard` / `ComparisonTable` components:** intentionally cut from MVP scope. The generative-UI registry currently implements `StockOverview`, `ResearchCard`, `MarketBrief`, `PriceChart`, `AgentTrace`, and `FilingExcerpt`.
- **Auth:** none — public demo, zero login friction, by design for this phase.

---

## Roadmap

- Verifier node (rule-based numeric sanity check between tool output and response, logged into trace)
- `MetricCard` for single-value questions (P/E, market cap)
- Auth (Clerk) if/when moving beyond public-demo scope
- Ingestion resumability + connection-pool hardening