![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-19%2B-61DAFB?style=for-the-badge&logo=react)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-blueviolet?style=for-the-badge)
![Mistral AI](https://img.shields.io/badge/LLM-Mistral%20AI-FF7000?style=for-the-badge)
![TiDB](https://img.shields.io/badge/Database-TiDB-red?style=for-the-badge)
![Pinecone](https://img.shields.io/badge/VectorDB-Pinecone-00B388?style=for-the-badge)
![RAG](https://img.shields.io/badge/Architecture-Hybrid%20RAG-orange?style=for-the-badge)
![GitHub](https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github)

---

# 🧠 ClientIQ — Enterprise Multi-Agent CRM Intelligence Platform

A full-stack *AI-powered CRM intelligence platform* built with *Python* and *React* that enables enterprise teams to query, analyse, and act on customer relationship data through natural language. The system orchestrates **11 specialised LangGraph agents** over a **Hybrid RAG** pipeline — combining semantic vector search, structured SQL queries, sentiment analysis, churn prediction, and knowledge graph construction — all served through a FastAPI backend and interactive browser dashboard.

---

## ✨ Key Features

### 🤖 Multi-Agent Orchestration (LangGraph)
- 🧭 **Supervisor Agent:** Classifies user intent, plans agent pipelines, and synthesises final coherent responses from all agent outputs.
- 🗄️ **CRM SQL Agent:** Translates natural-language questions into SQL queries, executes them against TiDB, and returns structured results.
- 🔍 **Retrieval Agent:** Performs hybrid RAG — semantic Pinecone vector search fused with SQL metadata filtering for ranked, deduplicated context chunks.
- 📌 **Citation Agent:** Builds structured source citations with relevance scores and rolls up an overall confidence score per query.
- 🧠 **Memory Agent:** Maintains conversational memory across turns, compresses long histories, and injects entity context into retrieval.
- 😊 **Sentiment Agent:** Detects sentiment, emotion signals, and dissatisfaction patterns from CRM communications using VADER and LLM analysis.
- 📊 **Analytics Agent:** Computes KPIs, revenue metrics (MRR/ARR), client health distributions, churn risk summaries, and SLA stats.
- ⚠️ **Risk Agent:** Predicts churn probability and renewal risk using scikit-learn ML models trained on CRM signals and engagement metrics.
- 💡 **Recommendation Agent:** Generates next-best-action recommendations, sales opportunity triggers, and communication strategy suggestions.
- 🕸️ **Knowledge Graph Agent:** Extracts entities and relationships from retrieved text, builds a NetworkX graph, and serves Cytoscape.js-compatible data.
- 🔒 **Compliance Agent:** Enforces RBAC policies, filters sensitive PII fields, and validates governance rules before any query proceeds.

### 🔍 Hybrid RAG Pipeline
- 🧲 **Semantic Search:** Pinecone vector database for high-relevance document retrieval across emails, calls, contracts, and meeting transcripts.
- 🗃️ **Structured SQL Retrieval:** Direct TiDB queries over a rich CRM schema covering companies, contacts, opportunities, contracts, support tickets, and communications.
- 🔀 **Context Fusion:** Merges and re-ranks semantic and SQL results into a unified, high-confidence context window for LLM synthesis.

### 🔒 Security & Compliance
- 🛡️ **RBAC Permissions Matrix:** Role-based access control across `admin`, `manager`, and `analyst` tiers, governing access to financials, PII, contracts, audit logs, and data exports.
- 🔑 **JWT Authentication:** Secure login, token refresh, and user profile endpoints with audit trail logging.
- 📋 **Query Audit Logging:** Every agent invocation and data access is logged with user, role, timestamp, and outcome.

### 📊 Analytics & Risk Intelligence
- 💰 **Revenue Dashboards:** MRR, ARR, pipeline value, and account-tier breakdowns surfaced via the analytics API.
- 🚨 **Churn Prediction:** ML-powered churn probability scores per client with key risk factors and renewal timeline alerts.
- 📈 **Sentiment Timelines:** Per-company sentiment trends across emails, meetings, and support tickets over configurable time windows.
- 🏥 **Client Health Snapshots:** Composite health scores with history, stored and queryable for trend analysis.

### 🕸️ Knowledge Graph
- 🔎 **Entity Extraction:** LLM-driven extraction of companies, contacts, products, topics, risks, and events from unstructured text.
- 🏗️ **Graph Construction:** NetworkX graph built from retrieved chunks, exported as Cytoscape.js JSON for interactive browser visualisation.
- 🔗 **Relationship Mapping:** Bidirectional edges connecting entities across communication touchpoints, enabling relationship-level querying.

### 🌐 REST API (FastAPI)
- 🔑 **`/api/auth`** — Login, token refresh, and user profile management.
- 🤖 **`/api/query`** — Main AI query endpoint: routes through the full LangGraph agent pipeline.
- 📊 **`/api/analytics`** — KPIs, revenue metrics, churn summaries, and sentiment timelines.
- 👥 **`/api/clients`** — Company profiles, contact lists, meetings, contracts, and support tickets.
- 🕸️ **`/api/graph`** — Knowledge graph retrieval with optional company scoping.
- 🛡️ **`/api/admin`** — Audit logs, user management, and system health for admin panels.
- 💚 **`/api/health`** — Live database and LLM connectivity status check.

---

## 📂 Project Structure

```plaintext
Clientiq_edai/
├── 📂 backend/
│   ├── 📂 agents/
│   │   ├── 🧭 supervisor.py
│   │   ├── 🔒 compliance_agent.py
│   │   ├── 🗄️ crm_sql_agent.py
│   │   ├── 🔍 retrieval_agent.py
│   │   ├── 📌 citation_agent.py
│   │   ├── 🧠 memory_agent.py
│   │   ├── 😊 sentiment_agent.py
│   │   ├── 📊 analytics_agent.py
│   │   ├── ⚠️ risk_agent.py
│   │   ├── 💡 recommendation_agent.py
│   │   ├── 🕸️ knowledge_graph_agent.py
│   │   └── 📦 __init__.py
│   └── 📂 api/
│       ├── 🚀 main.py
│       ├── 🔑 routes_auth.py
│       ├── 🤖 routes_query.py
│       ├── 📊 routes_analytics.py
│       ├── 👥 routes_clients.py
│       ├── 🕸️ routes_graph.py
│       └── 🛡️ routes_admin.py
├── ⚙️ .env.example
└── 🚫 .gitignore
```

---

## 🛠️ Tech Stack

**🐍 Backend / Core:**
- 🔤 Language: Python 3.8+
- ⚡ Web Framework: FastAPI + Uvicorn
- 🕹️ Agent Orchestration: LangGraph (multi-agent workflow)
- 🤖 LLM Provider: Mistral AI (`mistral-small-latest`)

**🗄️ Data Layer:**
- 🐬 Relational Database: TiDB (MySQL-compatible, distributed)
- 🌲 Vector Database: Pinecone (semantic similarity search)
- 🔧 ORM: SQLAlchemy (async)

**🧪 ML & NLP:**
- 📉 Churn Prediction: scikit-learn (`ChurnPredictor`)
- 💬 Sentiment Analysis: VADER + Mistral LLM
- 🕸️ Knowledge Graph: NetworkX + Cytoscape.js

**🖥️ Frontend:**
- ⚛️ UI Framework: React 19 (Vite)
- 🔵 Graph Visualisation: Cytoscape.js
- 📊 Charts: Recharts

---

## ⚙️ How to Run Locally

**📥 Clone the repository**
```bash
git clone https://github.com/your-username/clientiq.git
cd clientiq/Clientiq_edai
```

**🐍 Set up Python environment**
```bash
python -m venv myenv
source myenv/bin/activate        # On Windows: myenv\Scripts\activate
pip install fastapi uvicorn sqlalchemy pinecone-client langchain langgraph mistralai scikit-learn vaderSentiment networkx
```

**🔐 Configure environment variables**
```bash
cp .env.example .env
# Fill in your TiDB, Pinecone, and Mistral AI credentials in .env
```

**🚀 Start the FastAPI backend**
```bash
uvicorn backend.api.main:app --reload --port 8000
```

**⚛️ Launch the React frontend**
```bash
cd frontend
npm install
npm run dev
```

Open 🌐 `http://localhost:5173` in your browser. API docs are available at 📖 `http://localhost:8000/api/docs`.

---

## 🚀 Usage Guide

1. 🔑 **Authenticate** — Log in via `/api/auth/login` to receive a JWT token. Your role (`admin`, `manager`, `analyst`) determines which data you can access.
2. 💬 **Query** — Send natural-language questions to `/api/query`. The Supervisor Agent plans which of the 11 agents to invoke, executes the pipeline, and returns a synthesised answer with citations.
3. 👥 **Explore Clients** — Browse company profiles, contacts, meetings, contracts, and support tickets through the `/api/clients` endpoints.
4. 📊 **View Analytics** — Pull KPI dashboards, churn risk summaries, sentiment timelines, and revenue trends from `/api/analytics`.
5. 🕸️ **Inspect the Knowledge Graph** — Retrieve entity-relationship graphs for any company from `/api/graph` and render them in the browser with Cytoscape.js.
6. 🛡️ **Administer** — Manage users, review audit logs, and monitor system health from `/api/admin` (admin role required).

---

## 🤖 Agent Overview

| 🤖 Agent | 🎯 Role | ⚡ Key Capability |
|---|---|---|
| 🧭 Supervisor | Orchestrator | Intent classification & response synthesis |
| 🔒 Compliance | Gatekeeper | RBAC enforcement & PII filtering |
| 🗄️ CRM SQL | Data Retrieval | NL-to-SQL over TiDB CRM schema |
| 🔍 Retrieval | Hybrid RAG | Pinecone semantic search + SQL fusion |
| 📌 Citation | Attribution | Source citations & confidence scoring |
| 🧠 Memory | Context | Conversational memory & entity tracking |
| 😊 Sentiment | NLP | Emotion detection & dissatisfaction signals |
| 📊 Analytics | BI | KPIs, revenue metrics, SLA stats |
| ⚠️ Risk | ML | Churn probability & renewal risk prediction |
| 💡 Recommendation | Actions | Next-best-action & sales playbooks |
| 🕸️ Knowledge Graph | Graph AI | Entity extraction & relationship mapping |

---

## 🗄️ CRM Database Schema

| 📋 Table | 🔑 Key Fields |
|---|---|
| 🏢 `companies` | name, industry, annual_revenue, health_score, churn_risk |
| 👤 `contacts` | company_id, email, job_title, sentiment_score, last_contacted |
| 🎯 `opportunities` | company_id, stage, amount, probability, close_date |
| 📝 `contracts` | company_id, contract_type, value, start_date, end_date, status |
| 📧 `emails` | company_id, direction, subject, sentiment_score, sent_at |
| 🤝 `meetings` | company_id, meeting_type, duration_mins, sentiment_score |
| 📞 `call_transcripts` | company_id, call_type, duration_secs, sentiment_score |
| 🎫 `support_tickets` | company_id, priority, status, first_response_hrs, resolution_hrs |

---

## 📄 License
This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.
