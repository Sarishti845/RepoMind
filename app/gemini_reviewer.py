import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

REVIEW_PROMPT_TEMPLATE = """You are an expert code reviewer. Review the following GitHub pull request diff.

Focus on:
- Bugs or logic errors
- Security vulnerabilities  
- Code style and readability issues
- Missing error handling

{context_section}

Be concise. For each issue found, give:
1. The file and line (if visible in the diff)
2. A short description of the issue
3. A suggested fix

If the code looks good with no major issues, say so briefly.

DIFF:
{diff}
"""

def generate_review(diff: str, context_chunks: list[dict] = None) -> str:
    """
    Sends the PR diff + relevant codebase context to Gemini.
    context_chunks come from pgvector RAG retrieval.
    """
    max_chars = 12000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n... (diff truncated)"

    # Build context section from RAG results
    if context_chunks:
        context_parts = []
        for chunk in context_chunks:
            context_parts.append(
                f"# {chunk['chunk_type']}: {chunk['chunk_name']} "
                f"(from {chunk['file_path']}, similarity: {chunk['similarity']:.2f})\n"
                f"{chunk['content']}"
            )
        context_text = "\n\n".join(context_parts)
        context_section = f"Here is relevant existing code from the codebase for context:\n\n{context_text}\n"
    else:
        context_section = ""

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        diff=diff,
        context_section=context_section
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text