# api.py
from fastapi import FastAPI
from cedmate_analytics import generate_analytics_for_user
import json

app = FastAPI(title="CEDmate Analytics API")

@app.get("/")
def root():
    return {"status": "ok", "message": "CEDmate Analytics API läuft."}

@app.get("/analytics")
def run_analytics(user: str):
    """
    Führt die Analyse für einen bestimmten Benutzer aus.
    Beispiel: /analytics?user=Larissa
    """
    try:
        results = generate_analytics_for_user(user)
        # Konvertiere Pfade in Strings (JSON-serialisierbar)
        data = {k: str(v) if v else None for k, v in results.items()}
        return {"status": "ok", "user": user, "results": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
