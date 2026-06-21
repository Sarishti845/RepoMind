import os
import jwt
import time
import requests
from github import Github, GithubIntegration
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")

def get_installation_client(installation_id: int) -> Github:
    """
    GitHub Apps don't use a single static token like a personal access token.
    Instead: we sign a JWT with our private key, exchange it for a short-lived
    installation access token (valid ~1 hour), and use THAT to make API calls.
    This is more secure — if a token leaks, it expires soon and is scoped
    only to the repos this installation was given access to.
    """
    with open(PRIVATE_KEY_PATH, "r") as key_file:
        private_key = key_file.read()

    integration = GithubIntegration(APP_ID, private_key)
    access_token = integration.get_access_token(installation_id).token
    return Github(access_token)


def get_pr_diff(installation_id: int, repo_full_name: str, pr_number: int) -> str:
    """
    Fetches the actual code changes (the diff) for a pull request.
    A diff shows what lines were added/removed/changed — this is what
    we'll send to Gemini for review.
    """
    gh = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    # PyGithub doesn't directly expose the raw diff text, so we fetch it
    # via the diff_url using the same installation token
    headers = {
        "Authorization": f"Bearer {gh._Github__requester._Requester__auth.token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    response = requests.get(pr.url, headers=headers)
    return response.text

def post_pr_comment(installation_id: int, repo_full_name: str, pr_number: int, comment_body: str):
    """
    Posts the AI-generated review as a comment on the pull request.
    This uses the same installation-scoped client we used to fetch the diff —
    GitHub Apps act on behalf of the installation, not a personal user account.
    """
    gh = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(comment_body)