import os
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Lazy loading — model loads on first request, not at import time
# This lets uvicorn start instantly without waiting for model load
_model = None

def get_model():
    global _model
    if _model is None:
        print("   🔄 Loading embedding model...")
        _model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder="C:/Users/Sarishti/repomind/models"
        )
        print("   ✅ Embedding model loaded.")
    return _model


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def embed_text(text: str) -> list[float]:
    """
    Converts a piece of text into a 384-dimensional vector.
    Similar code will produce similar vectors — this is what
    makes semantic search possible.
    """
    return get_model().encode(text).tolist()


def store_chunks(repo_full_name: str, chunks: list[dict]):
    """
    Embeds each chunk and stores it in pgvector.
    First deletes existing chunks for this repo so we don't
    accumulate stale embeddings on repeated indexing.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Clear old chunks for this repo first
    cur.execute(
        "DELETE FROM code_chunks WHERE repo_full_name = %s",
        (repo_full_name,)
    )

    for chunk in chunks:
        embedding = embed_text(chunk["content"])
        cur.execute(
            """
            INSERT INTO code_chunks 
            (repo_full_name, file_path, chunk_type, chunk_name, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                repo_full_name,
                chunk["file_path"],
                chunk["chunk_type"],
                chunk["chunk_name"],
                chunk["content"],
                embedding
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Stored {len(chunks)} chunks for {repo_full_name}")


def retrieve_similar_chunks(repo_full_name: str, query_text: str, top_k: int = 5) -> list[dict]:
    """
    Embeds the query text (the PR diff) and finds the top_k most
    semantically similar chunks from the codebase using cosine similarity.
    
    This is the core of RAG — instead of sending the whole codebase to
    Gemini, we only send the most relevant pieces.
    """
    query_embedding = embed_text(query_text)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT file_path, chunk_name, chunk_type, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM code_chunks
        WHERE repo_full_name = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, repo_full_name, query_embedding, top_k)
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "file_path": row[0],
            "chunk_name": row[1],
            "chunk_type": row[2],
            "content": row[3],
            "similarity": row[4]
        }
        for row in rows
    ]