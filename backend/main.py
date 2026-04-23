from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import leads, investors, meetings, sequences, voice, discovery

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
# sequences router owns /review-queue/* and /sequences/* — no prefix, paths defined in router
app.include_router(sequences.router, tags=["sequences"])
app.include_router(discovery.router, tags=["discovery"])
app.include_router(voice.router, tags=["voice"])  # paths defined in router: /webhook/telegram, /voice/feedback


@app.get("/health")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
