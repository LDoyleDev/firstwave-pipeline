import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.auth import api_key_middleware
from backend.routers import leads, investors, meetings, sequences, voice, discovery, actions, status, analytics, compliance

app = FastAPI(title="FirstWave Pipeline", version="1.0.0")

# API-key gate. Registered first so it ends up INNERMOST — CORS (registered last,
# below) stays outermost and so adds its headers even to 401/503 responses.
app.middleware("http")(api_key_middleware)

# Host allow-list — the /u/{token} compliance routes are public-facing.
# Override via the ALLOWED_HOSTS env var (comma-separated) if a caller is missed.
_allowed_hosts = [
    h.strip() for h in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",") if h.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://0.0.0.0:5173",
        "http://localhost:5173",
        "https://firstwave-pipeline.vercel.app",
    ],
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
app.include_router(actions.router, prefix="/actions", tags=["actions"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# compliance router owns /u/* and /suppress — no prefix, paths defined in router
app.include_router(compliance.router, tags=["compliance"])


@app.get("/health")
def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}
