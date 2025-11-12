"""
CEDmate Analytics – final abgesicherte Version (keine .env nötig)
-----------------------------------------------------------------
Zulässig:
- deine Flutter-Webseite (GitHub Pages)
- deine App (Android / Windows)
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth
from cedmate_analytics import generate_analytics_for_user
import re

app = FastAPI(title="CEDmate Analytics API", version="3.0")

# -------------------------------------------------------------------
# KONFIGURATION
# -------------------------------------------------------------------

import os

API_KEY = os.getenv("API_KEY", "CEDmateHAWahmad1#")

# Zugelassene Ursprünge (Domains)
ALLOWED_ORIGINS = [
    "https://ahmad-kalaf.github.io",     # GitHub Pages Domain
    "https://ahmad-kalaf.github.io/CEDmate",  # direkter Pfad
    "http://localhost",                  # für lokale Tests
    "http://127.0.0.1",
]

# CORS konfigurieren (nur deine App darf Anfragen senden)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["x-api-key", "Content-Type", "Authorization"],
)

# Optional: App-Header-Erkennung für native Apps
TRUSTED_USER_AGENTS = ["CEDmate", "okhttp", "dart:io"]

# -------------------------------------------------------------------
# Healthcheck
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "CEDmate Analytics API aktiv"}

# -------------------------------------------------------------------
# Hauptendpunkt
# -------------------------------------------------------------------
@app.get("/analytics")
async def analytics(request: Request, user: str):
    """
    Erlaubt nur Zugriffe von:
      - https://ahmad-kalaf.github.io/CEDmate/
      - deiner App (Header x-api-key)
    """

    # 1️⃣ API-Key prüfen
    key = request.headers.get("x-api-key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key")

    # 2️⃣ Herkunft (Origin) prüfen – für Web-Aufrufe
    origin = request.headers.get("origin", "")
    if origin and not any(origin.startswith(o) for o in ALLOWED_ORIGINS):
        raise HTTPException(status_code=403, detail=f"Forbidden origin: {origin}")

    # 3️⃣ User-Agent prüfen – für native Apps (APK / Windows)
    agent = request.headers.get("user-agent", "").lower()
    if origin == "" and not any(re.search(pat.lower(), agent) for pat in TRUSTED_USER_AGENTS):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid User-Agent")

    # 4️⃣ Analyse starten
    try:
        results = generate_analytics_for_user(user)
        data = {k: str(v) if v else None for k, v in results.items()}
        return {"status": "ok", "user": user, "results": data}
    except Exception as e:
        print(f"⚠️ Fehler bei Analytics für {user}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
