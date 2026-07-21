# FinSight — 4-Day MVP Execution Plan

**Goal:** a live, deployed link showing an agent that answers natural-language questions about Indian stocks — with a hand-built LangGraph agent, generative UI, and cited RAG over real filings. No auth wall, no infra you can't defend in an interview.

---

## Scope Lock

**Hero features (must work on the live link):**
1. Chat interface, streamed responses
2. Hand-built LangGraph agent: `planner → tool_executor → responder`
3. Generative UI, 3 components: `PriceChart`, `AgentTrace`, `FilingExcerpt`
4. RAG over 5–8 seeded real annual reports, with citations
5. Live URL (Vercel + Render + Neon)

**Cut for this build (goes in README as "Roadmap," not silently dropped):**

| Cut | Why |
|---|---|
| Auth (Clerk) | Public demo link, zero login friction. Add later. |
| Verifier node + retry loop | Not demo-visible in 4 days. Stretch goal only. |
| Watchlists, portfolio, alerts | Zero demo value for the time cost |
| Arq worker / background jobs | Seed ingestion runs once via a script; no queue needed |
| Redis caching | Nothing here is under load |
| Docker / docker-compose | Deploying straight to managed services — containerizing local dev just slows you down this week |
| Eval harness, CI/CD, Sentry, OTel, load testing | Real signal, but Phase 3+ work, not MVP |
| `MetricCard`, `ComparisonTable` | 3 components proves the registry pattern; more is more surface area to bug-fix |
| NSE auto-fetch (Path A filings) | Fragile scraper, not worth the risk this week. Upload/seed only. |

---

## Final Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + LangGraph + LangChain (model/tool/embedding wrappers only — see note below) |
| DB | Neon (Postgres + pgvector), no Docker needed |
| LLM | Gemini Flash via `langchain-google-genai` (`ChatGoogleGenerativeAI`) |
| Embeddings | `GoogleGenerativeAIEmbeddings`, `models/text-embedding-004` (768-dim, matches schema) |
| Market data | `yfinance` (`.NS` / `.BO` tickers) |
| PDF parsing | `pdfplumber` |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind |
| Charts | `recharts` |
| Validation | Zod |
| Deploy | Vercel (web) + Render (api) + Neon (db) |

