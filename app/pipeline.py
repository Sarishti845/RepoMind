from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.github_client import get_pr_diff, get_repo_files, post_pr_comment
from app.chunker import chunk_repository
from app.embedder import store_chunks, retrieve_similar_chunks
from app.gemini_reviewer import generate_review


# ── 1. AGENT STATE ───────────────────────────────────────────────────────────
# This TypedDict is the single shared object that flows through all 4 nodes.
# Every node reads from it and writes back to it.
# Think of it as a baton being passed in a relay race — each runner adds
# something to it before handing it off.

class AgentState(TypedDict):
    # Inputs — set before the graph runs
    installation_id: int
    repo_full_name: str
    pr_number: int
    # Outputs — filled in progressively by each node
    diff: str
    context_chunks: list
    review: str
    posted: bool


# ── 2. NODE 1: DIFF PARSER ───────────────────────────────────────────────────
# Responsibility: fetch the PR diff from GitHub API
# Reads:  installation_id, repo_full_name, pr_number
# Writes: diff

def parse_diff(state: AgentState) -> dict:
    print("Node 1: Fetching diff...")
    diff = get_pr_diff(
        state["installation_id"],
        state["repo_full_name"],
        state["pr_number"]
    )
    print(f"Node 1: Diff length: {len(diff)} chars")
    return {"diff": diff}


# ── 3. NODE 2: CONTEXT RETRIEVER ─────────────────────────────────────────────
# Responsibility: index the codebase and retrieve relevant chunks via RAG
# Reads:  installation_id, repo_full_name, diff
# Writes: context_chunks

def retrieve_context(state: AgentState) -> dict:
    print("Node 2: Indexing repo and retrieving context...")
    repo_files = get_repo_files(
        state["installation_id"],
        state["repo_full_name"]
    )
    chunks = chunk_repository(repo_files)
    print(f"Node 2: Found {len(chunks)} code chunks")

    if chunks:
        store_chunks(state["repo_full_name"], chunks)
        context_chunks = retrieve_similar_chunks(
            state["repo_full_name"],
            state["diff"],
            top_k=5
        )
        print(f"Node 2: Retrieved {len(context_chunks)} relevant chunks")
    else:
        context_chunks = []
        print("Node 2: No Python chunks found, skipping RAG")

    return {"context_chunks": context_chunks}


# ── 4. NODE 3: REVIEW GENERATOR ──────────────────────────────────────────────
# Responsibility: call Gemini with diff + context, get structured review
# Reads:  diff, context_chunks
# Writes: review

def generate_review_node(state: AgentState) -> dict:
    print("Node 3: Generating review with Gemini...")
    review = generate_review(
        state["diff"],
        state["context_chunks"]
    )
    print(f"Node 3: Review generated ({len(review)} chars)")
    return {"review": review}


# ── 5. NODE 4: COMMENT POSTER ────────────────────────────────────────────────
# Responsibility: post the review as a PR comment on GitHub
# Reads:  installation_id, repo_full_name, pr_number, review
# Writes: posted

def post_comment(state: AgentState) -> dict:
    print("Node 4: Posting comment to PR...")
    post_pr_comment(
        state["installation_id"],
        state["repo_full_name"],
        state["pr_number"],
        "## RepoMind Review\n\n" + state["review"]
    )
    print("Node 4: Comment posted!")
    return {"posted": True}


# ── 6. BUILD THE GRAPH ───────────────────────────────────────────────────────
# Wire the 4 nodes together into a linear pipeline.
# START and END are special LangGraph sentinels.

def build_graph():
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("parse_diff", parse_diff)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_review", generate_review_node)
    graph.add_node("post_comment", post_comment)

    # Wire edges: START -> Node1 -> Node2 -> Node3 -> Node4 -> END
    graph.add_edge(START, "parse_diff")
    graph.add_edge("parse_diff", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_review")
    graph.add_edge("generate_review", "post_comment")
    graph.add_edge("post_comment", END)

    return graph.compile()


# Compile once at module level — reused for every PR
review_pipeline = build_graph()