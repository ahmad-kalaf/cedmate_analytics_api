"""
CEDmate Analytics Plugin – sichere & robuste Variante
----------------------------------------------------
Dieses Skript generiert Diagramme (PNG) für Firestore-Daten eines bestimmten Benutzers.
Es wird von api.py (FastAPI) aufgerufen, kann aber auch lokal über CLI verwendet werden.
"""

import os
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------------------------------------------
# Pfade & Initialisierung
# -------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
# serviceAccount.json wird als Secret File über Render bereitgestellt:
SA_PATH = Path(os.getenv("SERVICE_ACCOUNT_PATH", SCRIPT_DIR / "serviceAccount.json"))
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------------------
# Firestore-Verbindung
# -------------------------------------------------------------------
def connect_firestore(service_account_path: str | None = None):
    """Initialisiert Firestore mit dem Service-Account."""
    sa_path = Path(service_account_path) if service_account_path else SA_PATH
    if not sa_path.exists():
        raise FileNotFoundError(
            f"serviceAccount.json nicht gefunden unter: {sa_path}\n"
            f"Bitte Datei als Secret File bei Render hinterlegen oder lokal im Ordner ablegen."
        )

    cred = credentials.Certificate(str(sa_path))
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    return firestore.client()

# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------
def _convert_firestore_timestamps(entry: dict):
    for k, v in list(entry.items()):
        if hasattr(v, "to_datetime"):
            entry[k] = v.to_datetime()
    return entry


def _detect_time_col(df: pd.DataFrame) -> str | None:
    dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if dt_cols:
        return dt_cols[0]
    name_order = ["zeit", "time", "datum", "date", "timestamp", "startzeit", "endzeit",
                  "mahlzeitzeitpunkt"]
    for key in name_order:
        cand = [c for c in df.columns if key in c.lower()]
        if cand:
            try:
                df[cand[0]] = pd.to_datetime(df[cand[0]])
                return cand[0]
            except Exception:
                continue
    return None


def _detect_value_col(df: pd.DataFrame, preference: list[str]) -> str | None:
    for name in preference:
        cols = [c for c in df.columns if name == c.lower()]
        if cols and pd.api.types.is_numeric_dtype(df[cols[0]]):
            return cols[0]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return num_cols[0] if num_cols else None


def _df_from_user_subcollection(db, user_id: str, subcollection: str) -> pd.DataFrame:
    user_ref = db.collection("users").document(user_id)
    docs = user_ref.collection(subcollection).get()
    rows = []
    for d in docs:
        entry = d.to_dict() or {}
        entry["id"] = d.id
        rows.append(_convert_firestore_timestamps(entry))
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    print(f"Fetched {len(df)} docs from users/{user_id}/{subcollection}")
    return df

# -------------------------------------------------------------------
# Fetch Layer
# -------------------------------------------------------------------
def fetch_for_user(db, collection_name: str, user_id: str) -> pd.DataFrame:
    """Holt Daten aus users/<userId>/<collection_name>."""
    return _df_from_user_subcollection(db, user_id, collection_name)

# -------------------------------------------------------------------
# Plotter
# -------------------------------------------------------------------
def plot_stuhlgang(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No stuhlgang entries for '{user_id}'.")
        return None
    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df,
                             ["konsistenz", "bristol", "typ", "score", "wert", "level",
                              "intensitaet", "intensität", "staerke", "stärke"])
    if not tcol or not vcol:
        return None
    out_path = OUTPUT_DIR / f"stuhlgang_scatter_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.scatter(df[tcol], df[vcol], c=df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel(vcol)
    plt.title(f"Stuhlgang – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_stimmung(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No stimmung entries for '{user_id}'.")
        return None
    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df, ["wert", "score", "level"])
    if not tcol or not vcol:
        return None
    df = df.sort_values(tcol)
    out_path = OUTPUT_DIR / f"stimmung_line_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.plot(df[tcol], df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel("Stimmungswert")
    plt.title(f"Stimmung – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_symptome(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No symptome entries for '{user_id}'.")
        return None
    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df,
                             ["intensitaet", "intensität", "staerke", "stärke", "wert", "score",
                              "level", "schmerz", "severity"])
    if not tcol or not vcol:
        return None
    out_path = OUTPUT_DIR / f"symptome_scatter_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.scatter(df[tcol], df[vcol], c=df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel("Symptomstärke")
    plt.title(f"Symptome – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_mahlzeit(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No mahlzeiten entries for '{user_id}'.")
        return None
    tcol = _detect_time_col(df)
    if not tcol:
        return None
    df[tcol] = pd.to_datetime(df[tcol], errors='coerce')
    df = df.dropna(subset=[tcol])
    df["datum"] = df[tcol].dt.date
    counts = df.groupby("datum").size()
    if counts.empty:
        return None
    out_path = OUTPUT_DIR / f"mahlzeiten_bars_{user_id}.png"
    plt.figure(figsize=(10, 5))
    counts.plot(kind="bar", color="cornflowerblue", edgecolor="black")
    plt.xlabel("Datum")
    plt.ylabel("Anzahl Mahlzeiten")
    plt.title(f"Mahlzeiten pro Tag – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path

# -------------------------------------------------------------------
# Hauptfunktion
# -------------------------------------------------------------------
def generate_analytics_for_user(user_id: str, service_account: str | None = None):
    db = connect_firestore(service_account)
    data = {
        "stuhlgang": fetch_for_user(db, "stuhlgaenge", user_id),
        "stimmung": fetch_for_user(db, "stimmungen", user_id),
        "symptome": fetch_for_user(db, "symptoms", user_id),
        "mahlzeit": fetch_for_user(db, "mahlzeiten", user_id),
    }
    return {
        "stuhlgang": plot_stuhlgang(data["stuhlgang"], user_id),
        "stimmung": plot_stimmung(data["stimmung"], user_id),
        "symptome": plot_symptome(data["symptome"], user_id),
        "mahlzeit": plot_mahlzeit(data["mahlzeit"], user_id),
    }

# -------------------------------------------------------------------
# CLI-Aufruf
# -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate CEDmate analytics for a specific user.")
    parser.add_argument("--user", required=True, help="Firebase UID des Users (users/<uid>/...)")
    parser.add_argument("--creds", help="Pfad zur serviceAccount.json (optional)")
    args = parser.parse_args()
    results = generate_analytics_for_user(args.user, args.creds)
    print("\n✓ Analytics complete.")
    for k, v in results.items():
        print(f"  {k}: {v if v else 'no output'}")

if __name__ == "__main__":
    main()
