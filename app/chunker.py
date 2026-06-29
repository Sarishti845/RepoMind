import ast
import os

def chunk_python_file(file_path: str, content: str) -> list[dict]:
    """
    Uses Python's built-in AST (Abstract Syntax Tree) module to split
    a Python file into meaningful chunks — functions and classes.
    
    Why AST instead of splitting by lines?
    Splitting by line count is arbitrary — you might cut a function in half.
    AST understands Python's actual structure, so every chunk is a complete,
    syntactically valid unit (a whole function or a whole class).
    """
    chunks = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If the file has syntax errors, skip it
        return chunks
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Get the source lines for this node
            start_line = node.lineno - 1
            end_line = node.end_lineno
            
            chunk_content = "\n".join(content.split("\n")[start_line:end_line])
            
            chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"
            
            chunks.append({
                "file_path": file_path,
                "chunk_type": chunk_type,
                "chunk_name": node.name,
                "content": chunk_content
            })
    
    return chunks


def chunk_repository(repo_files: dict[str, str]) -> list[dict]:
    """
    Takes a dict of {file_path: file_content} and returns
    all chunks across all Python files in the repo.
    """
    all_chunks = []
    
    for file_path, content in repo_files.items():
        if file_path.endswith(".py"):
            chunks = chunk_python_file(file_path, content)
            all_chunks.extend(chunks)
    
    return all_chunks