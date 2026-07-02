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

def get_repo_files(installation_id: int, repo_full_name: str) -> dict[str, str]:
    """
    Fetches all Python files from the repo's default branch.
    Returns a dict of {file_path: file_content}.
    This is what we chunk and embed for RAG context.
    """
    gh = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    
    files = {}
    try:
        contents = repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            elif file_content.path.endswith(".py"):
                try:
                    files[file_content.path] = file_content.decoded_content.decode("utf-8")
                except Exception:
                    pass
    except Exception as e:
        print(f"   Warning: could not fetch repo files: {e}")
    
    return files    

def has_already_commented(installation_id: int, repo_full_name: str, pr_number: int) -> bool:
    """
    Checks if RepoMind has already posted a review comment on this PR.
    Prevents duplicate comments when new commits are pushed to an open PR.
    """
    gh = get_installation_client(installation_id)
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    
    for comment in pr.get_issue_comments():
        if "RepoMind Review" in comment.body:
            print("Already commented on this PR — skipping.")
            return True
    return False