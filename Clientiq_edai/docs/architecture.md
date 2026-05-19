# System Design Document
# ClientIQ — System Architecture

## Overview

ClientIQ is a production-grade enterprise AI platform built on three foundational pillars:

1. **Hybrid RAG** — combines SQL-structured retrieval (TiDB) with dense semantic search (Pinecone)
2. **Multi-Agent Orchestration** — 11 specialised LangGraph agents with shared mutable state
3. **ML Intelligence** — scikit-learn churn prediction, VADER/TextBlob sentiment, knowledge graph extraction

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                  │
│   Browser (HTML/CSS/JS) · Chart.js · Cytoscape.js                   │
│   Pages: Login · Dashboard · Chat · Clients · KG · Analytics · Admin│
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / REST (JWT)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                                 │
│  /api/auth  /api/query  /api/analytics  /api/clients                 │
│  /api/graph  /api/admin                                              │
│  Middleware: CORS · GZip · Request timing · Global error handler     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH STATEGRAPH                               │
│                                                                      │
│  GraphState (TypedDict)  ←── shared mutable state across all agents  │
│                                                                      │
│  Entry: Supervisor                                                   │
│    ↓                                                                 │
│  Compliance Agent  ──── BLOCKED? ──────────────────── ► END         │
│    ↓ CLEARED                                                         │
│  ┌─────────────────────────────────────────────────┐                 │
│  │  Parallel / Sequential based on intent          │                 │
│  │                                                 │                 │
│  │  CRM SQL Agent      Retrieval Agent             │                 │
│  │       ↓                  ↓                      │                 │
│  │  Memory Agent     Sentiment Agent               │                 │
│  │       ↓                  ↓                      │                 │
│  │  Analytics Agent  Risk Agent                    │                 │
│  │       ↓                  ↓                      │                 │
│  │  Knowledge Graph  Recommendation Agent          │                 │
│  └─────────────┬───────────────────────────────────┘                 │
│                ↓                                                      │
│          Citation Agent                                              │
│                ↓                                                      │
│          Final Synthesis (Supervisor)                                │
│                ↓                                                      │
│              END                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│     TiDB (MySQL)        │       │      Pinecone            │
│  Structured CRM data    │       │  Dense vector store      │
│  ─────────────────────  │       │  ─────────────────────── │
│  companies              │       │  Email embeddings        │
│  contacts               │       │  Meeting note embeddings │
│  emails                 │       │  Call transcript vectors │
│  meetings               │       │  Ticket description vecs │
│  call_transcripts       │       │  Contract term vectors   │
│  support_tickets        │       │                          │
│  contracts              │       │  Metadata filtering:     │
│  opportunities          │       │  company_id, source_type │
│  health_snapshots       │       │  date ranges             │
│  kg_entities            │       │                          │
│  kg_relationships       │       │  Cosine similarity       │
│  audit_logs             │       │  top-k retrieval         │
│  agent_sessions         │       │                          │
└─────────────────────────┘       └─────────────────────────┘
              │                                 │
              └────────────────┬────────────────┘
                               ▼
              ┌─────────────────────────────────┐
              │        Mistral AI API            │
              │   Hosted chat completions        │
              │   Model: mistral-small-latest    │
              │   Auth: MISTRAL_API_KEY          │
              └─────────────────────────────────┘
```

---

## Agent Interaction Diagram

```
User Query
    │
    ▼
┌──────────────┐   intent + agent list    ┌───────────────────┐
│  Supervisor  │ ───────────────────────► │  GraphState       │
│  (planner)   │                          │  ─────────────    │
└──────┬───────┘                          │  user_query       │
       │                                  │  intent           │
       ▼                                  │  required_agents  │
┌──────────────┐  ✓ cleared / ✗ blocked  │  sql_results      │
│  Compliance  │ ─── updates state ─────► │  retrieved_chunks │
│  (RBAC gate) │                          │  citations        │
└──────┬───────┘                          │  risk_scores      │
       │                                  │  recommendations  │
       ├──────────────────────────────┐   │  sentiment_*      │
       ▼                              ▼   │  kg_nodes/edges   │
