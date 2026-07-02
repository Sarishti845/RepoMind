# RepoMind — Agentic GitHub Code Review Copilot

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.137-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.7-7C3AED?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-FF6F00?style=for-the-badge&logo=google&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Render](https://img.shields.io/badge/Live_on_Render-46E3B7?style=for-the-badge)

> **An agentic system that automatically reviews GitHub pull requests** — fetches the diff, retrieves relevant codebase context via pgvector RAG, generates structured feedback via Gemini 2.5 Flash, and posts inline comments. Zero manual action required.

🔗 **Live:** https://repomind-vlry.onrender.com &nbsp;|&nbsp; 📁 **Repo:** https://github.com/Sarishti845/RepoMind

---

## What it does

Open a pull request → RepoMind automatically:

| Step | Action |
|------|--------|
| 1 | Receives GitHub webhook (HMAC verified) |
| 2 | Fetches the PR diff via GitHub App API |
| 3 | Indexes codebase with AST chunking + embeddings → pgvector |
| 4 | Retrieves top-5 semantically similar functions as context |
| 5 | Calls Gemini 2.5 Flash with diff + context + language hints |
| 6 | Posts structured review as PR comment |

---

## Architecture

```mermaid
flowchart LR
    A([GitHub PR Opened]) -->|Webhook| B[FastAPI Server]
    B --> C[LangGraph StateGraph]

    subgraph C[LangGraph StateGraph]
        direction LR
        N1[Node 1\nDiff Parser] --> N2[Node 2\nContext Retriever]
        N2 --> N3[Node 3\nReview Generator]
        N3 --> N4[Node 4\nComment Poster]
    end

    N1 -->|GitHub App API| GH[(GitHub)]
    N2 -->|embed + search| DB[(Supabase\npgvector)]
    N3 -->|prompt + context| LLM([Gemini 2.5 Flash])
    N4 -->|post comment| GH
```

**AgentState** — a TypedDict — flows through all 4 nodes. Each node reads what it needs and writes only its output back. No node talks directly to another.

---

## Demo

> RepoMind automatically reviewing a PR — from webhook received to comment posted in under 10 seconds.

![RepoMind demo](assets/demo.gif)

**What you're seeing:** A PR is opened containing SQL injection, a missing WHERE clause on DELETE, and a mutable default argument. RepoMind's bot detects all of them automatically and posts a structured review with suggested fixes — zero manual action required.

---

## RAG Storage — pgvector in action

Code chunks from the repository are embedded and stored in Supabase pgvector. When a PR opens, the diff is embedded and the top-5 most semantically similar chunks are retrieved as context for Gemini.

![Supabase code_chunks table](assets/supabase.png)

Each row stores: `repo_full_name`, `file_path`, `chunk_type`, `chunk_name`, `content`, and a `vector(384)` embedding used for cosine similarity search.

---

## RAG in action

When a new `percentage()` function was added in a PR, Gemini flagged:

> *"The percentage() function will raise a ZeroDivisionError if total is 0, **similar to the divide() function in the existing calculator.py**"*

Gemini knew about `divide()` — which was **not in the diff** — because it was retrieved from pgvector and injected as context. This is codebase-aware review, not just diff-aware.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async webhook handling, fast startup |
| Agent pipeline | LangGraph StateGraph | Retryable nodes, inspectable state, clean separation |
| LLM | Gemini 2.5 Flash | Free tier, fast, strong code reasoning |
| RAG — chunking | Python `ast` module | AST-aware splits guarantee complete function/class units |
| RAG — embeddings | fastembed (all-MiniLM-L6-v2) | 384-dim vectors, ONNX runtime — no PyTorch needed |
| RAG — storage | Supabase pgvector | Cosine similarity search with ivfflat index |
| GitHub integration | GitHub Apps + PyGithub | Scoped permissions, short-lived JWT tokens, bot identity |
| Deployment | Docker + Render | Containerized, auto-deploys on every push to main |

---

## Key Engineering Decisions

**Why LangGraph over a plain function chain?**
Each node owns one responsibility. If Gemini's API changes, only Node 3 changes. Nodes are independently retryable — a Gemini failure doesn't re-fetch the diff. Adding a step is `add_node()` + `add_edge()`.

**Why AST chunking over line splits?**
`ast.parse()` guarantees every chunk is a complete, syntactically valid unit. Line-count splitting could cut a function midway, producing meaningless embeddings.

**Why fastembed over sentence-transformers?**
`sentence-transformers` pulls in PyTorch — 2GB+ with CUDA on Linux, causing build timeouts on Render's free tier. `fastembed` uses ONNX runtime, produces identical 384-dim vectors, deploys in under 5 minutes.

**Why GitHub App over a Personal Access Token?**
GitHub Apps have scoped per-installation permissions, generate short-lived tokens via JWT exchange, and act as a separate bot identity not tied to any personal account.

---

## Project Structure

```
repomind/
├── app/
│   ├── main.py              # FastAPI entry point, router mounting
│   ├── webhook_handler.py   # HMAC verification, pipeline invocation
│   ├── pipeline.py          # LangGraph StateGraph — AgentState + 4 nodes
│   ├── github_client.py     # GitHub App JWT auth, diff fetch, comment posting
│   ├── gemini_reviewer.py   # Prompt engineering, language detection, Gemini call
│   ├── chunker.py           # AST-based code chunking (functions + classes)
│   └── embedder.py          # fastembed vectors, pgvector storage + retrieval
├── Dockerfile               # python:3.12-slim, uvicorn on 0.0.0.0:8000
└── requirements.txt
```

---

## Local Setup

```bash
git clone https://github.com/Sarishti845/RepoMind.git
cd RepoMind
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create `.env`:
```env
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=your_key.pem
GITHUB_WEBHOOK_SECRET=your_secret
DATABASE_URL=your_supabase_session_pooler_url
GEMINI_API_KEY=your_gemini_key
```

```bash
uvicorn app.main:app --reload --port 8000
ngrok http 8000
# Update GitHub App webhook URL to: https://your-ngrok-url/webhooks/github
```

---

## Built by

**Sarishti** — Final year B.Tech CSE, TIET (CGPA 9.50)
Amazon ML Summer School 2024 — selected from 80,000 applicants (top ~3,000)

*Built end-to-end as a solo project — every line written, debugged, and deployed independently.*