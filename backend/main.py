from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import leads, investors, meetings, sequences, voice

app = FastAPI(title="FirstWave Pipeline", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://0.0.0.0:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router, prefix="/leads", tags=["leads"])
app.include_router(investors.router, prefix="/investors", tags=["investors"])
app.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
app.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
app.include_router(voice.router, tags=["voice"])  # paths defined in router: /webhook/telegram, /voice/feedback


@app.get("/health")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
