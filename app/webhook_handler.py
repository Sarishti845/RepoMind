from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import os
import json
import traceback
from pathlib import Path
from dotenv import load_dotenv
from app.pipeline import review_pipeline
from app.github_client import has_already_commented

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


def run_review(installation_id: int, repo_full_name: str, pr_number: int):
    """
    Runs AFTER the response has been sent to GitHub.
    It's a plain 'def' (not async), so FastAPI runs it in a thread pool
    and the event loop stays free for other requests.
    """
    try:
        if has_already_commented(installation_id, repo_full_name, pr_number):
            return

        review_pipeline.invoke({
            "installation_id": installation_id,
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "diff": "",
            "context_chunks": [],
            "review": "",
            "posted": False
        })
    except Exception as e:
        print("ERROR: " + str(e))
        traceback.print_exc()


@router.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if WEBHOOK_SECRET and not verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(payload_bytes)
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        pr_number = payload["pull_request"]["number"]
        repo_full_name = payload["repository"]["full_name"]
        installation_id = payload["installation"]["id"]

        print("PR event: " + payload["action"] + " #" + str(pr_number) + " on " + repo_full_name)

        # Schedule the slow review to run after we reply
        background_tasks.add_task(run_review, installation_id, repo_full_name, pr_number)
        return {"status": "accepted"}

    return {"status": "ignored"}