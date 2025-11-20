from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from cedmate_analytics import generate_analytics_for_user
import os
import re

app = FastAPI(
    title="CEDmate Analytics API",
    description="Backend zur Generierung von Diagrammen für die CEDmate-App."
)

# -------------------------------------------------------------
# Konfiguration: API-Key, Environment, Origin-Listen
# -------------------------------------------------------------

API_KEY = os.getenv("API_KEY", "CEDmateHAWahmad1#")
ENV = os.getenv("ENV", "development").lower()

# Produktions-Frontend (GitHub Pages)
PROD_ORIGINS = [
    "https://ahmad-kalaf.github.io",
    "https://ahmad-kalaf.github.io/CEDmate",
]

# Entwicklungs-Frontends (lokale Flutter Web Tests)
DEV_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
]

# erlaubt localhost mit beliebigen Ports (Flutter web)
LOCALHOST_REGEX = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"

# Native App User-Agents
TRUSTED_USER_AGENTS = [
    "flutter",
    "dart:io",
    "okhttp",
    "cedmate",
    "mozilla"       # notwendig für Browser / Flutter Web
]

# -------------------------------------------------------------
# Output-Verzeichnis öffentlich erreichbar machen
# -------------------------------------------------------------

output_dir = Path(__file__).resolve().parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# -------------------------------------------------------------
# CORS Konfiguration für Browser
# -------------------------------------------------------------

def build_cors_list():
    if ENV == "production":
        return PROD_ORIGINS
    return PROD_ORIGINS + DEV_ORIGINS

CORS_ALLOWED = build_cors_list()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Healthcheck
# -------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "environment": ENV,
        "message": "CEDmate Analytics API aktiv"
    }

# -------------------------------------------------------------
# Origin Prüffunktion
# -------------------------------------------------------------

def is_allowed_origin(origin: str) -> bool:
    if ENV == "production":
        return origin in PROD_ORIGINS
    if origin in PROD_ORIGINS:
        return True
    if re.match(LOCALHOST_REGEX, origin or ""):
        return True
    return False

# -------------------------------------------------------------
# User-Agent Prüffunktion
# -------------------------------------------------------------

def is_allowed_user_agent(agent: str) -> bool:
    agent = agent.lower()
    return any(token in agent for token in TRUSTED_USER_AGENTS)

# -------------------------------------------------------------
# Analytics Endpoint — GET + OPTIONS
# -------------------------------------------------------------

@app.api_route("/analytics", methods=["GET", "OPTIONS"])
async def analytics(request: Request, user: str):

    if request.method == "OPTIONS":
        return {}


    # API-Key prüfen
    key = request.headers.get("x-api-key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key")

    # Origin prüfen (nur Browser)
    origin = request.headers.get("origin", "")
    if origin:
        if not is_allowed_origin(origin):
            raise HTTPException(status_code=403, detail=f"Forbidden origin: {origin}")

    # User-Agent prüfen (native Apps, kein Origin)
    agent = request.headers.get("user-agent", "")
    if not origin:
        if not is_allowed_user_agent(agent):
            raise HTTPException(status_code=403, detail="Forbidden: Invalid User-Agent")

    # Analyse generieren
    try:
        results = generate_analytics_for_user(user)

        base_url = "https://cedmate-analytics-api.onrender.com"
        mapped = {}

        for key, value in results.items():
            if value:
                filename = Path(value).name
                mapped[key] = f"{base_url}/output/{filename}"
            else:
                mapped[key] = None

        return {
            "status": "ok",
            "user": user,
            "results": mapped
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
