"""
CEDmate Analytics – sichere FastAPI-Schnittstelle (für Render)
--------------------------------------------------------------
Diese Datei startet den Webserver auf Render und bietet den Endpunkt:
  GET /analytics?user=<uid>
Erfordert Header:
  x-api-key: <dein geheimer Schlüssel>
"""

from fastapi import FastAPI, Request, HTTPException
from cedmate_analytics import generate_analytics_for_user
import os

app = FastAPI(title="CEDmate Analytics API", version="1.0")

# API-Key aus Render-Umgebung (in Environment-Variablen)
API_KEY = os.getenv("API_KEY", None)
if not API_KEY:
    print("⚠️ WARNUNG: Kein API_KEY gesetzt! Bitte in Render → Environment hinzufügen.")

@app.get("/")
def root():
    """Healthcheck-Endpunkt"""
    return {"status": "ok", "message": "CEDmate Analytics API läuft."}

@app.get("/analytics")
async def analytics(request: Request, user: str):
    """
    Führt die Analyse für den angegebenen Benutzer aus.
    Beispiel:
      GET /analytics?user=Larissa
      Header: x-api-key: <dein geheimnis>
    """
    key = request.headers.get("x-api-key")
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        results = generate_analytics_for_user(user)
        data = {k: str(v) if v else None for k, v in results.items()}
        return {"status": "ok", "user": user, "results": data}
    except Exception as e:
        print(f"Fehler bei Analytics für {user}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
