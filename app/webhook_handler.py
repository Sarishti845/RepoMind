from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import os
import json
from dotenv import load_dotenv

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
    
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if WEBHOOK_SECRET and not verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload from bytes (not request.json() — body already consumed)
    payload = json.loads(payload_bytes)
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = payload.get("action")
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        
        if action == "opened":
            print(f"\n🚀 PR #{pr_number} opened on {repo_name}")
            print(f"   Title: {payload['pull_request']['title']}")
            print(f"   Author: {payload['pull_request']['user']['login']}")

    return {"status": "ok"}