import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

REVIEW_PROMPT_TEMPLATE = """You are an expert code reviewer. Review the following GitHub pull request diff.

Focus on:
- Bugs or logic errors
- Security vulnerabilities
- Code style and readability issues
- Missing error handling

Be concise. For each issue found, give:
1. The file and line (if visible in the diff)
2. A short description of the issue
3. A suggested fix

If the code looks good with no major issues, say so briefly.

DIFF:
{diff}
"""

def generate_review(diff: str) -> str:
    """
    Sends the PR diff to Gemini 2.5 Flash and gets back a structured
    code review as plain text. We're using the free tier here —
    Gemini 2.5 Flash is fast and cheap, good enough for this use case.
    
    Note: Large diffs can exceed context limits. For now we truncate
    to keep it simple — proper chunking comes in Week 2 with RAG.
    """
    # Truncate very large diffs to avoid hitting token limits
    max_chars = 15000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n... (diff truncated for length)"

    prompt = REVIEW_PROMPT_TEMPLATE.format(diff=diff)

    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

    return response.text