┌──────────────┐            ┌──────────────┐  analytics_data  │
│  CRM SQL     │            │  Retrieval   │  conversation_*  │
│  NL→SQL      │            │  Pinecone    │  compliance_*    │
│  TiDB exec   │            │  hybrid RAG  │  final_response  │
└──────┬───────┘            └──────┬───────┘                  │
       │                           │                           │
       └───────────┬───────────────┘                          │
                   ▼                                           │
          ┌──────────────┐                                     │
          │   Memory     │ ── conversation + entity context ──►│
          └──────┬───────┘                                     │
                 ▼                                             │
       ┌─────────────────────────────────┐                    │
       │  Parallel execution:            │                    │
       │                                 │                    │
       │  Sentiment  Analytics   Risk    │                    │
       │    Agent      Agent     Agent   │                    │
       └──────────────────┬──────────────┘                    │
                          ▼                                    │
                 ┌──────────────┐                             │
                 │ Recommend.   │                             │
                 │  Agent       │                             │
                 └──────┬───────┘                             │
                        ▼                                     │
                 ┌──────────────┐                             │
                 │  KG Agent    │                             │
                 └──────┬───────┘                             │
                        ▼                                     │
                 ┌──────────────┐                             │
                 │  Citation    │ ── citations + confidence ──►│
                 │  Agent       │                             │
                 └──────┬───────┘                             │
                        ▼                                     │
                 ┌──────────────┐   final_response            │
                 │  Supervisor  │ ◄───────────────────────────┘
                 │  (synthesis) │
                 └──────┬───────┘
                        ▼
                   Final Response
```

---

## Data Flow: Hybrid Retrieval

```
User Query: "What issues has Acme Corp raised about API integration?"
                │
                ▼
        ┌───────────────┐
        │   Embedder    │  BGE-small-en-v1.5
        │               │  "Represent for searching: ..."
        └───────┬───────┘
                │ 384-dim vector
                ▼
        ┌───────────────┐
        │    Pinecone   │  Filter: {company_id: "acme-uuid", source_type: ["ticket","email","call"]}
        │    Query      │  top_k=10, min_score=0.30
        └───────┬───────┘
                │ [chunk_id, score, metadata, text]
                ▼
        ┌───────────────┐
        │  SQL Agent    │  SELECT * FROM support_tickets
        │               │  WHERE company_id='acme-uuid'
        └───────┬───────┘  AND category='integration'
                │ structured rows
                ▼
        ┌───────────────┐
        │Context Fusion │  ## Structured CRM Data
        │               │  [Record 1] name=Acme | priority=high | status=open
        │               │
        │               │  ## Retrieved Documents
        │               │  [TICKET] TKT-48291 (relevance: 0.87)
        │               │  "Our webhook events are not being delivered..."
        └───────┬───────┘
                │ fused_context string
                ▼
        ┌───────────────┐
        │  Mistral API  │  System: "You are ClientIQ..."
        │ Hosted model  │  User: query + fused_context
        └───────┬───────┘
                │
                ▼
        Grounded Response + Citations
```

---

## Database Schema (ER Summary)

```
roles ──────────────── users
                          │
              ┌───────────┤
              │           │
          companies ──── opportunities ── contracts
              │
    ┌─────────┼────────────────┬───────────────┐
    │         │                │               │
contacts   emails          meetings      call_transcripts
    │
support_tickets

companies ── health_snapshots
companies ── sentiment_timeline

kg_entities ── kg_relationships

users ── audit_logs
users ── agent_sessions
```

---

## Security Architecture

```
Request
  │
  ▼
CORS Middleware (origin whitelist in production)
  │
  ▼
HTTP Bearer Token extraction
  │
  ▼
JWT decode (HS256, 8h expiry)
  │
  ▼
User lookup → Role fetch
  │
  ▼
Compliance Agent (RBAC + sensitive pattern detection)
  │
  ├─ BLOCKED → 403 with reason + audit log
  │
  └─ CLEARED → agent pipeline
                │
                ▼
          All actions → audit_logs table
```

---

## Deployment Architecture

```
Internet
    │
    ▼
Nginx / Caddy (reverse proxy + TLS termination)
    │
    ├─► :8000  FastAPI  (clientiq-api container)
    │           │
    │           ├─► TiDB    :4000  (tidb container)
    │           ├─► Pinecone        (cloud API)
    │           └─► Mistral AI API  (hosted LLM)
    │
    └─► Static assets served by FastAPI StaticFiles
```

---

## Technology Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangGraph | Stateful graph with conditional routing; superior to simple chains |
| LLM runtime | Mistral AI API | Hosted LLM via `MISTRAL_API_KEY`; no local runtime required |
| Vector DB | Pinecone | Serverless, production-grade, sub-10ms query latency |
| Structured DB | TiDB | MySQL-compatible, distributed, handles large CRM datasets |
| Embeddings | BGE-small-en | High accuracy at 384-dim, fast inference, HuggingFace native |
| Churn model | RandomForest | Interpretable, handles mixed feature types, no scaling needed |
| Sentiment | VADER+TextBlob | Ensemble: rule-based speed + ML accuracy, business text optimised |
| Frontend | Vanilla HTML/JS | No build step, easy to understand, Chart.js + Cytoscape.js for viz |
