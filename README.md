# RepoMind — Agentic GitHub Code Review Copilot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.137-green?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.7-purple?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?style=flat-square&logo=google)
![pgvector](https://img.shields.io/badge/pgvector-0.4.2-blue?style=flat-square&logo=postgresql)
![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat-square)

**An agentic system that reviews GitHub PRs using a 4-node LangGraph pipeline — fetches the diff, retrieves relevant codebase context via pgvector RAG, generates structured feedback via Gemini 2.5 Flash, and posts inline comments automatically.**

[Live Demo](https://repomind-vlry.onrender.com)

</div>

---

## What it does

Open a pull request and RepoMind automatically:

1. **Fetches the diff** via GitHub App API
2. **Indexes your codebase** using AST-based chunking and sentence embeddings stored in pgvector
3. **Retrieves relevant context** — top-5 semantically similar functions from your existing code
4. **Generates a structured review** using Gemini 2.5 Flash with language-specific prompts
5. **Posts the review** as a PR comment within seconds

No manual action. No polling. Fully event-driven via GitHub webhooks.

---

## Architecture

\\\
PR opened on GitHub
        |
        v  webhook (HMAC verified)
+-------------------------------------------------------+
|                 LangGraph StateGraph                  |
|                                                       |
|  +----------+   +----------+   +----------+  +----+  |
|  |  Node 1  |-->|  Node 2  |-->|  Node 3  |->| N4 |  |
|  |  Diff    |   | Context  |   |  Review  |  |Post|  |
|  |  Parser  |   |Retriever |   |Generator |  |    |  |
|  +----------+   +----------+   +----------+  +----+  |
+-------------------------------------------------------+
        |                |               |
   GitHub API      pgvector RAG     Gemini 2.5
                   (Supabase)          Flash
\\\

AgentState flows through all 4 nodes. Each node reads what it needs and writes back its output. No node talks directly to another.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async webhook handling |
| Agent pipeline | LangGraph StateGraph | Retryable nodes, separation of concerns |
| LLM | Gemini 2.5 Flash | Free tier, fast, strong code reasoning |
| RAG chunking | Python ast module | AST-aware splits guarantee complete functions |
| RAG embeddings | fastembed all-MiniLM-L6-v2 | 384-dim vectors, no PyTorch dependency |
| RAG storage | Supabase pgvector | Cosine similarity with ivfflat index |
| GitHub integration | GitHub Apps + PyGithub | Scoped permissions, short-lived tokens |
| Deployment | Docker + Render | Containerized, auto-deploys on push |

---

## Key Engineering Decisions

**Why LangGraph over a function chain?**
Each node has a single responsibility. Nodes are independently retryable. Adding a step is one add_node() + one add_edge() call.

**Why AST chunking over line splits?**
ast.parse() guarantees every chunk is a complete, syntactically valid unit. Line-count splitting could cut a function midway.

**Why fastembed over sentence-transformers?**
sentence-transformers requires PyTorch (2GB+ with CUDA on Linux). fastembed uses ONNX runtime — same vectors, 10x smaller footprint.

**Why GitHub App over Personal Access Token?**
GitHub Apps have scoped permissions, generate short-lived tokens via JWT exchange, and act as a separate bot identity.

---

## RAG in action

RepoMind proved codebase-aware reviews: when a new percentage() function was added, Gemini identified it had the same zero-division bug as the existing divide() function in calculator.py — knowledge only possible through RAG retrieval.

---

## Project Structure

\\\
repomind/
+-- app/
|   +-- main.py              # FastAPI entry point
|   +-- webhook_handler.py   # Webhook verification, pipeline invocation
|   +-- pipeline.py          # LangGraph StateGraph, 4 nodes, AgentState
|   +-- github_client.py     # GitHub App auth, diff fetch, comment post
|   +-- gemini_reviewer.py   # Prompt engineering, language detection
|   +-- chunker.py           # AST-based code chunking
|   +-- embedder.py          # fastembed vectors, pgvector storage
+-- Dockerfile
+-- requirements.txt
\\\

---

## Local Setup

\\\ash
git clone https://github.com/Sarishti845/RepoMind.git
cd RepoMind
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Create .env with:
# GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH, GITHUB_WEBHOOK_SECRET
# DATABASE_URL, GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000
ngrok http 8000
\\\

---

## Built by

**Sarishti** — Final year B.Tech CSE, TIET (CGPA 9.50)
Amazon ML Summer School 2024 (top 3,000 from 80,000 applicants)

Built end-to-end as a solo project.
