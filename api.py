"""
CEDmate Analytics – finale Version (public Output URLs, ohne .env)
-----------------------------------------------------------------
Zulässig:
- deine Flutter-Webseite (GitHub Pages)
- deine App (Android / Windows)
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from firebase_admin import auth
from cedmate_analytics import generate_analytics_for_user
import re
import os

app = FastAPI(title="CEDmate Analytics API", version="3.1")

# -------------------------------------------------------------------
# KONFIGURATION
# -------------------------------------------------------------------

# 🔐 API-Key: zuerst versuchen aus Environment (Render),
# ansonsten Fallback für lokale Tests
API_KEY = os.getenv("API_KEY", "CEDmateHAWahmad1#")

# 🌍 Erlaubte Domains (Web + lokal)
ALLOWED_ORIGINS = [
    "https://ahmad-kalaf.github.io",          # GitHub Pages Domain
    "https://ahmad-kalaf.github.io/CEDmate",  # direkter Pfad
    "http://localhost",                       # lokale Tests (Flutter)
    "http://127.0.0.1",
]

# 🖥️ Vertrauenswürdige User-Agents (App-Erkennung)
TRUSTED_USER_AGENTS = ["CEDmate", "okhttp", "dart:io", "flutter"]

# -------------------------------------------------------------------
# STATIC FILES (macht Diagramme öffentlich erreichbar)
# -------------------------------------------------------------------
output_dir = Path(__file__).resolve().parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# -------------------------------------------------------------------
# CORS-Einstellungen
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["x-api-key", "Content-Type", "Authorization"],
)

# -------------------------------------------------------------------
# Healthcheck
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "CEDmate Analytics API aktiv"}

# -------------------------------------------------------------------
# Hauptendpunkt: /analytics
# -------------------------------------------------------------------
@app.get("/analytics")
async def analytics(request: Request, user: str):
    """
    Generiert Analysen für einen Benutzer (user = Firebase UID)
    Nur erlaubt:
      - wenn gültiger x-api-key vorhanden ist
      - wenn Origin zu ALLOWED_ORIGINS gehört (Web)
      - oder App-User-Agent erkannt wird (Mobile/Desktop)
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
        print(f"📊 Starte Analyse für User: {user}")
        results = generate_analytics_for_user(user)

        # Basis-URL automatisch ermitteln
        base_url = "https://cedmate-analytics-api.onrender.com"
        data = {}

        for k, v in results.items():
            if v:
                filename = Path(str(v)).name
                data[k] = f"{base_url}/output/{filename}"
            else:
                data[k] = None

        print(f"✅ Fertig: {data}")
        return {"status": "ok", "user": user, "results": data}

    except Exception as e:
        print(f"⚠️ Fehler bei Analytics für {user}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