> [!IMPORTANT]
> **LangChain boundary:** Use `ChatGoogleGenerativeAI`, `@tool`, `RecursiveCharacterTextSplitter`, `GoogleGenerativeAIEmbeddings`, and a vectorstore wrapper (`langchain-postgres`'s `PGVector`) for plumbing. Do **not** use `create_react_agent`/`AgentExecutor` or a prebuilt `RetrievalQA` chain — your planner prompt, tool-selection logic, and citation formatting are the parts that need to be yours.

---

## Day 0 — Before You Start (~1 hour)

- [ ] Neon account → new project → copy `DATABASE_URL` → run `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Google AI Studio → get Gemini API key (no card required)
- [ ] GitHub repo created, empty
- [ ] Vercel account, linked to GitHub
- [ ] Render account, linked to GitHub
- [ ] Download 5–8 real annual report PDFs into a local `seed_filings/` folder (Reliance, TCS, Infosys, HDFC Bank, etc. — from each company's own investor-relations page). Open each one and confirm the text is selectable (not scanned images) — a bad seed PDF is a Day 3 problem you can avoid now.

---

## Day 1 — Backend & Agent Core

> **End state:** `curl` a question at your local API, get back a streamed, correct answer with a `PriceChart` block. No frontend yet.

### Project Structure (after Day 1)

```
d:\AI_Analyzer\
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory, CORS, lifespan
│   │   ├── config.py               # pydantic-settings (DATABASE_URL, GOOGLE_API_KEY)
│   │   ├── database.py             # SQLAlchemy async engine + session → Neon
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # Aggregated v1 router
│   │   │       ├── chat.py         # POST /threads, POST /threads/{id}/messages (SSE)
│   │   │       └── health.py       # GET /health
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # SQLAlchemy declarative base
│   │   │   ├── thread.py           # Thread + Message
│   │   │   └── document.py         # Document + DocumentChunk (tables created, used Day 3)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── chat.py             # Pydantic request/response schemas
│   │   ├── services/
│   │   │   └── chat_service.py     # Invokes graph via .astream(), yields SSE events
│   │   └── agent/
│   │       ├── __init__.py
│   │       ├── graph.py            # ✨ StateGraph: planner → tool_executor → responder
│   │       ├── state.py            # AgentState TypedDict
│   │       ├── nodes/
│   │       │   ├── __init__.py
│   │       │   ├── planner.py      # ChatGoogleGenerativeAI + .bind_tools()
│   │       │   ├── tool_executor.py
│   │       │   └── responder.py    # Emits prose + ui_block JSON
│   │       └── tools/
│   │           ├── __init__.py
│   │           ├── stock_price.py  # get_stock_price(ticker, period="1mo")
│   │           ├── financials.py   # get_financials(ticker) — P/E, market cap, etc.
│   │           ├── company_info.py # get_company_info(ticker)
│   │           ├── stock_news.py   # get_stock_news(ticker) — Ticker.news
│   │           └── registry.py     # Tool name → callable map
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── render.yaml                 # Render deploy config
├── frontend/                        # Empty placeholder (Day 2)
├── seed_filings/                    # Annual report PDFs (git-ignored)
├── pnpm-workspace.yaml
├── .env.example
├── .gitignore
└── README.md                        # Stub
```

### Tasks

- [ ] Repo scaffold: `pnpm-workspace.yaml` (lists `backend`, `frontend`), `backend/`, `frontend/` (empty placeholder), `.env.example`, `README.md` stub
- [ ] `backend`: FastAPI app factory (`main.py`), `config.py` via `pydantic-settings` (`DATABASE_URL`, `GOOGLE_API_KEY`)
- [ ] DB models (SQLAlchemy): `Thread`, `Message`, `Document`, `DocumentChunk` — **no `User` table**, no auth for MVP
- [ ] Alembic init + first migration, run against Neon
- [ ] `agent/state.py` — `AgentState` TypedDict (`messages`, `tool_calls`, `tool_results`, `ui_blocks`)
- [ ] Tools in `agent/tools/`, each a LangChain `@tool`:
  - `get_stock_price(ticker, period="1mo")` — current price + historical closes (yfinance `.history()`) for chart data
  - `get_financials(ticker)` — key ratios (P/E, market cap, etc.)
  - `get_company_info(ticker)`
  - `get_stock_news(ticker)` — yfinance `.news`
  - *(Day 3 adds `rag_search`)*
- [ ] `agent/nodes/planner.py` — `ChatGoogleGenerativeAI` with `.bind_tools()`; system prompt carries Indian ticker conventions (`.NS`/`.BO`)
- [ ] `agent/nodes/tool_executor.py` — executes `tool_calls` from the model's response
- [ ] `agent/nodes/responder.py` — final LLM call; system prompt describes the 3 UI components and their prop shapes, model emits `ui_block` JSON alongside prose
- [ ] `agent/graph.py` — `StateGraph`: `START → planner → tool_executor → responder → END`, compiled with `PostgresSaver` pointed at Neon, `recursion_limit=25`
- [ ] `services/chat_service.py` — invokes the graph with `.astream()`, adapts node outputs into SSE-shaped events
- [ ] Routes: `POST /api/v1/threads`, `POST /api/v1/threads/{id}/messages` (returns `text/event-stream` via `StreamingResponse`)

### DB Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,       -- 'user', 'assistant', 'system'
    content TEXT,
    ui_blocks JSONB,                 -- Array of component specs
    tool_trace JSONB,                -- Tool calls, latencies, raw outputs
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,     -- 'seed', 'upload'
    ticker VARCHAR(10),
    title VARCHAR(500),
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    content TEXT,
    section_title VARCHAR(255),
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### Definition of Done

`curl -N` against your local `/api/v1/threads/{id}/messages` endpoint with *"What is Reliance's current stock price and how has it moved this month?"* returns a streamed sequence ending in a real answer with a `PriceChart` `ui_block` containing actual fetched data. Thread/message rows exist in Neon.

---

## Day 2 — Chat UI & Generative UI

> **End state:** open `localhost:3000`, ask a question, watch it stream, see a real chart render, expand a trace panel.

### Tasks

- [ ] `frontend` scaffold: `npx create-next-app@latest . --typescript --app --tailwind`
- [ ] **SSE gotcha:** `EventSource` only supports GET. Your endpoint is POST, so consume the stream with `fetch()` + a `ReadableStream` reader in `hooks/useChat.ts`, not native `EventSource`.
- [ ] `components/generative-ui/schemas.ts` — Zod schemas for `PriceChart`, `AgentTrace`, `FilingExcerpt` props
- [ ] `registry.ts` — component name → React component map
- [ ] `BlockRenderer.tsx` — `safeParse` each incoming `ui_block` against its schema; render the matched component, or a quiet fallback if it doesn't validate. **Never let a malformed block crash the page** — this is worth a line in your README as a design decision.
- [ ] `PriceChart.tsx` — `recharts` line/area chart from the historical-closes data
- [ ] `AgentTrace.tsx` — collapsible panel: planner's plan, each tool call (name, args, latency), from a `tool_trace` field on the message
- [ ] `FilingExcerpt.tsx` — stub with placeholder data (wired to real RAG on Day 3)
- [ ] Chat page: `ChatInput`, `MessageList`, `MessageBubble`, `StreamingMessage`
- [ ] Wire against local backend (`localhost:8000`), test end-to-end

### Zod Schemas

```typescript
import { z } from 'zod';

export const PriceChartSchema = z.object({
  component: z.literal('PriceChart'),
  props: z.object({
    ticker: z.string(),
    companyName: z.string(),
    currentPrice: z.number(),
    currency: z.string().default('INR'),
    change: z.number(),
    changePercent: z.number(),
    data: z.array(z.object({
      date: z.string(),
      close: z.number(),
    })),
  }),
});

export const AgentTraceSchema = z.object({
  component: z.literal('AgentTrace'),
  props: z.object({
    plan: z.string(),
    toolCalls: z.array(z.object({
      tool: z.string(),
      args: z.record(z.unknown()),
      result: z.unknown(),
      latencyMs: z.number(),
    })),
    totalLatencyMs: z.number(),
  }),
});

export const FilingExcerptSchema = z.object({
  component: z.literal('FilingExcerpt'),
  props: z.object({
    documentTitle: z.string(),
    sectionTitle: z.string(),
    content: z.string(),
    ticker: z.string().optional(),
    source: z.string(),
    relevanceScore: z.number().optional(),
  }),
});

export const UIBlockSchema = z.discriminatedUnion('component', [
  PriceChartSchema,
  AgentTraceSchema,
  FilingExcerptSchema,
]);
```

### Definition of Done

Ask *"What is TCS's stock price trend over the past month?"* in the browser → see streamed text + a rendered `PriceChart`. Click "Show trace" → see the planner's reasoning and tool call. Not every question needs a `ui_block` — a P/E or general question answered in clean prose is fine; only price/trend and filing questions trigger a component.

---

## Day 3 — RAG Pipeline

> **End state:** ask a question about a seeded filing, get back a real, cited excerpt.

### Tasks

- [ ] `services/ingestion_service.py` — shared function `ingest_document(file, ticker, title, source)`:
  - Extract text via `pdfplumber`
  - Split via `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=150`; only invest in section-aware splitting if Day 3 has slack)
  - Embed each chunk via `GoogleGenerativeAIEmbeddings`
  - Store in `document_chunks` (via `langchain-postgres`'s `PGVector` wrapper, or raw SQL insert — either is fine)
- [ ] `scripts/seed_documents.py` — one-off script, loops `seed_filings/` folder, calls `ingest_document` for each. Run against **production** Neon connection string so data is live for Day 4.
- [ ] `agent/tools/rag_search.py` — `@tool`: embeds the query, runs a cosine-similarity search over `document_chunks`, returns top-k with citations (document title, ticker, source)
- [ ] Update `registry.py` to include `rag_search`
- [ ] Wire `FilingExcerpt.tsx` to real RAG data (replace Day 2 stub)
- [ ] Update `responder.py`'s system prompt to emit `FilingExcerpt` blocks when RAG results are used
- [ ] **Stretch only, if ahead of schedule:** expose `ingest_document` via `POST /api/v1/documents/upload` (same function, synchronous — no queue needed at this scale) + a simple upload button in the UI. Strong demo moment ("watch me upload a real PDF live") but genuinely optional — seeded data alone tells the full RAG story.

### Definition of Done

Ask *"What did Reliance say about capex plans in their annual report?"* → response includes a `FilingExcerpt` block with real text pulled from the seeded PDF and a correct citation.

---

## Day 4 — Deploy & Harden

> **End state:** a live URL that survives a cold click from a recruiter.

### Tasks

- [ ] Push to GitHub
- [ ] Confirm seed data is in the **production** Neon DB (re-run `seed_documents.py` against prod if you seeded against local/dev on Day 3)
- [ ] **Render**: new Web Service from `backend`, env vars set (`DATABASE_URL`, `GOOGLE_API_KEY`), start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] **Vercel**: import `frontend`, set `NEXT_PUBLIC_API_URL` to the Render URL, deploy
- [ ] Update FastAPI CORS middleware to allow the Vercel domain
- [ ] **Cold-start UX:** Render's free tier spins down after 15 min idle (30–60s cold start). Add a "Waking up the backend…" loading state on first request instead of a silent hang. Ping the Render URL yourself ~5 min before you send the link to anyone.
- [ ] Error-handling pass: invalid ticker, Gemini API failure/rate limit, empty RAG result — each should degrade to a friendly message, never a raw 500 with no UI feedback
- [ ] README: architecture diagram, the "what I built vs. what I used" table, explicit cut list as "Roadmap," setup instructions, live link
- [ ] Rehearse the demo script below **on the deployed link**, not localhost — test it after 20+ minutes idle so you see the real cold-start behavior at least once
- [ ] Remaining hours = bug-fix buffer, not new features

---

## Demo Script (3 questions, ~2 minutes)

1. *"What is Reliance Industries' current stock price and how has it moved over the past month?"* → `PriceChart`
2. *"What did TCS say about revenue growth in their latest annual report?"* → `FilingExcerpt` with citation
3. Click **Show trace** on either response → `AgentTrace` — planner's reasoning, tool calls, latency

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Render cold start reads as "broken" | Pre-ping before sharing the link + explicit "waking up" loading state |
| Gemini free-tier rate limits | Verify current RPM/RPD quota in AI Studio before Day 4; keep pre-demo testing light |
| yfinance occasionally blocked/rate-limited by Yahoo | Test your exact demo tickers a day ahead; don't discover this live |
| pgvector returns irrelevant chunks (dimension mismatch, bad chunking) | Test retrieval quality on Day 3, not Day 4 |
| Scanned/image-only PDF in seed set | Verify text is selectable in each seed PDF during Day 0 |

---

## Known Risk: Render Cold Starts

> [!WARNING]
> Render's free tier spins down after 15 min idle. Cold start = 30–60s. For a recruiter clicking a link cold, this reads as "broken."

**Mitigations (implement all three):**
1. **Frontend loading state**: Detect slow `/health` response → show "Starting up the server (~30s)..." with a progress animation. Makes it look intentional.
2. **Pre-share ping**: Before sending the link to anyone, hit the Render URL to wake it up.
3. **Document it**: In the README, note the tradeoff and the upgrade path ($7/mo Render Starter for always-on).

---

## If You Finish Early

In order of value:
1. **Verifier node** — rule-based numeric check between the response and raw tool output, logged into the trace as pass/fail, no retry loop needed to be useful
2. **`MetricCard` component** for single-value questions (P/E, market cap)
3. **Upload endpoint** if you skipped it on Day 3

---

## Post-MVP Roadmap (README "What I'd Build Next")

Document these explicitly as future phases. They're not cut because they're bad ideas — they're cut because a 4-day sprint can't do them justice.

### Phase 2 — Product Depth (weeks 2–4)
- Auth via Clerk (with ADR: `clerk-vs-jwt-auth.md`)
- Verifier node with retry loop (promote from stretch to default)
- Watchlists + portfolio tracking
- PDF upload (user-uploaded filings, not just seeded)
- NSE filing auto-fetch via NseIndiaApi (with ADR: `unofficial-nse-api-risk.md`)
- `ComparisonTable` + `MetricCard` generative UI components
- Thread persistence + history sidebar

### Phase 3 — Production Grade (weeks 5–7)
- Arq background workers (ingestion, alerts, price refresh)
- Redis caching for yfinance calls
- Agent evaluation harness + CI gating (golden dataset, 85% pass threshold)
- CI/CD pipeline (GitHub Actions)
- Docker Compose for local dev
- OpenTelemetry tracing + Sentry error tracking
- Cost/latency dashboard

### Phase 4 — Enterprise Polish (weeks 8–10)
- Workspaces + RBAC (multi-tenant)
- Earnings call summarization
- PDF report export
- Semantic caching
- Security hardening (rate limiting, prompt injection mitigation)
- Load testing (k6) + documented results
- Architecture Decision Records (continuous)

---

## Verification Checklist (Day 4 sign-off)

- [ ] **Live URL works cold** — click the Vercel link, see the landing page, navigate to chat
- [ ] **Market data flow** — "What's TCS's stock price?" → streamed text + `PriceChart` renders
- [ ] **Financial data flow** — "What's Reliance's P/E ratio?" → streamed text with correct number
- [ ] **RAG flow** — "What did Infosys say about attrition in their annual report?" → `FilingExcerpt` with citation
- [ ] **Agent trace** — click "Show trace" on any response → see planner reasoning + tool calls with latency
- [ ] **Error resilience** — disconnect API, verify frontend shows error state with retry button
- [ ] **Cold start UX** — after 15+ min idle, click link → see "waking up" state → then normal response
- [ ] **README** — has architecture diagram, demo link, "what's cut", "what's next"
