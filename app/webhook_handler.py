from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from app.github_client import get_pr_diff, post_pr_comment, get_repo_files
from app.gemini_reviewer import generate_review
from app.chunker import chunk_repository
from app.embedder import store_chunks, retrieve_similar_chunks

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter()
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/webhooks/github")
async def github_webhook(request: Request):
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if WEBHOOK_SECRET and not verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(payload_bytes)
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = payload.get("action")
        pr_number = payload["pull_request"]["number"]
        repo_full_name = payload["repository"]["full_name"]
        installation_id = payload["installation"]["id"]

        if action == "opened":
            print(f"\n*** PR #{pr_number} opened on {repo_full_name} ***")
            try:
                print("   Fetching diff...")
                diff = get_pr_diff(installation_id, repo_full_name, pr_number)
                print(f"   Diff length: {len(diff)} chars")

                print("   Indexing repository for RAG...")
                repo_files = get_repo_files(installation_id, repo_full_name)
                chunks = chunk_repository(repo_files)
                print(f"   Found {len(chunks)} code chunks")

                if chunks:
                    store_chunks(repo_full_name, chunks)
                    context_chunks = retrieve_similar_chunks(repo_full_name, diff, top_k=5)
                    print(f"   Retrieved {len(context_chunks)} relevant chunks")
                else:
                    context_chunks = []
                    print("   No Python chunks found, skipping RAG")

                print("   Generating review with Gemini...")
                review = generate_review(diff, context_chunks)
                print(f"\n--- REVIEW ---\n{review}\n--------------")

                print("   Posting comment to PR...")
                post_pr_comment(installation_id, repo_full_name, pr_number, "## RepoMind Review\n\n" + review)
                print("   Comment posted!")

            except Exception as e:
                print(f"   ERROR: {e}")
                import traceback
                traceback.print_exc()

    return {"status": "ok"}
