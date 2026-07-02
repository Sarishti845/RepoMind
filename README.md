# RepoMind — Agentic GitHub Code Review Copilot

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.137-green?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.7-purple?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange?style=flat-square&logo=google)
![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat-square)

> An agentic system that reviews GitHub PRs using a 4-node LangGraph pipeline — fetches the diff, retrieves relevant codebase context via pgvector RAG, generates structured feedback via Gemini 2.5 Flash, and posts inline comments automatically.

**Live:** https://repomind-vlry.onrender.com

---

## What it does

Open a pull request and RepoMind automatically:

1. **Fetches the diff** via GitHub App API
2. **Indexes your codebase** using AST-based chunking and embeddings stored in pgvector
3. **Retrieves relevant context** — top-5 semantically similar functions from your existing code
4. **Generates a structured review** using Gemini 2.5 Flash with language-specific prompts
5. **Posts the review** as a PR comment within seconds

No manual action. No polling. Fully event-driven via GitHub webhooks.

---

## Architecture
PR opened on GitHub
|
v  webhook (HMAC verified)
+--------------------------------------------------+
|              LangGraph StateGraph                |
|                                                  |
|  [Node 1]    [Node 2]     [Node 3]   [Node 4]   |
|  Diff    --> Context  --> Review --> Comment     |
|  Parser      Retriever    Generator  Poster      |
+--------------------------------------------------+
|              |            |
GitHub API    pgvector RAG   Gemini 2.5
(Supabase)       Flash

AgentState flows through all 4 nodes — each node reads what it needs and writes back its output only.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async webhook handling |
| Agent pipeline | LangGraph StateGraph | Retryable nodes, clean separation of concerns |
| LLM | Gemini 2.5 Flash | Free tier, fast, strong code reasoning |
| RAG chunking | Python `ast` module | Guarantees complete function/class units |
| RAG embeddings | fastembed (all-MiniLM-L6-v2) | 384-dim vectors, no PyTorch dependency |
| RAG storage | Supabase pgvector | Cosine similarity with ivfflat index |
| GitHub integration | GitHub Apps + PyGithub | Scoped permissions, short-lived tokens |
| Deployment | Docker + Render | Containerized, auto-deploys on push |

---

## Key Engineering Decisions

**Why LangGraph over a plain function chain?**
Each node owns one responsibility. Nodes are independently retryable — if Gemini fails, only Node 3 retries without re-fetching the diff. Adding a new step is one `add_node()` + `add_edge()` call.

**Why AST chunking over line splits?**
`ast.parse()` guarantees every chunk is a complete, syntactically valid unit. Splitting by line count could cut a function in half, producing meaningless embeddings.

**Why fastembed over sentence-transformers?**
`sentence-transformers` pulls in PyTorch — 2GB+ with CUDA on Linux. `fastembed` uses ONNX runtime, produces identical 384-dim vectors, and fits in Render's free tier.

**Why GitHub App over a Personal Access Token?**
GitHub Apps have scoped per-installation permissions, generate short-lived tokens via JWT exchange, and act as a separate bot identity not tied to any personal account.

---

## RAG in action

When a new `percentage()` function was added in a PR, Gemini identified it had the same zero-division bug as the existing `divide()` function in `calculator.py` — knowledge only possible because `divide()` was retrieved from pgvector and injected into the prompt.

---

## Real bugs caught

On a single PR, RepoMind automatically caught:

- SQL injection in `get_user()` — string concatenation into query
- Missing WHERE clause on `DELETE FROM users` — would delete all rows
- Mutable default argument `password=[]` — classic Python gotcha
- Undefined `send_email` called without import
- Plaintext password storage in `UserManager`

All within 8 seconds of the PR being opened.

---

## Project Structure
repomind/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── webhook_handler.py   # Webhook verification, pipeline invocation
│   ├── pipeline.py          # LangGraph StateGraph — AgentState + 4 nodes
│   ├── github_client.py     # GitHub App auth, diff fetch, comment posting
│   ├── gemini_reviewer.py   # Prompt engineering, language detection
│   ├── chunker.py           # AST-based code chunking
│   └── embedder.py          # fastembed vectors, pgvector storage + retrieval
├── Dockerfile
└── requirements.txt

---

## Local Setup

```bash
git clone https://github.com/Sarishti845/RepoMind.git
cd RepoMind
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=your_key.pem
GITHUB_WEBHOOK_SECRET=your_secret
DATABASE_URL=your_supabase_session_pooler_url
GEMINI_API_KEY=your_gemini_key

```bash
uvicorn app.main:app --reload --port 8000
ngrok http 8000
```

---

## Built by

**Sarishti** — Final year B.Tech CSE, TIET (CGPA 9.50)
Amazon ML Summer School 2024 — selected from 80,000 applicants (top ~3,000)

*Built end-to-end as a solo project — every line written, debugged, and deployed independently.*