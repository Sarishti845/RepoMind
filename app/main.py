from fastapi import FastAPI
from app.webhook_handler import router

app = FastAPI(title="RepoMind")
app.include_router(router)

@app.get("/")
def health_check():
    return {"status": "RepoMind is running"}