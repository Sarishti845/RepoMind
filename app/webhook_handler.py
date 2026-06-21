from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import os
import json
from dotenv import load_dotenv

from app.github_client import get_pr_diff, post_pr_comment
from app.gemini_reviewer import generate_review

load_dotenv()

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
            print(f"\n🚀 PR #{pr_number} opened on {repo_full_name}")
            print(f"   Title: {payload['pull_request']['title']}")
            print(f"   Author: {payload['pull_request']['user']['login']}")

            try:
                # Node 1 — fetch the diff
                print("   📥 Fetching diff...")
                diff = get_pr_diff(installation_id, repo_full_name, pr_number)
                print(f"   Diff length: {len(diff)} chars")

                # Node 3 — generate review (we're skipping Node 2/RAG until Week 2)
                print("   🤖 Generating review with Gemini...")
                review = generate_review(diff)
                print(f"\n--- REVIEW ---\n{review}\n--------------")

                # Node 4 — post the review as a PR comment
                print("   💬 Posting comment to PR...")
                comment_header = "## 🤖 RepoMind Review\n\n"
                post_pr_comment(installation_id, repo_full_name, pr_number, comment_header + review)
                print("   ✅ Comment posted!")

            except Exception as e:
                print(f"   ❌ Error during review pipeline: {e}")

    return {"status": "ok"}