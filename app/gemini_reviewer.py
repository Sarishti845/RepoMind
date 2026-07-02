import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Per-language prompt additions — each language has unique things to check
LANGUAGE_HINTS = {
    "python": """
Python-specific checks:
- Missing type hints on function parameters and return values
- Bare except clauses (except: instead of except SpecificError:)
- Mutable default arguments (def f(x=[]) is a classic Python bug)
- Missing docstrings on public functions and classes
- Using == to compare with None instead of 'is None'
""",
    "javascript": """
JavaScript-specific checks:
- Using var instead of let/const
- Missing error handling in async/await (no try/catch)
- Potential null/undefined dereferencing
- Console.log statements left in production code
- Missing semicolons or inconsistent style
""",
    "typescript": """
TypeScript-specific checks:
- Using 'any' type instead of proper typing
- Missing return type annotations
- Non-null assertion operator (!) used without justification
- Interface vs type alias usage consistency
""",
    "sql": """
SQL-specific checks:
- SELECT * instead of explicit column names
- Missing WHERE clause on UPDATE/DELETE (catastrophic bug)
- N+1 query patterns
- Missing indexes on JOIN columns
""",
}

BASE_PROMPT = """You are an expert code reviewer. Review the following pull request diff.

Focus on:
- Bugs or logic errors
- Security vulnerabilities
- Code style and readability issues
- Missing error handling
{language_hints}
{context_section}

Be concise. For each issue found, give:
1. The file and line (if visible in the diff)
2. A short description of the issue
3. A suggested fix

If the code looks good with no major issues, say so briefly.

DIFF:
{diff}
"""

def detect_language(diff: str) -> str:
    """
    Detect the primary language from file extensions in the diff.
    Returns a language key matching LANGUAGE_HINTS, or empty string.
    """
    diff_lower = diff.lower()
    if ".py" in diff_lower:
        return "python"
    elif ".ts" in diff_lower:
        return "typescript"
    elif ".js" in diff_lower:
        return "javascript"
    elif ".sql" in diff_lower:
        return "sql"
    return ""

def generate_review(diff: str, context_chunks: list = None) -> str:
    """
    Sends the PR diff + relevant codebase context to Gemini.
    Automatically detects language and adds language-specific review hints.
    context_chunks come from pgvector RAG retrieval.
    """
    max_chars = 12000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n... (diff truncated)"

    # Detect language and get specific hints
    language = detect_language(diff)
    language_hints = LANGUAGE_HINTS.get(language, "")
    if language:
        print("Node 3: Detected language: " + language)

    # Build context section from RAG results
    if context_chunks:
        context_parts = []
        for chunk in context_chunks:
            context_parts.append(
                "# " + chunk["chunk_type"] + ": " + chunk["chunk_name"] +
                " (from " + chunk["file_path"] + ", similarity: " +
                str(round(chunk["similarity"], 2)) + ")\n" + chunk["content"]
            )
        context_text = "\n\n".join(context_parts)
        context_section = "Here is relevant existing code from the codebase for context:\n\n" + context_text
    else:
        context_section = ""

    prompt = BASE_PROMPT.format(
        diff=diff,
        language_hints=language_hints,
        context_section=context_section
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text